"""
File service layer.

This module contains business logic for file management operations.
"""

import os
import uuid
import hashlib
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from fastapi import UploadFile, HTTPException, status

from db.models.file import File, FileStatus, FileType
from core.config import settings


class FileService:
    """
    Service class for file-related business logic.
    """

    def __init__(self, db: Session):
        """Initialize file service with database session."""
        self.db = db
        self.upload_dir = "uploads"
        self._ensure_upload_dir()

    def _ensure_upload_dir(self):
        """Ensure upload directory exists."""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    def _generate_filename(self, original_filename: str) -> str:
        """Generate a unique filename."""
        file_extension = os.path.splitext(original_filename)[1]
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{file_extension}"

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate file checksum."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _determine_file_type(self, filename: str, content_type: str) -> FileType:
        """Determine file type based on filename and content type."""
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

    def get_file_by_id(self, file_id: int) -> Optional[File]:
        """Get file by ID."""
        return self.db.query(File).filter(File.id == file_id).first()

    def get_files_by_user(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[FileStatus] = None,
        file_type: Optional[FileType] = None,
    ) -> List[File]:
        """Get files for a specific user."""
        query = self.db.query(File).filter(File.user_id == user_id)

        if status:
            query = query.filter(File.status == status)

        if file_type:
            query = query.filter(File.file_type == file_type)

        return query.offset(skip).limit(limit).all()

    def create_file(
        self,
        file: UploadFile,
        user_id: int,
        is_public: bool = False,
        tags: Optional[List[str]] = None,
    ) -> File:
        """Create a new file record and save the uploaded file."""
        # Generate unique filename
        filename = self._generate_filename(file.filename)
        file_path = os.path.join(self.upload_dir, filename)

        # Save file to disk
        try:
            with open(file_path, "wb") as buffer:
                content = file.file.read()
                buffer.write(content)
        except Exception as e:
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
        self.db.commit()
        self.db.refresh(db_file)

        return db_file

    def update_file_status(
        self, file_id: int, status: FileStatus, metadata: Optional[Dict] = None
    ) -> bool:
        """Update file processing status."""
        file = self.get_file_by_id(file_id)
        if not file:
            return False

        file.status = status
        if metadata:
            if not file.processing_metadata:
                file.processing_metadata = {}
            file.processing_metadata.update(metadata)

        if status in [FileStatus.PROCESSED, FileStatus.FAILED]:
            file.processed_at = datetime.utcnow()

        self.db.commit()
        return True

    def update_file_metadata(self, file_id: int, metadata: Dict[str, Any]) -> bool:
        """Update file processing metadata."""
        file = self.get_file_by_id(file_id)
        if not file:
            return False

        if not file.processing_metadata:
            file.processing_metadata = {}

        file.processing_metadata.update(metadata)
        self.db.commit()

        return True

    def increment_download_count(self, file_id: int) -> bool:
        """Increment file download count."""
        file = self.get_file_by_id(file_id)
        if not file:
            return False

        file.download_count += 1
        self.db.commit()

        return True

    def add_file_tags(self, file_id: int, tags: List[str]) -> bool:
        """Add tags to file."""
        file = self.get_file_by_id(file_id)
        if not file:
            return False

        if not file.tags:
            file.tags = []

        for tag in tags:
            if tag not in file.tags:
                file.tags.append(tag)

        self.db.commit()
        return True

    def remove_file_tags(self, file_id: int, tags: List[str]) -> bool:
        """Remove tags from file."""
        file = self.get_file_by_id(file_id)
        if not file or not file.tags:
            return False

        for tag in tags:
            if tag in file.tags:
                file.tags.remove(tag)

        self.db.commit()
        return True

    def set_file_public(self, file_id: int, is_public: bool) -> bool:
        """Set file public/private status."""
        file = self.get_file_by_id(file_id)
        if not file:
            return False

        file.is_public = is_public
        self.db.commit()

        return True

    def delete_file(self, file_id: int) -> bool:
        """Delete file and its record."""
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

        return True

    def get_file_stats(self) -> Dict[str, Any]:
        """Get file statistics."""
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

        return {
            "total_files": total_files,
            "total_size": total_size,
            "files_by_type": files_by_type,
            "files_by_status": files_by_status,
            "public_files": public_files,
            "total_downloads": total_downloads,
        }

    def search_files(
        self, query: str, user_id: Optional[int] = None, limit: int = 20
    ) -> List[File]:
        """Search files by filename or tags."""
        search_filter = or_(
            File.filename.contains(query), File.original_filename.contains(query)
        )

        if user_id:
            search_filter = and_(search_filter, File.user_id == user_id)

        return self.db.query(File).filter(search_filter).limit(limit).all()

    def get_files_by_status(self, status: FileStatus, limit: int = 100) -> List[File]:
        """Get files by processing status."""
        return self.db.query(File).filter(File.status == status).limit(limit).all()

    def get_expired_files(self) -> List[File]:
        """Get files that have expired."""
        return (
            self.db.query(File)
            .filter(File.expires_at.isnot(None), File.expires_at < datetime.utcnow())
            .all()
        )

    def cleanup_expired_files(self) -> int:
        """Clean up expired files and return count of deleted files."""
        expired_files = self.get_expired_files()
        deleted_count = 0

        for file in expired_files:
            if self.delete_file(file.id):
                deleted_count += 1

        return deleted_count

    def get_recent_files(
        self, user_id: Optional[int] = None, days: int = 7
    ) -> List[File]:
        """Get files created in the last N days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = self.db.query(File).filter(File.created_at >= cutoff_date)

        if user_id:
            query = query.filter(File.user_id == user_id)

        return query.all()

    def get_large_files(self, size_threshold: int = 100 * 1024 * 1024) -> List[File]:
        """Get files larger than threshold size."""
        return self.db.query(File).filter(File.file_size >= size_threshold).all()

    def validate_file_type(self, filename: str) -> bool:
        """Validate if file type is allowed."""
        file_extension = os.path.splitext(filename)[1].lower()
        return file_extension in settings.ALLOWED_FILE_TYPES

    def get_storage_usage(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get storage usage statistics."""
        query = self.db.query(
            func.count(File.id).label("file_count"),
            func.sum(File.file_size).label("total_size"),
        )

        if user_id:
            query = query.filter(File.user_id == user_id)

        result = query.first()

        return {
            "file_count": result.file_count or 0,
            "total_size": result.total_size or 0,
            "total_size_mb": round((result.total_size or 0) / (1024 * 1024), 2),
        }
