"""VideoSource model for input video files."""

from typing import Optional, Tuple
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class VideoSource(BaseModel):
    """Represents an input MP4 video file to be processed.

    Attributes:
        video_id: Unique identifier for this video source
        file_path: Absolute path to input video file
        duration_seconds: Total video duration in seconds
        resolution: Video resolution (width, height)
        frame_rate: Frames per second
        has_audio: Whether video contains audio track
        audio_codec: Audio codec (e.g., "aac", "mp3")
        video_codec: Video codec (e.g., "h264")
        file_size_bytes: File size in bytes
        srt_file_path: Path to GPS-enabled SRT subtitle file (optional)
        file_timestamp: File creation/modification timestamp for chronological ordering
    """

    video_id: str = Field(..., description="Unique ID for this video source")
    file_path: str = Field(..., description="Absolute path to input video file")
    duration_seconds: float = Field(..., gt=0, description="Total video duration in seconds")
    resolution: Tuple[int, int] = Field(..., description="Video resolution (width, height)")
    frame_rate: float = Field(..., gt=0, description="Frames per second")
    has_audio: bool = Field(..., description="Whether video contains audio track")
    audio_codec: Optional[str] = Field(None, description="Audio codec")
    video_codec: Optional[str] = Field(None, description="Video codec")
    file_size_bytes: int = Field(..., ge=0, description="File size in bytes")
    srt_file_path: Optional[str] = Field(None, description="Path to GPS SRT file")
    file_timestamp: float = Field(..., description="File timestamp for chronological ordering")

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate that file path has .mp4 extension."""
        if not v.lower().endswith('.mp4'):
            raise ValueError("File must be MP4 format")
        return v

    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v: Tuple[int, int]) -> Tuple[int, int]:
        """Validate resolution dimensions."""
        width, height = v
        if width <= 0 or height <= 0:
            raise ValueError("Resolution dimensions must be positive")
        # Support up to 4K (3840x2160)
        if width > 3840 or height > 2160:
            raise ValueError("Resolution must not exceed 3840x2160 (4K)")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "video-001",
                "file_path": "/path/to/drone_video_1.mp4",
                "duration_seconds": 3600.5,
                "resolution": [1920, 1080],
                "frame_rate": 30.0,
                "has_audio": True,
                "audio_codec": "aac",
                "video_codec": "h264",
                "file_size_bytes": 2684354560,
                "srt_file_path": "/path/to/drone_video_1.srt",
                "file_timestamp": 1729872000.0
            }
        }
