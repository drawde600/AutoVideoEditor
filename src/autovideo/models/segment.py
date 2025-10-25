"""Segment model for extracted video clips."""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator
import uuid


class Segment(BaseModel):
    """Represents an extracted clip from a source video with quality metrics.

    Attributes:
        segment_id: Unique identifier for segment (UUID)
        video_id: Identifier of source video this segment belongs to
        start_time: Start timestamp in seconds (relative to source video)
        end_time: End timestamp in seconds (relative to source video)
        duration: Segment duration (5-15 seconds per FR-002)
        quality_score: Overall quality score (1-10)
        motion_score: Motion analysis score (1-10)
        scene_score: Scene change score (1-10)
        composition_score: Visual composition score (1-10)
        classifications: Segment classification tags
        included: Whether segment is included in final reel
        manually_edited: Flag indicating manual user edit
        gps_coordinates: GPS path coordinates [(lat, lon), ...]
        gps_elevations: Elevation values in meters
        gps_timestamps: Timestamps for each GPS point (relative to segment start)
        location_name: Reverse-geocoded location (populated in Phase 4)
    """

    segment_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique segment UUID")
    video_id: str = Field(..., description="Source video ID")
    start_time: float = Field(..., ge=0, description="Start timestamp (seconds)")
    end_time: float = Field(..., gt=0, description="End timestamp (seconds)")
    duration: float = Field(..., ge=5.0, le=15.0, description="Segment duration (5-15s per FR-002)")

    # Quality scores (optional until Phase 2)
    quality_score: Optional[float] = Field(None, ge=1.0, le=10.0, description="Overall quality (1-10)")
    motion_score: Optional[float] = Field(None, ge=1.0, le=10.0, description="Motion score (1-10)")
    scene_score: Optional[float] = Field(None, ge=1.0, le=10.0, description="Scene change score (1-10)")
    composition_score: Optional[float] = Field(None, ge=1.0, le=10.0, description="Composition score (1-10)")

    # Classification and selection
    classifications: List[str] = Field(default_factory=list, description="Classification tags")
    included: bool = Field(True, description="Whether included in final reel")
    manually_edited: bool = Field(False, description="Manual edit flag")

    # GPS data (optional)
    gps_coordinates: Optional[List[Tuple[float, float]]] = Field(None, description="GPS path [(lat, lon)]")
    gps_elevations: Optional[List[float]] = Field(None, description="Elevation values (meters)")
    gps_timestamps: Optional[List[float]] = Field(None, description="GPS point timestamps")
    location_name: Optional[str] = Field(None, description="Reverse-geocoded location")

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: float, info) -> float:
        """Validate end_time > start_time."""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError("end_time must be greater than start_time")
        return v

    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v: float, info) -> float:
        """Validate duration matches end_time - start_time."""
        if 'start_time' in info.data and 'end_time' in info.data:
            calculated_duration = info.data['end_time'] - info.data['start_time']
            if abs(v - calculated_duration) > 0.1:  # Allow small floating point differences
                raise ValueError(f"Duration {v} doesn't match end_time - start_time = {calculated_duration}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "segment_id": "550e8400-e29b-41d4-a716-446655440000",
                "video_id": "video-001",
                "start_time": 125.0,
                "end_time": 137.5,
                "duration": 12.5,
                "quality_score": 7.8,
                "motion_score": 8.2,
                "scene_score": 7.5,
                "composition_score": 7.7,
                "classifications": ["high-action", "highlight-candidate"],
                "included": True,
                "manually_edited": False,
                "gps_coordinates": [[37.7749, -122.4194], [37.7750, -122.4195]],
                "gps_elevations": [50.2, 52.1],
                "gps_timestamps": [0.0, 6.25],
                "location_name": "San Francisco, California, USA"
            }
        }
