"""
File handling endpoints for uploads, downloads, and file info.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.api import FileUploadResponse, MultipleFileUploadResponse
from services.auth import check_rate_limit, get_api_key
from services.file_service import FileService

router = APIRouter()
file_service = FileService()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    request: Request,
    file: UploadFile,
    api_key: str = Depends(get_api_key),
    rate_limit_info: dict = Depends(check_rate_limit),
    db: AsyncSession = Depends(get_db)
) -> FileUploadResponse:
    """
    Upload a single file (image/audio/video).
    """
    # Use file_service to upload the file
    file_info = await file_service.upload_file(db, file, api_key)
    
    return FileUploadResponse(
        success=True,
        file=file_info
    )


@router.post("/upload-multiple", response_model=MultipleFileUploadResponse)
async def upload_multiple_files(
    request: Request,
    files: list[UploadFile],
    api_key: str = Depends(get_api_key),
    rate_limit_info: dict = Depends(check_rate_limit),
    db: AsyncSession = Depends(get_db)
) -> MultipleFileUploadResponse:
    """
    Upload multiple files (image/audio/video).
    """
    successful_uploads, failed_uploads = await file_service.upload_multiple_files(db, files, api_key)
    
    if not successful_uploads:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="None of the files could be uploaded"
        )
    
    return MultipleFileUploadResponse(
        success=True,
        files=successful_uploads,
        failed_uploads=failed_uploads
    )
