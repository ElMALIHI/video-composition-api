"""
Job management endpoints for video composition.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from models.api import (
    JobListQuery, JobListResponse, JobResponse, JobSubmissionResponse,
    VideoCompositionRequest
)
from services.auth import check_rate_limit, get_api_key
from services.job_service import JobService
from services.video_service import VideoCompositionService

router = APIRouter()
job_service = JobService()
video_service = VideoCompositionService()


@router.post("/compose", response_model=JobSubmissionResponse)
async def submit_composition_job(
    request: Request,
    composition_request: VideoCompositionRequest,
    api_key: str = Depends(get_api_key),
    rate_limit_info: dict = Depends(check_rate_limit),
    db: AsyncSession = Depends(get_db)
) -> JobSubmissionResponse:
    """
    Submit a video composition job with the new format.
    
    Expected request body:
    {
      "scenes": {
        "Scene 1": {
          "source": "https://example.com/image.jpg",
          "media_type": "image/video",
          "duration": 3.0,
          "transition": "fade"
        },
        "Scene 2": {
          "source": "https://example.com/image2.jpg",
          "media_type": "image/video", 
          "duration": 5.0,
          "transition": "slide_left"
        }
      },
      "output_format": "mp4",
      "quality": "1080p",
      "fps": 30,
      "priority": "normal",
      "composition_settings": {
        "background_color": "black",
        "crossfade_audio": true
      },
      "webhook_url": null,
      "metadata": {}
    }
    """
    # Validate request
    if not composition_request.scenes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one scene is required"
        )
    
    # Create job title from scenes
    scene_names = list(composition_request.scenes.keys())
    title = f"Composition: {', '.join(scene_names[:3])}"
    if len(scene_names) > 3:
        title += f" and {len(scene_names) - 3} more scenes"
    
    # Calculate estimated duration
    total_duration = composition_request.get_total_duration()
    description = f"Video composition with {len(composition_request.scenes)} scenes, total duration: {total_duration:.1f}s"
    
    # Convert the request to a job
    job = await job_service.create_job(
        db=db,
        api_key=api_key,
        title=title,
        description=description,
        composition_config=composition_request.dict(),
        priority=composition_request.priority,
        webhook_url=str(composition_request.webhook_url) if composition_request.webhook_url else None
    )
    
    # TODO: Enqueue job for processing with video service
    # This would typically involve:
    # 1. Add job to Redis queue
    # 2. Background worker picks up job
    # 3. Worker calls video_service.compose_video()
    # 4. Worker updates job status and progress
    
    return JobSubmissionResponse(
        success=True,
        job=job,
        message=f"Video composition job submitted successfully. Total duration: {total_duration:.1f}s"
    )


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
) -> JobResponse:
    """
    Get the status and details of a specific job.
    """
    job = await job_service.get_job(db, job_id, api_key)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return job


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    query: JobListQuery = Depends(),
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
) -> JobListResponse:
    """
    List jobs for the authenticated API key.
    """
    jobs = await job_service.list_jobs(db, api_key, query)
    
    # TODO: Get total count for pagination
    total = len(jobs)  # Placeholder
    
    return JobListResponse(
        success=True,
        jobs=jobs,
        total=total,
        page=query.page,
        per_page=query.per_page
    )


@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: str,
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a job and all associated resources.
    """
    success = await job_service.delete_job(db, job_id, api_key)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return {"success": True, "message": "Job deleted successfully"}


# Additional endpoint to get job output/download
@router.get("/jobs/{job_id}/download")
async def download_job_result(
    job_id: str,
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Download the result of a completed job.
    """
    job = await job_service.get_job(db, job_id, api_key)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed. Current status: {job.status}"
        )
    
    if not job.output_file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job output file not found"
        )
    
    # TODO: Implement file download
    # This would typically return a FileResponse or redirect to download URL
    return {
        "download_url": f"/files/download/{job.output_file}",
        "filename": f"composition_{job_id}.{job.output_format}",
        "size": job.output_size,
        "format": job.output_format
    }


# Endpoint for processing job (would be called by background worker)
@router.post("/jobs/{job_id}/process")
async def process_job(
    job_id: str,
    api_key: str = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a job (internal endpoint for background workers).
    """
    job = await job_service.get_job(db, job_id, api_key)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    if job.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job cannot be processed. Current status: {job.status}"
        )
    
    try:
        # Update job status to processing
        await job_service.update_job_status(db, job_id, api_key, "processing")
        
        # Parse composition config
        import json
        composition_config = json.loads(job.composition_config) if isinstance(job.composition_config, str) else job.composition_config
        
        # Create progress callback
        async def progress_callback(message: str, progress: float):
            # Update job progress in database
            # This would be implemented in job_service
            pass
        
        # Process the video composition
        output_path = await video_service.compose_video(
            scenes=composition_config["scenes"],
            output_format=composition_config["output_format"],
            quality=composition_config["quality"],
            fps=composition_config["fps"],
            composition_settings=composition_config["composition_settings"],
            progress_callback=progress_callback
        )
        
        # Update job with results
        await job_service.update_job_status(db, job_id, api_key, "completed")
        # TODO: Update job with output_file, output_size, etc.
        
        return {
            "success": True,
            "message": "Job processed successfully",
            "output_file": str(output_path)
        }
        
    except Exception as e:
        # Update job status to failed
        await job_service.update_job_status(db, job_id, api_key, "failed")
        # TODO: Store error message in job
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job processing failed: {str(e)}"
        )
