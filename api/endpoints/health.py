"""
Health check and system information endpoints.
"""

import os
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.settings import settings
from models.api import HealthCheckResponse, ApiInfoResponse

router = APIRouter()

# Store startup time for uptime calculation
startup_time = time.time()


@router.get("/", response_model=ApiInfoResponse)
async def get_api_info() -> ApiInfoResponse:
    """Get API information and documentation links."""
    return ApiInfoResponse(
        name="Video Composition API",
        version="1.0.0",
        description="A powerful API for creating video compositions from images, audio, and video clips",
        documentation_url="/docs",
        supported_formats_url="/supported-formats",
        examples_url="/example-requests"
    )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> HealthCheckResponse:
    """
    Comprehensive health check endpoint.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - Disk space
    - Active jobs count
    """
    # Calculate uptime
    uptime = time.time() - startup_time
    
    # Check database connectivity
    database_connected = True
    try:
        await db.execute("SELECT 1")
    except Exception:
        database_connected = False
    
    # Check Redis connectivity
    redis_connected = True
    try:
        redis_client = request.app.state.redis
        await redis_client.ping()
    except Exception:
        redis_connected = False
    
    # Check disk space (in bytes)
    disk_space_available = 0
    try:
        statvfs = os.statvfs(settings.upload_dir)
        disk_space_available = statvfs.f_frsize * statvfs.f_bavail
    except Exception:
        pass
    
    # Get active jobs count (would be implemented with job service)
    active_jobs = 0
    try:
        # This would query the jobs table for active jobs
        pass
    except Exception:
        pass
    
    # Determine overall status
    status = "healthy"
    if not database_connected or not redis_connected:
        status = "degraded"
    if disk_space_available < 1024 * 1024 * 100:  # Less than 100MB
        status = "degraded"
    
    return HealthCheckResponse(
        status=status,
        version="1.0.0",
        uptime=uptime,
        database_connected=database_connected,
        redis_connected=redis_connected,
        disk_space_available=disk_space_available,
        active_jobs=active_jobs,
        timestamp=datetime.utcnow()
    )
