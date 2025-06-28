"""
Database models.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, Text, Integer, Float, Boolean, DateTime, func
from sqlalchemy.orm import mapped_column, Mapped

from core.database import Base
from models.api import JobStatus, JobPriority, FileType


class Job(Base):
    """Model for representing video composition jobs."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    api_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[JobStatus] = mapped_column(
        String(20), default=JobStatus.PENDING, nullable=False, index=True
    )
    priority: Mapped[JobPriority] = mapped_column(
        String(10), default=JobPriority.NORMAL, nullable=False
    )
    
    # Composition configuration (stored as JSON)
    composition_config: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Job metadata
    title: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Progress tracking
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_step: Mapped[Optional[str]] = mapped_column(String(255))
    total_steps: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Results
    output_file: Mapped[Optional[str]] = mapped_column(String(500))
    output_format: Mapped[Optional[str]] = mapped_column(String(10))
    output_size: Mapped[Optional[int]] = mapped_column(Integer)  # File size in bytes
    duration: Mapped[Optional[float]] = mapped_column(Float)  # Video duration in seconds
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_details: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    
    # Webhook configuration
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500))
    webhook_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    webhook_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Job {self.id} - {self.status}>"

    @property
    def is_processing(self) -> bool:
        """Check if job is currently being processed."""
        return self.status in (JobStatus.QUEUED, JobStatus.PROCESSING)

    @property
    def is_finished(self) -> bool:
        """Check if job is finished (completed, failed, or cancelled)."""
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)

    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (
            self.status == JobStatus.FAILED
            and self.retry_count < self.max_retries
        )


class UploadedFile(Base):
    """Model for tracking uploaded files."""

    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    api_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[FileType] = mapped_column(String(10), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # File metadata (stored as JSON)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)
    
    # Media-specific properties
    width: Mapped[Optional[int]] = mapped_column(Integer)
    height: Mapped[Optional[int]] = mapped_column(Integer)
    duration: Mapped[Optional[float]] = mapped_column(Float)
    fps: Mapped[Optional[float]] = mapped_column(Float)
    
    # Checksums for integrity
    md5_hash: Mapped[Optional[str]] = mapped_column(String(32))
    sha256_hash: Mapped[Optional[str]] = mapped_column(String(64))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<UploadedFile {self.id} - {self.filename}>"


class JobFile(Base):
    """Association table for jobs and their associated files."""

    __tablename__ = "job_files"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    file_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    
    # Usage context
    usage_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'input', 'output', 'temp'
    scene_index: Mapped[Optional[int]] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<JobFile {self.job_id} - {self.file_id}>"


class ApiKeyUsage(Base):
    """Model for tracking API key usage and rate limiting."""

    __tablename__ = "api_key_usage"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    api_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Usage tracking
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Request metadata
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    
    # Resource usage
    file_size_uploaded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processing_time: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<ApiKeyUsage {self.api_key} - {self.endpoint}>"
