"""
Main FastAPI application for Video Composition API.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from api.endpoints import files, health, jobs
from core.database import create_tables
from core.settings import settings
from models.api import ErrorResponse


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan events."""
    logger.info("Starting Video Composition API...")
    
    # Initialize database
    logger.info("Creating database tables...")
    await create_tables()
    
    # Initialize Redis connection
    logger.info("Connecting to Redis...")
    redis_client = redis.from_url(settings.redis_url)
    app.state.redis = redis_client
    
    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
    
    # Create necessary directories
    settings.create_directories()
    logger.info("Application startup complete")
    
    yield
    
    # Cleanup
    logger.info("Shutting down Video Composition API...")
    if hasattr(app.state, 'redis'):
        await app.state.redis.close()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Video Composition API",
    description="A powerful API for creating video compositions from images, audio, and video clips",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware in production
if not settings.debug:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure this properly for production
    )


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            success=False,
            message=exc.detail,
            error_code=f"HTTP_{exc.status_code}"
        ).dict()
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            success=False,
            message=str(exc),
            error_code="VALUE_ERROR"
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            message="An unexpected error occurred",
            error_code="INTERNAL_SERVER_ERROR",
            error_details={"type": type(exc).__name__} if settings.debug else None
        ).dict()
    )


# Request logging middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all requests and responses."""
    import time
    
    start_time = time.time()
    
    # Log request
    logger.info(f"{request.method} {request.url.path} - Started")
    
    # Process request
    response = await call_next(request)
    
    # Calculate response time
    process_time = time.time() - start_time
    
    # Log response
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    # Add response time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Rate limiting header middleware
@app.middleware("http")
async def rate_limit_headers_middleware(request: Request, call_next):
    """Add rate limiting headers to responses."""
    response = await call_next(request)
    
    # Add rate limiting headers if available
    if hasattr(request.state, 'rate_limit_info'):
        rate_info = request.state.rate_limit_info
        response.headers["X-RateLimit-Limit"] = str(rate_info.get("requests_limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(rate_info.get("requests_remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(int(rate_info.get("window_reset_time", 0).timestamp()) if rate_info.get("window_reset_time") else 0)
    
    return response


# Include routers
app.include_router(health.router, tags=["Health & Info"])
app.include_router(files.router, tags=["File Management"])
app.include_router(jobs.router, tags=["Job Management"])


# Additional endpoints
@app.get("/supported-formats")
async def get_supported_formats():
    """Get information about supported file formats."""
    from services.file_service import FileService
    file_service = FileService()
    return file_service.get_supported_formats()


@app.get("/example-requests")
async def get_example_requests():
    """Get example API requests for different endpoints."""
    examples = [
        {
            "endpoint": "/upload",
            "method": "POST",
            "description": "Upload a single file",
            "curl_example": '''curl -X POST "http://localhost:8000/upload" \\
  -H "Authorization: Bearer your-api-key" \\
  -F "file=@example.jpg"'''
        },
        {
            "endpoint": "/compose",
            "method": "POST",
            "description": "Submit a video composition job with new format",
            "curl_example": '''curl -X POST "http://localhost:8000/compose" \\
  -H "Authorization: Bearer your-api-key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "scenes": {
      "Scene 1": {
        "source": "https://i.ibb.co/Xxjt47yJ/generate.jpg",
        "media_type": "image/video",
        "duration": 3.0,
        "transition": "fade"
      },
      "Scene 2": {
        "source": "https://i.ibb.co/1GPcCXCB/generate.jpg", 
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
  }' '''
        },
        {
            "endpoint": "/jobs/{job_id}",
            "method": "GET",
            "description": "Get job status and progress",
            "curl_example": '''curl -H "Authorization: Bearer your-api-key" \\
  http://localhost:8000/jobs/your-job-id-here'''
        },
        {
            "endpoint": "/jobs/{job_id}/download",
            "method": "GET", 
            "description": "Download completed video",
            "curl_example": '''curl -H "Authorization: Bearer your-api-key" \\
  http://localhost:8000/jobs/your-job-id-here/download'''
        }
    ]
    return {"examples": examples}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
