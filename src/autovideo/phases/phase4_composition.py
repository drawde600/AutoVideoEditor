"""Phase 4: Composition - Apply transitions and effects."""

from typing import List
from pathlib import Path
import time
import tempfile
import os

from ..models.checkpoint import Phase2Checkpoint, Phase3Checkpoint, Phase4Checkpoint
from ..models.segment import Segment
from ..models.pipeline_config import PipelineConfig
from ..video.ffmpeg_wrapper import FFmpegWrapper
from ..utils.logger import get_logger
from ..utils.progress import ProgressReporter

logger = get_logger(__name__)


class Phase4Composition:
    """Phase 4: Compose final video with transitions and effects.

    Process (Basic for MVP):
    1. Load Phase2 and Phase3 Checkpoints
    2. Extract selected segments from source videos
    3. Concatenate with transitions (cut for MVP)
    4. Save Phase4Checkpoint
    """

    def __init__(self, config: PipelineConfig, progress: ProgressReporter):
        """Initialize Phase 4.

        Args:
            config: Pipeline configuration
            progress: Progress reporter
        """
        self.config = config
        self.progress = progress
        self.ffmpeg = FFmpegWrapper()

    def execute(
        self,
        phase2_checkpoint: Phase2Checkpoint,
        phase3_checkpoint: Phase3Checkpoint,
        output_path: str,
        transition_type: str = "cut"
    ) -> Phase4Checkpoint:
        """Execute composition phase.

        Args:
            phase2_checkpoint: Phase 2 checkpoint with segment details
            phase3_checkpoint: Phase 3 checkpoint with selected segment IDs
            output_path: Path for output video
            transition_type: Transition type (cut, fade, dissolve)

        Returns:
            Phase4Checkpoint
        """
        start_time = time.time()
        logger.info(f"Starting Phase 4: Composition with {transition_type} transitions")
        self.progress.update("Phase 4: Composition - Extracting segments")

        # Create temporary directory for segment files
        temp_dir = Path(tempfile.mkdtemp(prefix="autovideo_segments_"))

        try:
            # Extract segments to temporary files
            segment_files = self.extract_segments(
                phase2_checkpoint,
                phase3_checkpoint,
                temp_dir
            )

            if not segment_files:
                raise RuntimeError("No segments extracted for composition")

            logger.info(f"Extracted {len(segment_files)} segments to temporary files")

            # Concatenate segments
            self.progress.update("Phase 4: Composition - Concatenating segments")
            self.ffmpeg.concatenate_videos(
                segment_files,
                output_path,
                transition_type
            )

            logger.info(f"Concatenated segments to: {output_path}")

        finally:
            # Clean up temporary directory
            try:
                for file in temp_dir.glob("*"):
                    file.unlink()
                temp_dir.rmdir()
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary directory: {e}")

        phase_duration = time.time() - start_time

        checkpoint = Phase4Checkpoint(
            input_video_paths=phase3_checkpoint.input_video_paths,
            phase_duration_seconds=phase_duration,
            transition_type=transition_type,
            transition_duration=None if transition_type == "cut" else 0.5
        )

        logger.info(f"Phase 4 complete: Video composed in {phase_duration:.1f}s")
        self.progress.update("Phase 4: Composition complete")
        return checkpoint

    def extract_segments(
        self,
        phase2_checkpoint: Phase2Checkpoint,
        phase3_checkpoint: Phase3Checkpoint,
        temp_dir: Path
    ) -> List[str]:
        """Extract selected segments to temporary files.

        Args:
            phase2_checkpoint: Phase 2 checkpoint with all segment details
            phase3_checkpoint: Phase 3 checkpoint with selected segment IDs
            temp_dir: Temporary directory for extracted segments

        Returns:
            List of paths to extracted segment files (in order)
        """
        # Create segment lookup by ID
        segments_by_id = {seg.segment_id: seg for seg in phase2_checkpoint.segments}

        # Get selected segments in order
        selected_segments = []
        for seg_id in phase3_checkpoint.selected_segments:
            if seg_id not in segments_by_id:
                logger.warning(f"Selected segment {seg_id} not found in Phase 2 checkpoint")
                continue
            selected_segments.append(segments_by_id[seg_id])

        logger.info(f"Extracting {len(selected_segments)} selected segments")

        # Extract each segment
        segment_files = []
        for i, segment in enumerate(selected_segments):
            self.progress.update(f"Extracting segment {i+1}/{len(selected_segments)}")

            # Find source video path
            source_video = None
            for input_path in self.config.input_videos:
                video_id = Path(input_path).stem
                if video_id == segment.video_id:
                    source_video = input_path
                    break

            if not source_video:
                logger.error(f"Source video not found for segment {segment.segment_id}")
                continue

            # Create output filename
            output_file = temp_dir / f"segment_{i:04d}.mp4"

            try:
                # Extract segment using FFmpeg
                self.ffmpeg.extract_segment(
                    input_path=source_video,
                    output_path=str(output_file),
                    start_time=segment.start_time,
                    duration=segment.duration
                )
                segment_files.append(str(output_file))
                logger.debug(f"Extracted segment {i+1}: {segment.start_time:.1f}s - {segment.end_time:.1f}s from {segment.video_id}")

            except Exception as e:
                logger.error(f"Failed to extract segment {segment.segment_id}: {e}")
                continue

        return segment_files
