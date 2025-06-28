"""
Application settings with environment variable support.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Configuration
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    api_keys: List[str] = Field(
        default_factory=list, description="List of valid API keys"
    )
    secret_key: str = Field(
        default="change-this-secret-key", description="Secret key for encryption"
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"], description="CORS allowed origins"
    )

    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./dev.db",
        description="Database connection URL",
    )
    database_url_dev: Optional[str] = Field(
        default=None, description="Development database URL"
    )

    # Redis Configuration
    redis_url: str = Field(
        default="redis://localhost:6379/0", description="Redis connection URL"
    )

    # File Upload Configuration
    upload_max_size: int = Field(
        default=104857600, description="Maximum upload size in bytes (100MB)"
    )
    upload_dir: Path = Field(
        default=Path("./uploads"), description="Upload directory path"
    )
    output_dir: Path = Field(
        default=Path("./outputs"), description="Output directory path"
    )

    # Job Configuration
    job_timeout: int = Field(
        default=3600, description="Job timeout in seconds (1 hour)"
    )
    max_concurrent_jobs: int = Field(
        default=5, description="Maximum concurrent jobs"
    )

    # Rate Limiting
    rate_limit_requests: int = Field(
        default=100, description="Rate limit requests per window"
    )
    rate_limit_window: int = Field(
        default=3600, description="Rate limit window in seconds (1 hour)"
    )

    # Webhook Configuration
    webhook_secret: Optional[str] = Field(
        default=None, description="Webhook secret key"
    )
    webhook_timeout: int = Field(
        default=30, description="Webhook timeout in seconds"
    )

    # Monitoring
    metrics_enabled: bool = Field(
        default=True, description="Enable metrics collection"
    )
    health_check_timeout: int = Field(
        default=30, description="Health check timeout in seconds"
    )

    # Video Processing Defaults
    default_video_quality: str = Field(
        default="medium", description="Default video quality"
    )
    default_video_format: str = Field(
        default="mp4", description="Default video format"
    )
    default_resolution: str = Field(
        default="1920x1080", description="Default video resolution"
    )
    default_fps: int = Field(default=30, description="Default video FPS")

    # FFmpeg Configuration
    ffmpeg_binary: str = Field(default="ffmpeg", description="FFmpeg binary path")

    @field_validator("api_keys", mode="before")
    @classmethod
    def parse_api_keys(cls, v):
        """Parse comma-separated API keys."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse comma-separated CORS origins."""
        if isinstance(v, str):
            # Handle JSON-like string format
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated format
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("upload_dir", "output_dir", mode="before")
    @classmethod
    def ensure_path(cls, v):
        """Ensure path values are Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v

    def create_directories(self):
        """Create necessary directories if they don't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug or "dev" in self.database_url.lower()

    @property
    def effective_database_url(self) -> str:
        """Get the effective database URL based on environment."""
        if self.is_development and self.database_url_dev:
            return self.database_url_dev
        return self.database_url


# Global settings instance
settings = Settings()

# Create directories on import
settings.create_directories()
