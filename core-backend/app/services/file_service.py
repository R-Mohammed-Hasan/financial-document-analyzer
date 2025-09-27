"""
File service layer.

This module contains business logic for file management operations.
"""

import os
import uuid
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, func, select
from fastapi import UploadFile, HTTPException, status

from db.models.file import File, FileStatus, FileType
from core.config import settings
from core.logging_config import get_logger

# Module-level logger for the service layer
logger = get_logger(__name__)


class FileService:
    """
    Service class for file-related business logic.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the file service with a database session.

        Returns:
            None
        """
        self.db = db
        self.upload_dir = "uploads"
        self._ensure_upload_dir()

    def _ensure_upload_dir(self):
        """
        Ensure the upload directory exists; create if missing.

        Returns:
            None
        """
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
            logger.debug(f"Created upload directory at {self.upload_dir}")

    def _generate_filename(self, original_filename: str) -> str:
        """
        Generate a unique filename preserving the original extension.

        Returns:
            A unique filename string.
        """
        file_extension = os.path.splitext(original_filename)[1]
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_extension}"

    def _calculate_checksum(self, file_path: str) -> str:
        """
        Calculate MD5 checksum of a file on disk.

        Returns:
            Hex string of the checksum.
        """
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _determine_file_type(self, filename: str, content_type: str) -> FileType:
        """
        Determine logical file type from filename and content type.

        Returns:
            A `FileType` enum value.
        """
        file_extension = os.path.splitext(filename)[1].lower()

        type_mapping = {
            ".pdf": FileType.PDF,
            ".docx": FileType.DOCX,
            ".xlsx": FileType.XLSX,
            ".csv": FileType.CSV,
            ".txt": FileType.TXT,
            ".json": FileType.JSON,
            ".xml": FileType.XML,
        }

        return type_mapping.get(file_extension, FileType.OTHER)

    async def get_file_by_id(self, file_id: int) -> Optional[File]:
        """
        Retrieve a file record by ID.

        Returns:
            The `File` if found; otherwise `None`.
        """
        result = await self.db.execute(select(File).where(File.id == file_id))
        file = result.scalars().first()
        logger.debug(f"Fetch file by id | id={file_id} found={bool(file)}")
        return file

    async def get_files_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[FileStatus] = None,
        file_type: Optional[FileType] = None,
    ) -> List[File]:
        """
        Get files for a specific user with optional filters and pagination.

        Returns:
            List of `File` records.
        """
        query = select(File).where(File.user_id == user_id)

        if status:
            query = query.where(File.status == status)

        if file_type:
            query = query.where(File.file_type == file_type)

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        files = result.scalars().all()
        logger.debug(
            f"User files | user_id={user_id} status={status} type={file_type} count={len(files)}"
        )
        return files

    async def create_file(
        self,
        file: UploadFile,
        user_id: int,
        is_public: bool = False,
        tags: Optional[List[str]] = None,
    ) -> File:
        """
        Save an uploaded file to disk and create its database record.

        Returns:
            The created `File` record.
        """
        # Generate unique filename
        filename = self._generate_filename(file.filename)
        file_path = os.path.join(self.upload_dir, filename)

        # Save file to disk
        try:
            with open(file_path, "wb") as buffer:
                content = file.file.read()
                buffer.write(content)
        except Exception as e:
            logger.error(f"Failed to save file | filename={file.filename} error={e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}",
            )

        # Calculate checksum
        checksum = self._calculate_checksum(file_path)

        # Determine file type
        file_type = self._determine_file_type(file.filename, file.content_type)

        # Check file size
        file_size = len(content)
        if file_size > settings.MAX_FILE_SIZE:
            # Clean up file
            os.remove(file_path)
            logger.warning(
                f"Upload rejected (too large) | filename={file.filename} size={file_size}"
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes",
            )

        # Create file record
        db_file = File(
            filename=filename,
            original_filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            content_type=file.content_type,
            file_type=file_type,
            status=FileStatus.UPLOADED,
            user_id=user_id,
            is_public=is_public,
            checksum=checksum,
            tags=tags,
        )

        self.db.add(db_file)
        await self.db.commit()
        await self.db.refresh(db_file)

        logger.info(
            f"File uploaded | id={db_file.id} user_id={user_id} size={file_size} type={file_type}"
        )
        return db_file

    async def update_file_status(
        self, file_id: int, status: FileStatus, metadata: Optional[Dict] = None
    ) -> bool:
        """
        Update file processing status and optional metadata.

        Returns:
            True if updated; False if the file does not exist.
        """
        file = await self.get_file_by_id(file_id)
        if not file:
            return False

        file.status = status
        if metadata:
            if not file.processing_metadata:
                file.processing_metadata = {}
            file.processing_metadata.update(metadata)

        if status in [FileStatus.PROCESSED, FileStatus.FAILED]:
            file.processed_at = datetime.utcnow()

        await self.db.commit()
        logger.info(
            f"File status updated | id={file_id} status={status} metadata_keys={list(metadata.keys()) if metadata else []}"
        )
        return True

    async def update_file_metadata(
        self, file_id: int, metadata: Dict[str, Any]
    ) -> bool:
        """
        Merge new metadata into file.processing_metadata.

        Returns:
            True if updated; False if the file does not exist.
        """
        file = await self.get_file_by_id(file_id)
        if not file:
            return False

        if not file.processing_metadata:
            file.processing_metadata = {}

        file.processing_metadata.update(metadata)
        await self.db.commit()
        logger.debug(
            f"File metadata updated | id={file_id} keys_added={list(metadata.keys())}"
        )
        return True

    async def increment_download_count(self, file_id: int) -> bool:
        """
        Increment the file's download counter.

        Returns:
            True if updated; False if the file does not exist.
        """
        file = await self.get_file_by_id(file_id)
        if not file:
            return False

        file.download_count += 1
        await self.db.commit()

        return True

    async def add_file_tags(self, file_id: int, tags: List[str]) -> bool:
        """
        Add unique tags to a file's tag list.

        Returns:
            True if updated; False if the file does not exist.
        """
        file = await self.get_file_by_id(file_id)
        if not file:
            return False

        if not file.tags:
            file.tags = []

        for tag in tags:
            if tag not in file.tags:
                file.tags.append(tag)

        await self.db.commit()
        return True

    def remove_file_tags(self, file_id: int, tags: List[str]) -> bool:
        """
        Remove provided tags from a file's tag list.

        Returns:
            True if updated; False if the file does not exist or no tags present.
        """
        file = self.get_file_by_id(file_id)
        if not file or not file.tags:
            return False

        for tag in tags:
            if tag in file.tags:
                file.tags.remove(tag)

        self.db.commit()
        return True

    def set_file_public(self, file_id: int, is_public: bool) -> bool:
        """
        Set whether a file is publicly accessible.

        Returns:
            True if updated; False if the file does not exist.
        """
        file = self.get_file_by_id(file_id)
        if not file:
            return False

        file.is_public = is_public
        self.db.commit()

        return True

    def delete_file(self, file_id: int) -> bool:
        """
        Delete the physical file (if exists) and remove its database record.

        Returns:
            True if deleted; False if the file does not exist.
        """
        file = self.get_file_by_id(file_id)
        if not file:
            return False

        # Delete physical file
        try:
            if os.path.exists(file.file_path):
                os.remove(file.file_path)
        except Exception:
            # Log error but continue with database deletion
            pass

        # Delete database record
        self.db.delete(file)
        self.db.commit()
        logger.info(f"File deleted | id={file_id}")
        return True

    def get_file_stats(self) -> Dict[str, Any]:
        """
        Aggregate and return overall file statistics.

        Returns:
            Dictionary of totals and grouped counts.
        """
        total_files = self.db.query(func.count(File.id)).scalar()
        total_size = self.db.query(func.sum(File.file_size)).scalar() or 0

        # Files by type
        files_by_type = {}
        for file_type in FileType:
            count = (
                self.db.query(func.count(File.id))
                .filter(File.file_type == file_type)
                .scalar()
            )
            files_by_type[file_type] = count

        # Files by status
        files_by_status = {}
        for status in FileStatus:
            count = (
                self.db.query(func.count(File.id))
                .filter(File.status == status)
                .scalar()
            )
            files_by_status[status] = count

        public_files = (
            self.db.query(func.count(File.id)).filter(File.is_public == True).scalar()
        )

        total_downloads = self.db.query(func.sum(File.download_count)).scalar() or 0

        stats = {
            "total_files": total_files,
            "total_size": total_size,
            "files_by_type": files_by_type,
            "files_by_status": files_by_status,
            "public_files": public_files,
            "total_downloads": total_downloads,
        }
        logger.debug(
            f"File stats | total={total_files} public={public_files} downloads={total_downloads}"
        )
        return stats

    def search_files(
        self, query: str, user_id: Optional[int] = None, limit: int = 20
    ) -> List[File]:
        """
        Search files by filename (and optionally by user).

        Returns:
            List of matching `File` records.
        """
        search_filter = or_(
            File.filename.contains(query), File.original_filename.contains(query)
        )

        if user_id:
            search_filter = and_(search_filter, File.user_id == user_id)

        files = self.db.query(File).filter(search_filter).limit(limit).all()
        logger.debug(
            f"Search files | query={query!r} user_id={user_id} limit={limit} count={len(files)}"
        )
        return files

    def get_files_by_status(self, status: FileStatus, limit: int = 100) -> List[File]:
        """
        Get files filtered by their processing status.

        Returns:
            List of `File` records.
        """
        files = self.db.query(File).filter(File.status == status).limit(limit).all()
        logger.debug(f"Files by status | status={status} count={len(files)}")
        return files

    def get_expired_files(self) -> List[File]:
        """
        Retrieve files whose expiration time has passed.

        Returns:
            List of expired `File` records.
        """
        return (
            self.db.query(File)
            .filter(File.expires_at.isnot(None), File.expires_at < datetime.utcnow())
            .all()
        )

    def cleanup_expired_files(self) -> int:
        """
        Delete all expired files and return how many were removed.

        Returns:
            Integer count of deleted files.
        """
        expired_files = self.get_expired_files()
        deleted_count = 0

        for file in expired_files:
            if self.delete_file(file.id):
                deleted_count += 1

        logger.info(f"Expired files cleanup | deleted={deleted_count}")
        return deleted_count

    def get_recent_files(
        self, user_id: Optional[int] = None, days: int = 7
    ) -> List[File]:
        """
        Get files created within the last N days (optionally for a user).

        Returns:
            List of `File` records.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = self.db.query(File).filter(File.created_at >= cutoff_date)

        if user_id:
            query = query.filter(File.user_id == user_id)

        files = query.all()
        logger.debug(f"Recent files | days={days} user_id={user_id} count={len(files)}")
        return files

    def get_large_files(self, size_threshold: int = 100 * 1024 * 1024) -> List[File]:
        """
        Get files larger than the provided size threshold (bytes).

        Returns:
            List of `File` records.
        """
        files = self.db.query(File).filter(File.file_size >= size_threshold).all()
        logger.debug(f"Large files | threshold={size_threshold} count={len(files)}")
        return files

    def validate_file_type(self, filename: str) -> bool:
        """
        Validate if a file has an allowed extension per settings.

        Returns:
            True if allowed; False otherwise.
        """
        file_extension = os.path.splitext(filename)[1].lower()
        return file_extension in settings.ALLOWED_FILE_TYPES

    def get_storage_usage(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Return counts and total size of stored files (optionally per user).

        Returns:
            Dictionary with file_count, total_size (bytes) and MB.
        """
        query = self.db.query(
            func.count(File.id).label("file_count"),
            func.sum(File.file_size).label("total_size"),
        )

        if user_id:
            query = query.filter(File.user_id == user_id)

        result = query.first()

        usage = {
            "file_count": result.file_count or 0,
            "total_size": result.total_size or 0,
            "total_size_mb": round((result.total_size or 0) / (1024 * 1024), 2),
        }
        logger.debug(
            f"Storage usage | user_id={user_id} files={usage['file_count']} size={usage['total_size']}"
        )
        return usage
