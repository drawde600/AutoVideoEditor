"""Checkpoint models for pipeline state persistence."""

from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from .segment import Segment


class Checkpoint(BaseModel):
    """Base checkpoint model with common fields.

    Attributes:
        phase: Phase number (1-5)
        timestamp: When checkpoint was created
        input_video_paths: Paths to all source videos
        pipeline_version: Version of pipeline that created this
        phase_duration_seconds: Time taken to complete this phase
    """

    phase: int = Field(..., ge=1, le=5, description="Phase number (1-5)")
    timestamp: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    input_video_paths: List[str] = Field(..., description="Paths to source videos")
    pipeline_version: str = Field(default="1.0.0", description="Pipeline version")
    phase_duration_seconds: float = Field(..., ge=0, description="Phase duration (seconds)")


class Phase1Checkpoint(Checkpoint):
    """Phase 1 (Segmentation) checkpoint.

    Contains extracted segments with timestamps but no scores yet.
    """

    phase: int = Field(default=1, frozen=True)
    segments: List[Segment] = Field(..., min_length=1, description="Extracted segments")
    total_segments: int = Field(..., gt=0, description="Count of segments extracted")
    sample_rate_fps: float = Field(..., gt=0, description="Frame sampling rate used")

    @field_validator('total_segments')
    @classmethod
    def validate_total(cls, v: int, info) -> int:
        """Validate total matches segment list length."""
        if 'segments' in info.data and v != len(info.data['segments']):
            raise ValueError(f"total_segments {v} doesn't match segments length {len(info.data['segments'])}")
        return v


class Phase2Checkpoint(Checkpoint):
    """Phase 2 (Ranking & Classification) checkpoint.

    Contains segments with quality scores and classifications.
    """

    phase: int = Field(default=2, frozen=True)
    segments: List[Segment] = Field(..., min_length=1, description="Scored segments")
    min_quality_threshold: float = Field(..., ge=1.0, le=10.0, description="Quality threshold")
    segments_above_threshold: int = Field(..., ge=0, description="Segments meeting threshold")
    score_weights: Dict[str, float] = Field(..., description="Score weights (scene, motion, composition)")

    @field_validator('score_weights')
    @classmethod
    def validate_weights(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Validate score weights sum to 1.0."""
        required_keys = {'scene', 'motion', 'composition'}
        if set(v.keys()) != required_keys:
            raise ValueError(f"score_weights must have keys: {required_keys}")
        total = sum(v.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"score_weights must sum to 1.0, got {total}")
        return v

    @field_validator('segments_above_threshold')
    @classmethod
    def validate_threshold_count(cls, v: int) -> int:
        """FR-007: Fail if no segments above threshold."""
        if v == 0:
            raise ValueError("No segments above quality threshold (FR-007)")
        return v


class Phase3Checkpoint(Checkpoint):
    """Phase 3 (Assembly) checkpoint.

    Contains selected segments and ordering for highlight reel.
    """

    phase: int = Field(default=3, frozen=True)
    selected_segments: List[str] = Field(..., description="Ordered list of segment IDs")
    target_duration: float = Field(..., gt=0, description="Target duration")
    actual_duration: float = Field(..., gt=0, description="Actual duration of selected segments")
    selection_algorithm: str = Field(..., description="Algorithm used (e.g., greedy_variety)")
    variety_score: Optional[float] = Field(None, ge=0, le=1, description="Temporal distribution measure")


class Phase4Checkpoint(Checkpoint):
    """Phase 4 (Composition) checkpoint.

    Contains composition settings (transitions, overlays, subtitles).
    """

    phase: int = Field(default=4, frozen=True)
    transition_type: str = Field(default="cut", description="Transition effect (cut, fade, dissolve)")
    transition_duration: Optional[float] = Field(None, gt=0, description="Transition duration (seconds)")
    text_overlays: List[Dict] = Field(default_factory=list, description="Text overlay configurations")
    subtitle_file: Optional[str] = Field(None, description="Path to subtitle file (SRT)")
    subtitle_style: Optional[Dict] = Field(None, description="Subtitle styling options")
    gps_overlay_enabled: bool = Field(False, description="Whether to render GPS overlays")
    gps_overlay_config: Optional[Dict] = Field(None, description="GPS overlay configuration")

    @field_validator('transition_type')
    @classmethod
    def validate_transition(cls, v: str) -> str:
        """Validate transition type."""
        valid_types = ["cut", "fade", "dissolve"]
        if v not in valid_types:
            raise ValueError(f"transition_type must be one of: {', '.join(valid_types)}")
        return v


class Phase5Checkpoint(Checkpoint):
    """Phase 5 (Audio) checkpoint.

    Contains audio mixing and normalization settings.
    """

    phase: int = Field(default=5, frozen=True)
    normalize_audio: bool = Field(True, description="Whether to normalize audio levels")
    normalization_target_db: Optional[float] = Field(-16.0, ge=-30, le=0, description="Target loudness (dB LUFS)")
    background_music_file: Optional[str] = Field(None, description="Path to background music")
    background_music_volume: Optional[float] = Field(None, ge=0.0, le=1.0, description="Music volume (0-1)")
    fade_music_at_speech: bool = Field(False, description="Reduce music during speech/high audio")
    output_audio_codec: str = Field(default="aac", description="Audio codec for output")

    @field_validator('output_audio_codec')
    @classmethod
    def validate_codec(cls, v: str) -> str:
        """Validate audio codec."""
        valid_codecs = ["aac", "mp3"]
        if v not in valid_codecs:
            raise ValueError(f"output_audio_codec must be one of: {', '.join(valid_codecs)}")
        return v
