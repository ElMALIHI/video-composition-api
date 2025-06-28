"""
Service for video composition with URL and file support.
"""

import asyncio
import hashlib
import mimetypes
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiofiles
import aiohttp
from moviepy.editor import (
    AudioFileClip, CompositeVideoClip, ImageClip, VideoFileClip,
    concatenate_videoclips
)
from PIL import Image

from core.settings import settings
from models.api import (
    CompositionSettings, MediaType, SceneData, TransitionType, VideoFormat,
    VideoQuality
)


class VideoCompositionService:
    """Service for creating video compositions from scenes."""
    
    # Quality mapping to resolution
    QUALITY_RESOLUTIONS = {
        VideoQuality.SD: (640, 480),
        VideoQuality.HD: (1280, 720),
        VideoQuality.FHD: (1920, 1080),
        VideoQuality.QHD: (2560, 1440),
        VideoQuality.UHD: (3840, 2160),
        VideoQuality.LOW: (640, 480),
        VideoQuality.MEDIUM: (1280, 720),
        VideoQuality.HIGH: (1920, 1080),
        VideoQuality.ULTRA: (3840, 2160),
    }
    
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "video_composition"
        self.temp_dir.mkdir(exist_ok=True)
    
    async def download_media_from_url(self, url: str) -> Path:
        """Download media from URL to temporary file."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise ValueError(f"Failed to download from {url}: HTTP {response.status}")
                    
                    # Get content type and determine file extension
                    content_type = response.headers.get('content-type', '')
                    extension = mimetypes.guess_extension(content_type) or '.tmp'
                    
                    # Create temporary file
                    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                    temp_file = self.temp_dir / f"download_{url_hash}{extension}"
                    
                    # Download and save file
                    async with aiofiles.open(temp_file, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            await f.write(chunk)
                    
                    return temp_file
                    
            except Exception as e:
                raise ValueError(f"Failed to download media from {url}: {str(e)}")
    
    def is_url(self, source: str) -> bool:
        """Check if source is a URL."""
        try:
            result = urlparse(source)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    async def get_media_path(self, source: str, db_session=None) -> Path:
        """Get media path from either URL or file ID."""
        if self.is_url(source):
            return await self.download_media_from_url(source)
        else:
            # Assume it's a file ID - in real implementation, fetch from database
            # For now, return the source as-is (would need file service integration)
            from services.file_service import FileService
            file_service = FileService()
            # This would need API key context - simplified for now
            return Path(source)  # Placeholder
    
    async def create_clip_from_scene(
        self, 
        scene_name: str, 
        scene_data: SceneData, 
        target_resolution: Tuple[int, int],
        target_fps: int
    ) -> VideoFileClip:
        """Create a video clip from scene data."""
        media_path = await self.get_media_path(scene_data.source)
        
        try:
            if scene_data.media_type in [MediaType.IMAGE, MediaType.IMAGE_VIDEO]:
                # Try to load as image first
                try:
                    # Verify it's actually an image
                    with Image.open(media_path) as img:
                        img.verify()
                    
                    # Create image clip
                    clip = ImageClip(str(media_path), duration=scene_data.duration)
                    clip = clip.resize(target_resolution)
                    clip = clip.set_fps(target_fps)
                    
                except Exception:
                    # If image loading fails and media_type allows video, try video
                    if scene_data.media_type == MediaType.IMAGE_VIDEO:
                        clip = VideoFileClip(str(media_path))
                        clip = clip.subclip(0, min(scene_data.duration, clip.duration))
                        clip = clip.resize(target_resolution)
                        if clip.fps != target_fps:
                            clip = clip.set_fps(target_fps)
                    else:
                        raise
            
            elif scene_data.media_type == MediaType.VIDEO:
                # Load as video
                clip = VideoFileClip(str(media_path))
                clip = clip.subclip(0, min(scene_data.duration, clip.duration))
                clip = clip.resize(target_resolution)
                if clip.fps != target_fps:
                    clip = clip.set_fps(target_fps)
            
            else:
                raise ValueError(f"Unsupported media type: {scene_data.media_type}")
            
            return clip
            
        except Exception as e:
            raise ValueError(f"Failed to create clip from {scene_name}: {str(e)}")
    
    def apply_transition(
        self, 
        clip1: VideoFileClip, 
        clip2: VideoFileClip, 
        transition: TransitionType, 
        duration: float = 0.5
    ) -> VideoFileClip:
        """Apply transition between two clips."""
        if transition == TransitionType.NONE:
            return concatenate_videoclips([clip1, clip2])
        
        elif transition == TransitionType.FADE:
            # Apply fade out to first clip and fade in to second clip
            clip1_faded = clip1.fadeout(duration)
            clip2_faded = clip2.fadein(duration)
            return concatenate_videoclips([clip1_faded, clip2_faded])
        
        elif transition == TransitionType.CROSSFADE:
            # Overlap clips with crossfade
            if duration > min(clip1.duration, clip2.duration):
                duration = min(clip1.duration, clip2.duration) * 0.5
            
            clip1_fade = clip1.fadeout(duration)
            clip2_fade = clip2.fadein(duration).set_start(clip1.duration - duration)
            
            return CompositeVideoClip([clip1_fade, clip2_fade])
        
        elif transition == TransitionType.SLIDE_LEFT:
            # Simple slide transition (basic implementation)
            clip2_slide = clip2.set_position(lambda t: (max(0, clip2.w - clip2.w * t/duration), 0))
            clip2_positioned = clip2_slide.set_start(clip1.duration).set_duration(duration)
            return CompositeVideoClip([clip1, clip2_positioned]).set_duration(clip1.duration + duration)
        
        # Add more transition types as needed
        else:
            # Default to concatenation for unsupported transitions
            return concatenate_videoclips([clip1, clip2])
    
    async def compose_video(
        self,
        scenes: Dict[str, SceneData],
        output_format: VideoFormat,
        quality: VideoQuality,
        fps: int,
        composition_settings: CompositionSettings,
        progress_callback: Optional[callable] = None
    ) -> Path:
        """
        Compose video from scenes.
        
        Args:
            scenes: Dictionary of scene names to scene data
            output_format: Output video format
            quality: Video quality/resolution
            fps: Frames per second
            composition_settings: Composition settings
            progress_callback: Optional callback for progress updates
        
        Returns:
            Path to the composed video file
        """
        try:
            # Get target resolution
            target_resolution = self.QUALITY_RESOLUTIONS.get(quality, (1920, 1080))
            
            if progress_callback:
                await progress_callback("Creating clips from scenes", 10)
            
            # Create clips for each scene
            clips = []
            scene_items = list(scenes.items())
            
            for i, (scene_name, scene_data) in enumerate(scene_items):
                if progress_callback:
                    progress = 10 + (i / len(scene_items)) * 50
                    await progress_callback(f"Processing scene: {scene_name}", progress)
                
                clip = await self.create_clip_from_scene(
                    scene_name, scene_data, target_resolution, fps
                )
                clips.append((clip, scene_data.transition))
            
            if progress_callback:
                await progress_callback("Applying transitions", 70)
            
            # Apply transitions between clips
            final_clips = []
            for i, (clip, transition) in enumerate(clips):
                if i == 0:
                    final_clips.append(clip)
                else:
                    prev_clip = final_clips[-1]
                    if transition != TransitionType.NONE:
                        # Apply transition between previous and current clip
                        transitioned = self.apply_transition(prev_clip, clip, transition)
                        final_clips[-1] = transitioned
                    else:
                        final_clips.append(clip)
            
            if progress_callback:
                await progress_callback("Concatenating video", 80)
            
            # Concatenate all clips
            if len(final_clips) == 1:
                final_video = final_clips[0]
            else:
                final_video = concatenate_videoclips(final_clips, method="compose")
            
            # Apply composition settings
            if composition_settings.background_color != "black":
                # This would require more complex implementation for background colors
                pass
            
            if progress_callback:
                await progress_callback("Rendering final video", 90)
            
            # Generate output filename
            output_filename = f"composition_{os.urandom(6).hex()}.{output_format.value}"
            output_path = settings.output_dir / output_filename
            
            # Set up codec and quality settings
            codec_settings = {
                VideoFormat.MP4: {
                    "codec": "libx264",
                    "audio_codec": "aac",
                    "preset": "medium"
                },
                VideoFormat.WEBM: {
                    "codec": "libvpx-vp9",
                    "audio_codec": "libvorbis"
                },
                VideoFormat.AVI: {
                    "codec": "libxvid",
                    "audio_codec": "mp3"
                },
                VideoFormat.MOV: {
                    "codec": "libx264",
                    "audio_codec": "aac"
                },
                VideoFormat.GIF: {
                    "program": "ffmpeg",
                    "fps": min(fps, 15)  # Limit GIF FPS
                }
            }
            
            settings_for_format = codec_settings.get(output_format, codec_settings[VideoFormat.MP4])
            
            # Write video file
            if output_format == VideoFormat.GIF:
                final_video.write_gif(
                    str(output_path),
                    fps=settings_for_format["fps"],
                    program=settings_for_format["program"]
                )
            else:
                final_video.write_videofile(
                    str(output_path),
                    fps=fps,
                    **settings_for_format
                )
            
            if progress_callback:
                await progress_callback("Video composition complete", 100)
            
            # Clean up clips
            for clip, _ in clips:
                clip.close()
            final_video.close()
            
            return output_path
            
        except Exception as e:
            raise ValueError(f"Video composition failed: {str(e)}")
    
    async def cleanup_temp_files(self):
        """Clean up temporary downloaded files."""
        try:
            for file_path in self.temp_dir.glob("download_*"):
                file_path.unlink()
        except Exception:
            pass  # Ignore cleanup errors
