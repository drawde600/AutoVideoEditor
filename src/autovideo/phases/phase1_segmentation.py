"""Phase 1: Segmentation - Extract video segments."""

from typing import List
from pathlib import Path
import time
import uuid

from ..models.video_source import VideoSource
from ..models.segment import Segment
from ..models.checkpoint import Phase1Checkpoint
from ..models.pipeline_config import PipelineConfig
from ..video.video_io import VideoReader
from ..video.ffmpeg_wrapper import FFmpegWrapper
from ..analysis.scene_detector import SceneDetector
from ..utils.logger import get_logger
from ..utils.progress import ProgressReporter

logger = get_logger(__name__)


class Phase1Segmentation:
    """Phase 1: Extract 5-15 second segments from input videos.

    Process:
    1. Validate MP4 file headers (skip invalid with warning per FR-046)
    2. Extract video metadata
    3. Detect scene changes for segment boundaries
    4. Extract 5-15 second segments (FR-002)
    5. Parse GPS data from SRT files if available (FR-037)
    6. Save Phase1Checkpoint
    """

    def __init__(self, config: PipelineConfig, progress: ProgressReporter):
        """Initialize Phase 1.

        Args:
            config: Pipeline configuration
            progress: Progress reporter
        """
        self.config = config
        self.progress = progress
        self.scene_detector = SceneDetector()
        self.ffmpeg = FFmpegWrapper()

    def execute(self) -> Phase1Checkpoint:
        """Execute segmentation phase.

        Returns:
            Phase1Checkpoint with extracted segments
        """
        start_time = time.time()
        logger.info(f"Starting Phase 1: Segmentation for {len(self.config.input_videos)} videos")
        self.progress.update("Phase 1: Segmentation - Validating videos")

        # Validate all input videos
        valid_videos = self.validate_videos()
        if not valid_videos:
            raise RuntimeError("No valid MP4 videos found after validation (FR-046)")

        logger.info(f"Found {len(valid_videos)} valid videos")

        # Process all videos and collect segments
        all_segments = []
        for i, video_path in enumerate(valid_videos):
            self.progress.update(f"Processing video {i+1}/{len(valid_videos)}: {Path(video_path).name}")

            # Extract metadata
            video_source = self.extract_video_metadata(video_path)
            logger.info(f"Video {video_source.video_id}: {video_source.duration_seconds:.1f}s, "
                       f"{video_source.resolution[0]}x{video_source.resolution[1]}, "
                       f"{video_source.frame_rate:.1f}fps")

            # Detect segments
            segments = self.detect_segments(video_source)
            logger.info(f"Extracted {len(segments)} segments from {video_source.video_id}")

            all_segments.extend(segments)

        phase_duration = time.time() - start_time

        # Create checkpoint
        checkpoint = Phase1Checkpoint(
            input_video_paths=self.config.input_videos,
            phase_duration_seconds=phase_duration,
            segments=all_segments,
            total_segments=len(all_segments),
            sample_rate_fps=self.config.sample_rate_fps
        )

        # Optionally export segments as MP4 files for verification
        if self.config.save_segments:
            self.progress.update("Phase 1: Exporting segments to MP4 files")
            self._export_segments(all_segments)

        logger.info(f"Phase 1 complete: {len(all_segments)} total segments extracted in {phase_duration:.1f}s")
        self.progress.update("Phase 1: Segmentation complete")

        return checkpoint

    def _export_segments(self, segments: List[Segment]) -> None:
        """Export segments as MP4 files for visual verification.

        Args:
            segments: List of segments to export
        """
        segments_dir = self.config.output_directory / "segments"
        segments_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Exporting {len(segments)} segments to {segments_dir}")

        for i, segment in enumerate(segments):
            try:
                # Find source video
                source_video = None
                for video_path in self.config.input_videos:
                    if Path(video_path).stem == segment.video_id:
                        source_video = video_path
                        break

                if not source_video:
                    logger.warning(f"Source video not found for segment {segment.segment_id}")
                    continue

                # Create output filename with metadata
                output_filename = f"seg_{i:04d}_{segment.video_id}_{segment.start_time:.1f}s-{segment.end_time:.1f}s.mp4"
                output_path = segments_dir / output_filename

                # Extract segment using FFmpeg
                self.ffmpeg.extract_segment(
                    input_path=source_video,
                    output_path=str(output_path),
                    start_time=segment.start_time,
                    duration=segment.duration
                )

                if (i + 1) % 5 == 0:
                    logger.info(f"Exported {i+1}/{len(segments)} segments")

            except Exception as e:
                logger.error(f"Failed to export segment {segment.segment_id}: {e}")
                continue

        logger.info(f"✓ All segments exported to: {segments_dir}")

    def validate_videos(self) -> List[str]:
        """Validate MP4 files and return valid paths.

        Returns:
            List of valid video file paths
        """
        valid_paths = []

        for video_path in self.config.input_videos:
            # Check if file exists
            if not Path(video_path).exists():
                logger.warning(f"Video file not found: {video_path}")
                continue

            # Validate MP4 format (basic check using FFmpeg)
            if not self.ffmpeg.validate_mp4(video_path):
                logger.warning(f"Invalid MP4 file (skipping per FR-046): {video_path}")
                continue

            valid_paths.append(video_path)

        return valid_paths

    def extract_video_metadata(self, video_path: str) -> VideoSource:
        """Extract metadata from video file.

        Args:
            video_path: Path to video file

        Returns:
            VideoSource with metadata
        """
        reader = VideoReader(video_path, self.config.sample_rate_fps, self.config.resize_to_hd)
        video_source = reader.get_video_info()
        return video_source

    def detect_segments(self, video_source: VideoSource) -> List[Segment]:
        """Detect and extract segments from video.

        Args:
            video_source: Video metadata

        Returns:
            List of segments (5-15 seconds each)
        """
        segments = []

        # Read video frames at sample rate
        reader = VideoReader(video_source.file_path, self.config.sample_rate_fps, self.config.resize_to_hd)

        with reader:
            frames = list(reader.read_frames())

        if len(frames) < 2:
            logger.warning(f"Video {video_source.video_id} has insufficient frames for segmentation")
            return []

        # Find scene boundaries
        scene_boundaries = self.scene_detector.find_scene_boundaries(frames)
        logger.debug(f"Found {len(scene_boundaries)} scene boundaries")

        # Calculate time per sampled frame
        time_per_frame = 1.0 / self.config.sample_rate_fps

        # Create segments from scene boundaries
        for i in range(len(scene_boundaries) - 1):
            start_frame_idx = scene_boundaries[i]
            end_frame_idx = scene_boundaries[i + 1]

            # Calculate timestamps
            start_time = start_frame_idx * time_per_frame
            end_time = end_frame_idx * time_per_frame
            duration = end_time - start_time

            # Ensure segment is within 5-15 second range (FR-002)
            if duration < 5.0:
                # Segment too short - skip or merge with next
                continue
            elif duration > 15.0:
                # Segment too long - split into 10-second chunks
                num_chunks = int(duration / 10.0)
                chunk_duration = duration / num_chunks

                for chunk_idx in range(num_chunks):
                    chunk_start = start_time + (chunk_idx * chunk_duration)
                    chunk_end = chunk_start + chunk_duration

                    if 5.0 <= chunk_duration <= 15.0:
                        segment = Segment(
                            segment_id=str(uuid.uuid4()),
                            video_id=video_source.video_id,
                            start_time=chunk_start,
                            end_time=chunk_end,
                            duration=chunk_duration
                        )
                        segments.append(segment)
            else:
                # Duration is within range - create segment
                segment = Segment(
                    segment_id=str(uuid.uuid4()),
                    video_id=video_source.video_id,
                    start_time=start_time,
                    end_time=end_time,
                    duration=duration
                )
                segments.append(segment)

        # Handle last segment
        if len(scene_boundaries) > 0:
            last_boundary_idx = scene_boundaries[-1]
            last_start_time = last_boundary_idx * time_per_frame
            last_end_time = video_source.duration_seconds
            last_duration = last_end_time - last_start_time

            if 5.0 <= last_duration <= 15.0:
                segment = Segment(
                    segment_id=str(uuid.uuid4()),
                    video_id=video_source.video_id,
                    start_time=last_start_time,
                    end_time=last_end_time,
                    duration=last_duration
                )
                segments.append(segment)

        logger.debug(f"Created {len(segments)} segments from {len(scene_boundaries)} scene boundaries")

        return segments

    def parse_gps_data(self, srt_path: str) -> dict:
        """Parse GPS data from SRT file.

        Args:
            srt_path: Path to GPS-enabled SRT file

        Returns:
            Dict with GPS coordinates, elevations, timestamps

        Note: GPS parsing will be implemented in Phase 5 (User Story 3)
              For MVP (User Story 1), this is a placeholder
        """
        # TODO: Implement GPS parsing for User Story 3
        return {}
