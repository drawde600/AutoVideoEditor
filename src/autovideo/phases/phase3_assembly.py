"""Phase 3: Assembly - Select and order segments for highlight reel."""

from typing import List
import time

from ..models.checkpoint import Phase2Checkpoint, Phase3Checkpoint
from ..models.segment import Segment
from ..models.pipeline_config import PipelineConfig
from ..utils.logger import get_logger
from ..utils.progress import ProgressReporter

logger = get_logger(__name__)


class Phase3Assembly:
    """Phase 3: Select segments and assemble into highlight reel order.

    Process:
    1. Load Phase2Checkpoint
    2. Filter segments by quality threshold (>= 7/10)
    3. Select segments optimizing for quality AND variety (FR-013)
    4. Order segments chronologically by timestamp (FR-014, clarifications)
    5. Ensure total duration matches target (FR-012)
    6. Save Phase3Checkpoint

    Ordering (clarifications):
    - Multi-video: chronological by original timestamp across ALL videos
    - Single video: chronological order

    TODO: Implement greedy selection with variety optimization
    """

    def __init__(self, config: PipelineConfig, progress: ProgressReporter):
        """Initialize Phase 3.

        Args:
            config: Pipeline configuration
            progress: Progress reporter
        """
        self.config = config
        self.progress = progress

    def execute(self, phase2_checkpoint: Phase2Checkpoint) -> Phase3Checkpoint:
        """Execute assembly phase.

        Args:
            phase2_checkpoint: Checkpoint from Phase 2

        Returns:
            Phase3Checkpoint with selected segments
        """
        start_time = time.time()
        target_duration = self.config.target_duration
        logger.info(f"Starting Phase 3: Assembly with target duration {target_duration}s")
        self.progress.update("Phase 3: Assembly - Selecting segments")

        # Filter to only included segments (those above quality threshold)
        included_segments = [s for s in phase2_checkpoint.segments if s.included]
        logger.info(f"Filtering {len(included_segments)} segments above quality threshold")

        if not included_segments:
            raise RuntimeError("No segments available for assembly (all below quality threshold)")

        # Select segments using greedy algorithm with variety
        selected_segment_ids = self.select_segments(
            included_segments,
            target_duration,
            self.config.min_quality_threshold
        )

        # Calculate actual duration
        selected_segments = [s for s in included_segments if s.segment_id in selected_segment_ids]
        actual_duration = sum(s.duration for s in selected_segments)

        # Calculate variety score (temporal distribution)
        variety_score = self.calculate_variety_score(selected_segments)

        phase_duration = time.time() - start_time

        checkpoint = Phase3Checkpoint(
            input_video_paths=phase2_checkpoint.input_video_paths,
            phase_duration_seconds=phase_duration,
            selected_segments=selected_segment_ids,
            target_duration=target_duration,
            actual_duration=actual_duration,
            selection_algorithm="greedy_variety",
            variety_score=variety_score
        )

        logger.info(f"Phase 3 complete: {len(selected_segment_ids)} segments, "
                   f"{actual_duration:.1f}s duration (target: {target_duration}s), "
                   f"variety score: {variety_score:.2f}")
        self.progress.update("Phase 3: Assembly complete")
        return checkpoint

    def select_segments(
        self,
        segments: List[Segment],
        target_duration: float,
        min_quality: float
    ) -> List[str]:
        """Select segments optimizing for quality and variety.

        Args:
            segments: Available segments (from Phase 2)
            target_duration: Target duration in seconds
            min_quality: Minimum quality threshold

        Returns:
            List of selected segment IDs (ordered chronologically)
        """
        # Sort segments by quality score (descending) for greedy selection
        sorted_segments = sorted(segments, key=lambda s: s.quality_score or 0.0, reverse=True)

        selected = []
        current_duration = 0.0

        # Greedy selection: pick highest quality segments until target duration reached
        for segment in sorted_segments:
            if current_duration + segment.duration <= target_duration:
                selected.append(segment)
                current_duration += segment.duration
            elif current_duration < target_duration:
                # Still have room, but this segment would exceed target
                # Check if we can fit it anyway (allow small overage)
                if (current_duration + segment.duration) - target_duration < 5.0:
                    selected.append(segment)
                    current_duration += segment.duration
                    break

            # Stop if we've reached or exceeded target
            if current_duration >= target_duration:
                break

        # FR-012: Handle case where source shorter than target
        total_available = sum(s.duration for s in segments)
        if current_duration < target_duration and total_available < target_duration:
            logger.warning(f"Source duration ({total_available:.1f}s) shorter than target ({target_duration}s). "
                          "Using all available segments (FR-012)")
            selected = segments  # Use all segments

        # FR-014: Order chronologically by timestamp (across all videos per clarifications)
        # Sort by start_time to maintain chronological order
        selected_ordered = sorted(selected, key=lambda s: s.start_time)

        # Return segment IDs in chronological order
        return [s.segment_id for s in selected_ordered]

    def calculate_variety_score(self, segments: List[Segment]) -> float:
        """Calculate variety score based on temporal distribution.

        Args:
            segments: Selected segments

        Returns:
            Variety score (0-1), higher is better distribution
        """
        if not segments:
            return 0.0

        # Simple variety metric: standard deviation of gaps between segments
        # More evenly distributed segments = higher variety
        if len(segments) < 2:
            return 1.0

        # Calculate gaps between consecutive segments
        sorted_segs = sorted(segments, key=lambda s: s.start_time)
        gaps = []
        for i in range(len(sorted_segs) - 1):
            gap = sorted_segs[i + 1].start_time - sorted_segs[i].end_time
            gaps.append(gap)

        # Lower standard deviation = more even distribution = higher variety
        if not gaps:
            return 1.0

        avg_gap = sum(gaps) / len(gaps)
        variance = sum((g - avg_gap) ** 2 for g in gaps) / len(gaps)
        std_dev = variance ** 0.5

        # Normalize to 0-1 range (inverse of coefficient of variation)
        if avg_gap == 0:
            return 0.5
        variety = max(0.0, min(1.0, 1.0 - (std_dev / (avg_gap + 1.0))))

        return round(variety, 2)

    def order_chronologically(
        self,
        segment_ids: List[str],
        segments: List[Segment]
    ) -> List[str]:
        """Order segments chronologically by original timestamp.

        Args:
            segment_ids: Selected segment IDs
            segments: All segments (to lookup timestamps)

        Returns:
            Segment IDs in chronological order

        Ordering (clarifications):
        TODO: For multi-video: sort by (video_timestamp + start_time)
        TODO: For single video: sort by start_time
        TODO: Return ordered segment IDs (FR-014)
        """
        # TODO: Implement chronological ordering
        return segment_ids  # Placeholder

    def calculate_variety_score(self, segments: List[Segment]) -> float:
        """Calculate temporal variety of selected segments.

        Args:
            segments: Selected segments

        Returns:
            Variety score (0-1), higher = better distribution

        TODO: Measure temporal distribution across video duration
        TODO: Penalize clustering in one section
        TODO: Return 0-1 score
        """
        # TODO: Implement variety calculation
        return 0.5  # Placeholder
