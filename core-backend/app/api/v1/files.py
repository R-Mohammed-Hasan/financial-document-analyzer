"""
Files API router.

This module defines file management API endpoints including file upload, download,
processing, and management operations.
"""

from typing import List, Optional
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from db.session import get_db
from db.models.file import FileStatus, FileType
from db.models.user import User
from services.file_service import FileService
from core.config import settings
from core.logging_config import get_logger
from fastapi import HTTPException, Query
from typing import Optional
from core.dependencies import get_current_user
from db.session import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession

# Module-level logger
logger = get_logger(__name__)

router = APIRouter()


@router.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    is_public: bool = Form(False),
    tags: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Upload a file for processing.

    Args:
        file: File to upload
        is_public: Whether the file should be publicly accessible
        tags: Comma-separated tags for the file
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with upload status and file information
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Validate file type
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File must have a filename"
        )

    file_extension = (
        file.filename.split(".")[-1].lower() if "." in file.filename else ""
    )
    if f".{file_extension}" not in settings.ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_FILE_TYPES)}",
        )

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

    # Use FileService to handle the upload
    file_service = FileService(db)
    try:
        db_file = await file_service.create_file(
            file=file,
            user_id=current_user.id,
            is_public=is_public,
            tags=tag_list,
        )

        return {
            "message": "File uploaded successfully",
            "file_id": db_file.id,
            "filename": db_file.filename,
            "original_filename": db_file.original_filename,
            "file_size": db_file.file_size,
            "content_type": db_file.content_type,
            "file_type": db_file.file_type,
            "status": db_file.status,
            "is_public": db_file.is_public,
            "tags": db_file.tags,
            "created_at": (
                db_file.created_at.isoformat() if db_file.created_at else None
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during file upload",
        )


@router.get("/files", response_model=dict)
async def list_files(
    skip: int = Query(0, ge=0, description="Number of files to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of files to return"),
    status: Optional[FileStatus] = Query(None, description="Filter by file status"),
    file_type: Optional[FileType] = Query(None, description="Filter by file type"),
    search: Optional[str] = Query(None, description="Search query for files"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    is_public: Optional[bool] = Query(None, description="Filter by public status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    List files with pagination and filtering.

    Args:
        skip: Number of files to skip
        limit: Number of files to return
        status: Filter by file status
        file_type: Filter by file type
        search: Search query for files
        user_id: Filter by user ID
        is_public: Filter by public status
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with paginated file list
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get files
    file_service = FileService(db)

    # Get user's files with filters
    files = await file_service.get_files_by_user(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status,
        file_type=file_type,
    )

    # Convert files to dict format
    file_list = []
    for file in files:
        file_dict = {
            "id": file.id,
            "filename": file.filename,
            "original_filename": file.original_filename,
            "file_size": file.file_size,
            "content_type": file.content_type,
            "file_type": file.file_type,
            "status": file.status,
            "user_id": file.user_id,
            "created_at": file.created_at.isoformat() if file.created_at else None,
            "is_public": file.is_public,
            "download_count": file.download_count,
            "tags": file.tags,
        }
        file_list.append(file_dict)

    # Apply additional filters if specified
    if search:
        search_lower = search.lower()
        file_list = [
            f
            for f in file_list
            if (
                search_lower in f["filename"].lower()
                or search_lower in f["original_filename"].lower()
            )
        ]

    if user_id:
        file_list = [f for f in file_list if f["user_id"] == user_id]

    if is_public is not None:
        file_list = [f for f in file_list if f["is_public"] == is_public]

    # Apply pagination
    total = len(file_list)
    files = file_list[skip : skip + limit]

    return {
        "files": files,
        "total": total,
        "page": skip // limit + 1 if limit > 0 else 1,
        "page_size": limit,
    }


@router.get("/files/{file_id}")
async def get_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Get file information by ID.

    Args:
        file_id: File ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with file information
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get file
    file_service = FileService(db)
    file = await file_service.get_file_by_id(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Security check: user can only access their own files or public files
    if file.user_id != current_user.id and not file.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. File is not public and does not belong to you.",
        )

    return {
        "id": file.id,
        "filename": file.filename,
        "original_filename": file.original_filename,
        "file_path": file.file_path,
        "file_url": f"http://localhost:8000/files/{file_id}/download",
        "file_size": file.file_size,
        "content_type": file.content_type,
        "file_type": file.file_type,
        "status": file.status,
        "user_id": file.user_id,
        "created_at": file.created_at.isoformat() if file.created_at else None,
        "updated_at": file.updated_at.isoformat() if file.updated_at else None,
        "processed_at": file.processed_at.isoformat() if file.processed_at else None,
        "is_public": file.is_public,
        "download_count": file.download_count,
        "tags": file.tags,
        "processing_metadata": file.processing_metadata,
    }


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> FileResponse:
    """
    Download file by ID.

    Args:
        file_id: File ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        FileResponse with the file
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get file
    file_service = FileService(db)
    file = await file_service.get_file_by_id(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Security check: user can only download their own files or public files
    if file.user_id != current_user.id and not file.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. File is not public and does not belong to you.",
        )

    # Check if file exists on disk
    import os

    if not os.path.exists(file.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk"
        )

    # Increment download count
    file_service.increment_download_count(file_id)

    # Return file response
    return FileResponse(
        path=file.file_path,
        filename=file.original_filename,
        media_type=file.content_type,
    )


@router.put("/files/{file_id}")
async def update_file(
    file_id: int,
    is_public: Optional[bool] = None,
    tags: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Update file metadata.

    Args:
        file_id: File ID
        is_public: Whether the file should be publicly accessible
        tags: List of tags for the file
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with update status
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get file
    file_service = FileService(db)
    file = file_service.get_file_by_id(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Security check: user can only update their own files
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only update your own files.",
        )

    # Update file metadata
    updated_data = {}

    if is_public is not None:
        success = file_service.set_file_public(file_id, is_public)
        if success:
            updated_data["is_public"] = is_public

    if tags is not None:
        # Add new tags
        if len(tags) > 0:
            success = file_service.add_file_tags(file_id, tags)
            if success:
                updated_data["tags"] = tags

    return {
        "message": "File updated successfully",
        "file_id": file_id,
        "updated_fields": updated_data,
    }


@router.delete("/files/{file_id}")
async def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Delete file.

    Args:
        file_id: File ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with deletion status
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get file
    file_service = FileService(db)
    file = await file_service.get_file_by_id(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Security check: user can only delete their own files
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only delete your own files.",
        )

    # Delete the file
    success = await file_service.delete_file(file_id)

    if success:
        return {"message": "File deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file",
        )


@router.post("/files/{file_id}/process")
async def process_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Trigger file processing.

    Args:
        file_id: File ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with processing status
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get file
    file_service = FileService(db)
    file = file_service.get_file_by_id(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Security check: user can only process their own files
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only process your own files.",
        )

    # Check if file is already processed or processing
    if file.status in [FileStatus.PROCESSED, FileStatus.PROCESSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File is already {file.status}",
        )

    # Update file status to processing
    success = file_service.update_file_status(
        file_id=file_id,
        status=FileStatus.PROCESSING,
        metadata={"processing_started": True},
    )

    if success:
        return {
            "message": "File processing started",
            "file_id": file_id,
            "status": "processing",
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start file processing",
        )


@router.get("/files/{file_id}/status")
async def get_file_status(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Get file processing status.

    Args:
        file_id: File ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with file status information
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get file
    file_service = FileService(db)
    file = file_service.get_file_by_id(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Security check: user can only access their own files or public files
    if file.user_id != current_user.id and not file.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. File is not public and does not belong to you.",
        )

    return {
        "file_id": file_id,
        "status": file.status,
        "progress": 100 if file.status == FileStatus.PROCESSED else 0,
        "message": f"File {file.status}",
        "created_at": file.created_at.isoformat() if file.created_at else None,
        "processed_at": file.processed_at.isoformat() if file.processed_at else None,
    }


@router.get("/files/{file_id}/metadata")
async def get_file_metadata(
    file_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Get file processing metadata.

    Args:
        file_id: File ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with file metadata
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get file
    file_service = FileService(db)
    file = file_service.get_file_by_id(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Security check: user can only access their own files or public files
    if file.user_id != current_user.id and not file.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. File is not public and does not belong to you.",
        )

    return {
        "file_id": file_id,
        "processing_metadata": file.processing_metadata or {},
        "file_size": file.file_size,
        "content_type": file.content_type,
        "file_type": file.file_type,
        "checksum": file.checksum,
    }


@router.post("/files/{file_id}/tags")
async def add_file_tags(
    file_id: int,
    tags: List[str],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Add tags to file.

    Args:
        file_id: File ID
        tags: List of tags to add
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with update status
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get file
    file_service = FileService(db)
    file = file_service.get_file_by_id(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Security check: user can only modify their own files
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only modify your own files.",
        )

    # Add tags using FileService
    success = file_service.add_file_tags(file_id, tags)

    if success:
        return {"message": "Tags added successfully", "file_id": file_id, "tags": tags}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add tags",
        )


@router.delete("/files/{file_id}/tags")
async def remove_file_tags(
    file_id: int,
    tags: List[str],
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Remove tags from file.

    Args:
        file_id: File ID
        tags: List of tags to remove
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with update status
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get file
    file_service = FileService(db)
    file = file_service.get_file_by_id(file_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )

    # Security check: user can only modify their own files
    if file.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only modify your own files.",
        )

    # Remove tags using FileService
    success = file_service.remove_file_tags(file_id, tags)

    if success:
        return {
            "message": "Tags removed successfully",
            "file_id": file_id,
            "tags": tags,
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove tags",
        )


@router.get("/files/stats/overview")
async def get_file_stats(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """
    Get file statistics overview.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        Dict with file statistics
    """
    # Security check: ensure user is active
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated"
        )

    # Use FileService to get statistics
    file_service = FileService(db)
    stats = file_service.get_file_stats()

    # Add user-specific stats
    user_stats = file_service.get_storage_usage(current_user.id)

    return {
        **stats,
        "user_stats": user_stats,
    }
