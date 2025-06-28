"""
Service for job management.
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.api import JobResponse, JobListQuery, JobStatus, JobPriority
from models.database import Job


class JobService:
    """Service for managing video composition jobs."""
    
    async def create_job(
        self,
        db: AsyncSession,
        api_key: str,
        title: Optional[str],
        description: Optional[str],
        composition_config: dict,
        priority: JobPriority = JobPriority.NORMAL,
        webhook_url: Optional[str] = None
    ) -> JobResponse:
        """Create a new job record."""
        job = Job(
            api_key=api_key,
            title=title or "Untitled Composition",
            description=description,
            composition_config=json.dumps(composition_config),
            priority=priority,
            webhook_url=webhook_url,
            
            # Default values
            status=JobStatus.PENDING,
            progress=0.0,
            retry_count=0,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=7)  # Default expiration
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        return self._to_job_response(job)
    
    async def get_job(self, db: AsyncSession, job_id: str, api_key: str) -> Optional[JobResponse]:
        """Retrieve a job by ID and API key."""
        result = await db.execute(
            select(Job).where(
                Job.id == job_id,
                Job.api_key == api_key
            )
        )
        job = result.scalar_one_or_none()
        
        return self._to_job_response(job) if job else None
    
    async def list_jobs(
        self,
        db: AsyncSession,
        api_key: str,
        query: JobListQuery
    ) -> List[JobResponse]:
        """List jobs for an API key with optional filtering and pagination."""
        stmt = select(Job).where(Job.api_key == api_key)
        
        if query.status:
            stmt = stmt.where(Job.status == query.status)
        if query.priority:
            stmt = stmt.where(Job.priority == query.priority)
        
        if query.sort_order == "asc":
            stmt = stmt.order_by(getattr(Job, query.sort_by).asc())
        else:
            stmt = stmt.order_by(getattr(Job, query.sort_by).desc())
        
        result = await db.execute(
            stmt.limit(query.per_page).offset((query.page - 1) * query.per_page)
        )
        jobs = result.scalars().all()
        
        return [self._to_job_response(job) for job in jobs]
    
    def _to_job_response(self, job: Job) -> JobResponse:
        """Convert a Job model to a JobResponse model."""
        return JobResponse(
            id=job.id,
            status=job.status,
            priority=job.priority,
            title=job.title,
            description=job.description,
            progress=job.progress,
            current_step=job.current_step,
            total_steps=job.total_steps,
            output_file=job.output_file,
            output_format=job.output_format,
            output_size=job.output_size,
            duration=job.duration,
            error_message=job.error_message,
            retry_count=job.retry_count,
            max_retries=job.max_retries,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            expires_at=job.expires_at,
            webhook_url=job.webhook_url,
            webhook_sent=job.webhook_sent
        )
    
    async def update_job_status(
        self, db: AsyncSession, job_id: str, api_key: str, status: JobStatus
    ) -> bool:
        """Update the status of an existing job."""
        try:
            result = await db.execute(
                select(Job).where(
                    Job.id == job_id,
                    Job.api_key == api_key
                )
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return False
            
            job.status = status
            job.updated_at = datetime.utcnow()
            
            # If job is finished, set completion time
            if status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                job.completed_at = datetime.utcnow()
            
            await db.commit()
            return True
            
        except Exception as e:
            import logging
            logging.error(f"Failed to update status for job {job_id}: {e}")
            return False
    
    async def delete_job(self, db: AsyncSession, job_id: str, api_key: str) -> bool:
        """Delete a job and all associated resources."""
        try:
            result = await db.execute(
                select(Job).where(
                    Job.id == job_id,
                    Job.api_key == api_key
                )
            )
            job = result.scalar_one_or_none()
            
            if not job:
                return False
            
            await db.delete(job)
            await db.commit()
            return True
            
        except Exception as e:
            import logging
            logging.error(f"Failed to delete job {job_id}: {e}")
            return False
    
    async def cleanup_expired_jobs(self, db: AsyncSession):
        """Clean up expired jobs from the database."""
        expired_jobs = await db.execute(
            select(Job).where(
                Job.expires_at < datetime.utcnow()
            )
        )
        
        for job in expired_jobs.scalars():
            try:
                await db.delete(job)
            except Exception as e:
                import logging
                logging.warning(f"Failed to clean up expired job {job.id}: {e}")
        
        await db.commit()
