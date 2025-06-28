"""
Pydantic models for API request/response schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, field_validator


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(str, Enum):
    """Job priority enumeration."""
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class FileType(str, Enum):
    """File type enumeration."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class MediaType(str, Enum):
    """Media type enumeration for scenes."""
    IMAGE = "image"
    VIDEO = "video"
    IMAGE_VIDEO = "image/video"  # For sources that could be either


class TransitionType(str, Enum):
    """Video transition types."""
    FADE = "fade"
    CROSSFADE = "crossfade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    NONE = "none"


class VideoQuality(str, Enum):
    """Video quality presets."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    # Resolution-based quality
    SD = "480p"
    HD = "720p"
    FHD = "1080p"
    QHD = "1440p"
    UHD = "4k"


class VideoFormat(str, Enum):
    """Supported video formats."""
    MP4 = "mp4"
    WEBM = "webm"
    AVI = "avi"
    MOV = "mov"
    GIF = "gif"


# Base response models
class BaseResponse(BaseModel):
    """Base response model."""
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseResponse):
    """Error response model."""
    success: bool = False
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


# File models
class FileInfo(BaseModel):
    """File information model."""
    id: str
    filename: str
    original_filename: str
    file_type: FileType
    mime_type: str
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    fps: Optional[float] = None
    created_at: datetime


class FileUploadResponse(BaseResponse):
    """File upload response."""
    file: FileInfo


class MultipleFileUploadResponse(BaseResponse):
    """Multiple file upload response."""
    files: List[FileInfo]
    failed_uploads: List[Dict[str, str]] = Field(default_factory=list)


# NEW: Scene model for the requested format
class SceneData(BaseModel):
    """Scene data configuration matching the new format."""
    source: str = Field(..., description="URL or file ID for the media source")
    media_type: MediaType = Field(..., description="Type of media (image, video, image/video)")
    duration: float = Field(..., gt=0, description="Scene duration in seconds")
    transition: TransitionType = Field(default=TransitionType.NONE, description="Transition effect")
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v):
        """Validate source is either a URL or file ID."""
        if not v:
            raise ValueError("Source cannot be empty")
        return v


# NEW: Composition settings
class CompositionSettings(BaseModel):
    """Composition settings for video processing."""
    background_color: str = Field(default="black", description="Background color for compositions")
    crossfade_audio: bool = Field(default=False, description="Enable audio crossfading between scenes")
    watermark_url: Optional[str] = Field(None, description="URL to watermark image")
    watermark_position: str = Field(default="bottom-right", description="Watermark position")
    watermark_opacity: float = Field(default=0.5, ge=0, le=1, description="Watermark opacity")
    
    @field_validator('background_color')
    @classmethod
    def validate_background_color(cls, v):
        """Validate background color format."""
        if v.startswith('#') and len(v) in [4, 7]:
            return v
        # Allow common color names
        common_colors = {
            'white', 'black', 'red', 'green', 'blue', 'yellow', 'cyan', 
            'magenta', 'orange', 'purple', 'pink', 'brown', 'gray', 'grey'
        }
        if v.lower() in common_colors:
            return v
        raise ValueError(f"Invalid color: {v}")


# NEW: Main composition request model
class VideoCompositionRequest(BaseModel):
    """Video composition request matching the new format."""
    scenes: Dict[str, SceneData] = Field(..., description="Dictionary of scene names to scene data")
    output_format: VideoFormat = Field(default=VideoFormat.MP4, description="Output video format")
    quality: VideoQuality = Field(default=VideoQuality.FHD, description="Video quality/resolution")
    fps: int = Field(default=30, ge=1, le=60, description="Frames per second")
    priority: JobPriority = Field(default=JobPriority.NORMAL, description="Job priority")
    composition_settings: CompositionSettings = Field(default_factory=CompositionSettings, description="Composition settings")
    webhook_url: Optional[HttpUrl] = Field(None, description="Webhook URL for job completion")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator('scenes')
    @classmethod
    def validate_scenes(cls, v):
        """Validate scenes dictionary."""
        if not v:
            raise ValueError("At least one scene is required")
        return v
    
    def get_total_duration(self) -> float:
        """Calculate total video duration."""
        return sum(scene.duration for scene in self.scenes.values())


# Legacy models for backward compatibility
class TextOverlay(BaseModel):
    """Text overlay configuration."""
    text: str = Field(..., description="Text content")
    x: float = Field(default=0.5, ge=0, le=1, description="X position (0-1)")
    y: float = Field(default=0.5, ge=0, le=1, description="Y position (0-1)")
    font_size: int = Field(default=48, ge=1, description="Font size in pixels")
    font_color: str = Field(default="white", description="Font color (name or hex)")
    font_family: str = Field(default="Arial", description="Font family")
    background_color: Optional[str] = Field(None, description="Background color")
    opacity: float = Field(default=1.0, ge=0, le=1, description="Text opacity")
    start_time: float = Field(default=0, ge=0, description="Start time in seconds")
    duration: Optional[float] = Field(None, ge=0, description="Duration in seconds")
    
    @field_validator('font_color', 'background_color')
    @classmethod
    def validate_color(cls, v):
        if v is None:
            return v
        # Simple validation for hex colors or named colors
        if v.startswith('#') and len(v) in [4, 7]:
            return v
        # Allow common color names
        common_colors = {
            'white', 'black', 'red', 'green', 'blue', 'yellow', 'cyan', 
            'magenta', 'orange', 'purple', 'pink', 'brown', 'gray', 'grey'
        }
        if v.lower() in common_colors:
            return v
        raise ValueError(f"Invalid color: {v}")


class ImageOverlay(BaseModel):
    """Image overlay configuration."""
    file_id: str = Field(..., description="ID of uploaded image file")
    x: float = Field(default=0, ge=0, le=1, description="X position (0-1)")
    y: float = Field(default=0, ge=0, le=1, description="Y position (0-1)")
    width: Optional[float] = Field(None, ge=0, le=1, description="Width (0-1)")
    height: Optional[float] = Field(None, ge=0, le=1, description="Height (0-1)")
    opacity: float = Field(default=1.0, ge=0, le=1, description="Image opacity")
    start_time: float = Field(default=0, ge=0, description="Start time in seconds")
    duration: Optional[float] = Field(None, ge=0, description="Duration in seconds")


# Legacy scene model (keeping for backward compatibility)
class Scene(BaseModel):
    """Legacy scene configuration for video composition."""
    duration: float = Field(..., gt=0, description="Scene duration in seconds")
    image_file_id: Optional[str] = Field(None, description="ID of image file")
    video_file_id: Optional[str] = Field(None, description="ID of video file")
    background_color: Optional[str] = Field(None, description="Background color")
    audio_file_id: Optional[str] = Field(None, description="ID of audio file for this scene")
    audio_volume: float = Field(default=1.0, ge=0, le=2, description="Audio volume multiplier")
    text_overlays: List[TextOverlay] = Field(default_factory=list)
    image_overlays: List[ImageOverlay] = Field(default_factory=list)
    transition: TransitionType = Field(default=TransitionType.NONE)
    transition_duration: float = Field(default=0.5, ge=0, description="Transition duration in seconds")
    
    @field_validator('background_color')
    @classmethod
    def validate_background_color(cls, v):
        if v is None:
            return v
        # Use same validation as text overlay colors
        return TextOverlay.validate_color(v)
    
    def model_validate(self):
        """Validate that at least one media source is provided."""
        if not any([self.image_file_id, self.video_file_id, self.background_color]):
            raise ValueError("Each scene must have at least one media source (image, video, or background color)")
        return self


# Job response models
class JobResponse(BaseModel):
    """Job status response."""
    id: str
    status: JobStatus
    priority: JobPriority
    title: Optional[str] = None
    description: Optional[str] = None
    
    # Progress information
    progress: float = Field(ge=0, le=100)
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    
    # Results
    output_file: Optional[str] = None
    output_format: Optional[str] = None
    output_size: Optional[int] = None
    duration: Optional[float] = None
    
    # Error information
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Timestamps
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Webhook
    webhook_url: Optional[str] = None
    webhook_sent: bool = False


class JobListResponse(BaseResponse):
    """Job list response."""
    jobs: List[JobResponse]
    total: int
    page: int = 1
    per_page: int = 50


class JobSubmissionResponse(BaseResponse):
    """Job submission response."""
    job: JobResponse


# System info models
class SupportedFormat(BaseModel):
    """Supported file format information."""
    extension: str
    mime_types: List[str]
    max_size: Optional[int] = None
    description: str


class SupportedFormatsResponse(BaseResponse):
    """Supported formats response."""
    image_formats: List[SupportedFormat]
    video_formats: List[SupportedFormat]
    audio_formats: List[SupportedFormat]
    output_formats: List[VideoFormat]


class HealthCheckResponse(BaseResponse):
    """Health check response."""
    status: str = "healthy"
    version: str
    uptime: float
    database_connected: bool
    redis_connected: bool
    disk_space_available: int
    active_jobs: int


class ApiInfoResponse(BaseResponse):
    """API information response."""
    name: str = "Video Composition API"
    version: str
    description: str
    documentation_url: str
    supported_formats_url: str
    examples_url: str


# Request query models
class JobListQuery(BaseModel):
    """Query parameters for job listing."""
    status: Optional[JobStatus] = None
    priority: Optional[JobPriority] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=50, ge=1, le=100)
    sort_by: str = Field(default="created_at")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


# Webhook models
class WebhookPayload(BaseModel):
    """Webhook payload for job completion."""
    event: str = "job.completed"
    job_id: str
    status: JobStatus
    timestamp: datetime
    data: JobResponse


# Example request models
class ExampleRequest(BaseModel):
    """Example API request."""
    endpoint: str
    method: str
    description: str
    payload: Dict[str, Any]
    curl_example: str


class ExampleRequestsResponse(BaseResponse):
    """Example requests response."""
    examples: List[ExampleRequest]


# Rate limiting models
class RateLimitInfo(BaseModel):
    """Rate limit information."""
    requests_remaining: int
    requests_limit: int
    window_reset_time: datetime
    window_duration: int
