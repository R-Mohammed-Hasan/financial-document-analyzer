"""
File database model.

This module defines the File SQLAlchemy model for file management and processing.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Float,
    JSON,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from db.base import Base


class FileStatus(str, Enum):
    """File processing status enumeration."""

    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DELETED = "deleted"


class FileType(str, Enum):
    """File type enumeration."""

    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    TXT = "txt"
    JSON = "json"
    XML = "xml"
    IMAGE = "image"
    OTHER = "other"


class File(Base):
    """
    File model for storing file information and processing status.

    Attributes:
        id: Primary key
        filename: Original filename
        original_filename: Original filename before processing
        file_path: Path to stored file
        file_url: URL to access the file
        file_size: File size in bytes
        content_type: MIME type of the file
        file_type: Categorized file type
        status: Processing status
        processing_metadata: JSON metadata from processing
        checksum: File checksum for integrity verification
        user_id: Foreign key to user who uploaded the file
        created_at: Upload timestamp
        updated_at: Last update timestamp
        processed_at: Processing completion timestamp
        expires_at: File expiration timestamp
        is_public: Whether the file is publicly accessible
        download_count: Number of downloads
        tags: JSON array of tags for categorization
    """

    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_url = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=False)
    file_type = Column(String(20), nullable=False, default=FileType.OTHER)
    status = Column(String(20), nullable=False, default=FileStatus.UPLOADING)
    processing_metadata = Column(JSON, nullable=True)
    checksum = Column(String(128), nullable=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    processed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    download_count = Column(Integer, default=0, nullable=False)
    tags = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User", back_populates="files")

    def __repr__(self) -> str:
        """String representation of the file."""
        return f"<File(id={self.id}, filename={self.filename}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert file to dictionary."""
        return {
            "id": self.id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_url": self.file_url,
            "file_size": self.file_size,
            "content_type": self.content_type,
            "file_type": self.file_type,
            "status": self.status,
            "processing_metadata": self.processing_metadata,
            "checksum": self.checksum,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": (
                self.processed_at.isoformat() if self.processed_at else None
            ),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_public": self.is_public,
            "download_count": self.download_count,
            "tags": self.tags,
        }

    @property
    def is_expired(self) -> bool:
        """Check if file is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return round(self.file_size / (1024 * 1024), 2)

    @property
    def processing_time(self) -> Optional[float]:
        """Get processing time in seconds."""
        if self.processed_at and self.created_at:
            return (self.processed_at - self.created_at).total_seconds()
        return None

    def increment_download_count(self) -> None:
        """Increment download count."""
        self.download_count += 1

    def set_status(self, status: FileStatus) -> None:
        """
        Set file status and update timestamps.

        Args:
            status: New status
        """
        self.status = status
        if status == FileStatus.PROCESSED:
            self.processed_at = datetime.utcnow()
        elif status == FileStatus.FAILED:
            self.processed_at = datetime.utcnow()

    def add_tag(self, tag: str) -> None:
        """
        Add a tag to the file.

        Args:
            tag: Tag to add
        """
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """
        Remove a tag from the file.

        Args:
            tag: Tag to remove
        """
        if self.tags and tag in self.tags:
            self.tags.remove(tag)

    def set_expiration(self, days: int) -> None:
        """
        Set file expiration date.

        Args:
            days: Number of days until expiration
        """
        self.expires_at = datetime.utcnow() + timedelta(days=days)

    def make_public(self) -> None:
        """Make file publicly accessible."""
        self.is_public = True

    def make_private(self) -> None:
        """Make file private."""
        self.is_public = False

    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Update processing metadata.

        Args:
            metadata: Metadata to update
        """
        if not self.processing_metadata:
            self.processing_metadata = {}
        self.processing_metadata.update(metadata)

    @classmethod
    def get_by_filename(cls, filename: str):
        """Get file by filename."""
        return cls.query.filter(cls.filename == filename).first()

    @classmethod
    def get_by_user(cls, user_id: int):
        """Get all files for a user."""
        return cls.query.filter(cls.user_id == user_id).all()

    @classmethod
    def get_public_files(cls):
        """Get all public files."""
        return cls.query.filter(cls.is_public == True).all()

    @classmethod
    def get_expired_files(cls):
        """Get all expired files."""
        return cls.query.filter(
            cls.expires_at.isnot(None), cls.expires_at < datetime.utcnow()
        ).all()

    @classmethod
    def get_files_by_status(cls, status: FileStatus):
        """Get files by status."""
        return cls.query.filter(cls.status == status).all()

    @classmethod
    def get_files_by_type(cls, file_type: FileType):
        """Get files by type."""
        return cls.query.filter(cls.file_type == file_type).all()

    @classmethod
    def search_files(cls, query: str):
        """Search files by filename or tags."""
        return cls.query.filter(
            (cls.filename.contains(query))
            | (cls.original_filename.contains(query))
            | (cls.tags.contains([query]))
        ).all()
