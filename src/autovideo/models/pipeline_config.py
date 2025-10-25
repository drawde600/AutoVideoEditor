"""PipelineConfig model for user settings."""

from typing import List, Union
from pydantic import BaseModel, Field, field_validator, field_serializer
from pathlib import Path


class PipelineConfig(BaseModel):
    """User settings controlling pipeline behavior.

    Attributes:
        input_videos: Paths to one or more input videos
        output_directory: Output directory for results
        target_duration: Target highlight duration (seconds)
        min_quality_threshold: Minimum quality score (default 7.0)
        sample_rate_fps: Frame sampling rate (default 1.0)
        logging_verbosity: Logging level (minimal, moderate, detailed, verbose)
        resume_from_phase: Phase to resume from (1-5, default 1)
        checkpoint_directory: Where to save/load checkpoints
    """

    input_videos: List[str] = Field(..., description="Paths to input MP4 files")
    output_directory: Union[str, Path] = Field(default="./output", description="Output directory")
    target_duration: float = Field(..., gt=0, description="Target highlight duration (seconds)")
    min_quality_threshold: float = Field(default=7.0, ge=1.0, le=10.0, description="Min quality score")
    sample_rate_fps: float = Field(default=1.0, gt=0, description="Frame sampling rate")
    logging_verbosity: str = Field(default="detailed", description="Logging verbosity")
    resume_from_phase: int = Field(default=1, ge=1, le=5, description="Phase to resume from")
    checkpoint_directory: Union[str, Path] = Field(default="", description="Checkpoint directory")
    resize_to_hd: bool = Field(default=False, description="Resize frames to 1920x1080 for faster processing")
    save_segments: bool = Field(default=False, description="Export individual segments as MP4 files for verification")

    @field_validator('input_videos')
    @classmethod
    def validate_input_videos(cls, v: List[str]) -> List[str]:
        """Validate input videos are MP4 files."""
        if not v:
            raise ValueError("At least one input video required")
        for path in v:
            if not path.lower().endswith('.mp4'):
                raise ValueError(f"File must be MP4 format: {path}")
        return v

    @field_validator('logging_verbosity')
    @classmethod
    def validate_verbosity(cls, v: str) -> str:
        """Validate logging verbosity level."""
        valid_levels = ["minimal", "moderate", "detailed", "verbose"]
        if v not in valid_levels:
            raise ValueError(f"Verbosity must be one of: {', '.join(valid_levels)}")
        return v

    @field_validator('output_directory')
    @classmethod
    def convert_output_directory(cls, v: Union[str, Path]) -> Path:
        """Convert output directory to Path object."""
        return Path(v)

    @field_validator('checkpoint_directory')
    @classmethod
    def set_default_checkpoint_dir(cls, v: Union[str, Path], info) -> Path:
        """Set default checkpoint directory if not provided."""
        if not v and 'output_directory' in info.data:
            return Path(info.data['output_directory']) / "checkpoints"
        return Path(v) if v else Path("./output/checkpoints")

    class Config:
        json_schema_extra = {
            "example": {
                "input_videos": ["/path/to/video1.mp4", "/path/to/video2.mp4"],
                "output_directory": "./output",
                "target_duration": 180.0,
                "min_quality_threshold": 7.0,
                "sample_rate_fps": 1.0,
                "logging_verbosity": "detailed",
                "resume_from_phase": 1,
                "checkpoint_directory": "./output/checkpoints"
            }
        }
