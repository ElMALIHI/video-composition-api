"""
File upload and management service.
"""

import hashlib
import json
import mimetypes
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiofiles
from fastapi import HTTPException, UploadFile, status
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.settings import settings
from models.api import FileInfo, FileType
from models.database import UploadedFile


class FileService:
    """Service for handling file uploads and management."""
    
    # Supported file types and extensions
    SUPPORTED_TYPES = {
        FileType.IMAGE: {
            'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff'],
            'mime_types': [
                'image/jpeg', 'image/png', 'image/gif', 'image/bmp',
                'image/webp', 'image/tiff'
            ],
            'max_size': 50 * 1024 * 1024  # 50MB
        },
        FileType.VIDEO: {
            'extensions': ['.mp4', '.avi', '.mov', '.webm', '.mkv', '.flv'],
            'mime_types': [
                'video/mp4', 'video/x-msvideo', 'video/quicktime',
                'video/webm', 'video/x-matroska', 'video/x-flv'
            ],
            'max_size': 500 * 1024 * 1024  # 500MB
        },
        FileType.AUDIO: {
            'extensions': ['.mp3', '.wav', '.aac', '.ogg', '.flac', '.m4a'],
            'mime_types': [
                'audio/mpeg', 'audio/wav', 'audio/aac', 'audio/ogg',
                'audio/flac', 'audio/mp4'
            ],
            'max_size': 100 * 1024 * 1024  # 100MB
        }
    }
    
    def __init__(self):
        self.upload_dir = settings.upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_type(self, filename: str, mime_type: str) -> Optional[FileType]:
        """Determine file type from filename and MIME type."""
        extension = Path(filename).suffix.lower()
        
        for file_type, config in self.SUPPORTED_TYPES.items():
            if (extension in config['extensions'] or 
                mime_type in config['mime_types']):
                return file_type
        
        return None
    
    def _validate_file(self, upload_file: UploadFile) -> Tuple[FileType, Dict]:
        """
        Validate uploaded file.
        
        Returns:
            tuple: (file_type, validation_info)
        
        Raises:
            HTTPException: If file is invalid
        """
        # Check file size
        if upload_file.size and upload_file.size > settings.upload_max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {settings.upload_max_size} bytes"
            )
        
        # Determine file type
        mime_type = upload_file.content_type or mimetypes.guess_type(upload_file.filename)[0] or ""
        file_type = self._get_file_type(upload_file.filename, mime_type)
        
        if not file_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {upload_file.filename}"
            )
        
        # Check type-specific size limits
        type_config = self.SUPPORTED_TYPES[file_type]
        if upload_file.size and upload_file.size > type_config['max_size']:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large for {file_type.value}. Maximum size: {type_config['max_size']} bytes"
            )
        
        return file_type, {
            'mime_type': mime_type,
            'size': upload_file.size,
            'original_filename': upload_file.filename
        }
    
    async def _save_file(self, upload_file: UploadFile, file_id: str, api_key: str) -> Path:
        """Save uploaded file to disk."""
        # Create directory structure: uploads/{api_key_hash}/{date}/{file_id}
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        
        file_dir = self.upload_dir / api_key_hash / date_str
        file_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        extension = Path(upload_file.filename).suffix.lower()
        filename = f"{file_id}{extension}"
        file_path = file_dir / filename
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await upload_file.read()
            await f.write(content)
        
        return file_path
    
    async def _get_file_metadata(self, file_path: Path, file_type: FileType) -> Dict:
        """Extract metadata from uploaded file."""
        metadata = {}
        
        try:
            if file_type == FileType.IMAGE:
                metadata = await self._get_image_metadata(file_path)
            elif file_type == FileType.VIDEO:
                metadata = await self._get_video_metadata(file_path)
            elif file_type == FileType.AUDIO:
                metadata = await self._get_audio_metadata(file_path)
        except Exception as e:
            # Don't fail upload if metadata extraction fails
            import logging
            logging.warning(f"Failed to extract metadata from {file_path}: {e}")
        
        return metadata
    
    async def _get_image_metadata(self, file_path: Path) -> Dict:
        """Extract image metadata."""
        try:
            with Image.open(file_path) as img:
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode
                }
        except Exception:
            return {}
    
    async def _get_video_metadata(self, file_path: Path) -> Dict:
        """Extract video metadata using moviepy."""
        try:
            from moviepy.editor import VideoFileClip
            
            with VideoFileClip(str(file_path)) as clip:
                return {
                    'width': clip.w,
                    'height': clip.h,
                    'duration': clip.duration,
                    'fps': clip.fps
                }
        except Exception:
            return {}
    
    async def _get_audio_metadata(self, file_path: Path) -> Dict:
        """Extract audio metadata."""
        try:
            from moviepy.editor import AudioFileClip
            
            with AudioFileClip(str(file_path)) as clip:
                return {
                    'duration': clip.duration
                }
        except Exception:
            return {}
    
    async def _calculate_file_hashes(self, file_path: Path) -> Tuple[str, str]:
        """Calculate MD5 and SHA256 hashes for file integrity."""
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()
        
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(8192):
                md5_hash.update(chunk)
                sha256_hash.update(chunk)
        
        return md5_hash.hexdigest(), sha256_hash.hexdigest()
    
    async def upload_file(
        self,
        db: AsyncSession,
        upload_file: UploadFile,
        api_key: str
    ) -> FileInfo:
        """
        Upload and process a single file.
        
        Args:
            db: Database session
            upload_file: FastAPI UploadFile object
            api_key: API key for the request
        
        Returns:
            FileInfo: Information about the uploaded file
        """
        # Validate file
        file_type, validation_info = self._validate_file(upload_file)
        
        # Generate file ID
        file_id = str(uuid.uuid4())
        
        # Save file to disk
        file_path = await self._save_file(upload_file, file_id, api_key)
        
        try:
            # Get file metadata
            metadata = await self._get_file_metadata(file_path, file_type)
            
            # Calculate file hashes
            md5_hash, sha256_hash = await self._calculate_file_hashes(file_path)
            
            # Create database record
            db_file = UploadedFile(
                id=file_id,
                api_key=hashlib.sha256(api_key.encode()).hexdigest()[:16],
                filename=file_path.name,
                original_filename=validation_info['original_filename'],
                file_path=str(file_path),
                file_type=file_type,
                mime_type=validation_info['mime_type'],
                file_size=file_path.stat().st_size,
                metadata_json=json.dumps(metadata) if metadata else None,  # Changed from metadata
                width=metadata.get('width'),
                height=metadata.get('height'),
                duration=metadata.get('duration'),
                fps=metadata.get('fps'),
                md5_hash=md5_hash,
                sha256_hash=sha256_hash,
                expires_at=datetime.utcnow() + timedelta(days=30)  # 30 day retention
            )
            
            db.add(db_file)
            await db.commit()
            await db.refresh(db_file)
            
            return FileInfo(
                id=db_file.id,
                filename=db_file.filename,
                original_filename=db_file.original_filename,
                file_type=db_file.file_type,
                mime_type=db_file.mime_type,
                file_size=db_file.file_size,
                width=db_file.width,
                height=db_file.height,
                duration=db_file.duration,
                fps=db_file.fps,
                created_at=db_file.created_at
            )
            
        except Exception as e:
            # Clean up file if database operation fails
            try:
                file_path.unlink()
            except:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process uploaded file: {str(e)}"
            )
    
    async def upload_multiple_files(
        self,
        db: AsyncSession,
        upload_files: List[UploadFile],
        api_key: str
    ) -> Tuple[List[FileInfo], List[Dict[str, str]]]:
        """
        Upload and process multiple files.
        
        Args:
            db: Database session
            upload_files: List of FastAPI UploadFile objects
            api_key: API key for the request
        
        Returns:
            tuple: (successful_uploads, failed_uploads)
        """
        successful_uploads = []
        failed_uploads = []
        
        for upload_file in upload_files:
            try:
                file_info = await self.upload_file(db, upload_file, api_key)
                successful_uploads.append(file_info)
            except HTTPException as e:
                failed_uploads.append({
                    'filename': upload_file.filename,
                    'error': e.detail
                })
            except Exception as e:
                failed_uploads.append({
                    'filename': upload_file.filename,
                    'error': str(e)
                })
        
        return successful_uploads, failed_uploads
    
    async def get_file(self, db: AsyncSession, file_id: str, api_key: str) -> Optional[UploadedFile]:
        """Get file information by ID and API key."""
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        result = await db.execute(
            select(UploadedFile).where(
                UploadedFile.id == file_id,
                UploadedFile.api_key == api_key_hash
            )
        )
        
        return result.scalar_one_or_none()
    
    async def get_file_path(self, db: AsyncSession, file_id: str, api_key: str) -> Optional[Path]:
        """Get file system path for a file."""
        file_record = await self.get_file(db, file_id, api_key)
        if not file_record:
            return None
        
        file_path = Path(file_record.file_path)
        if not file_path.exists():
            return None
        
        # Update last accessed time
        file_record.last_accessed = datetime.utcnow()
        await db.commit()
        
        return file_path
    
    async def delete_file(self, db: AsyncSession, file_id: str, api_key: str) -> bool:
        """Delete a file and its database record."""
        file_record = await self.get_file(db, file_id, api_key)
        if not file_record:
            return False
        
        # Delete physical file
        try:
            file_path = Path(file_record.file_path)
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass  # Continue even if file deletion fails
        
        # Delete database record
        await db.delete(file_record)
        await db.commit()
        
        return True
    
    async def cleanup_expired_files(self, db: AsyncSession):
        """Clean up expired files from storage and database."""
        expired_files = await db.execute(
            select(UploadedFile).where(
                UploadedFile.expires_at < datetime.utcnow()
            )
        )
        
        for file_record in expired_files.scalars():
            try:
                # Delete physical file
                file_path = Path(file_record.file_path)
                if file_path.exists():
                    file_path.unlink()
                
                # Delete database record
                await db.delete(file_record)
                
            except Exception as e:
                import logging
                logging.warning(f"Failed to clean up expired file {file_record.id}: {e}")
        
        await db.commit()
    
    def get_supported_formats(self) -> Dict:
        """Get information about supported file formats."""
        formats = {}
        
        for file_type, config in self.SUPPORTED_TYPES.items():
            formats[f"{file_type.value}_formats"] = {
                'extensions': config['extensions'],
                'mime_types': config['mime_types'],
                'max_size': config['max_size']
            }
        
        return formats
