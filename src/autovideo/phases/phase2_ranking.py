"""Phase 2: Ranking & Classification - Score and classify segments."""

from typing import List
from pathlib import Path
import time
import numpy as np

from ..models.checkpoint import Phase1Checkpoint, Phase2Checkpoint
from ..models.segment import Segment
from ..models.pipeline_config import PipelineConfig
from ..analysis.motion_detector import MotionDetector
from ..analysis.scene_detector import SceneDetector
from ..analysis.composition_analyzer import CompositionAnalyzer
from ..video.video_io import VideoReader, extract_frames_at_timestamps
from ..utils.logger import get_logger
from ..utils.progress import ProgressReporter

logger = get_logger(__name__)


class Phase2Ranking:
    """Phase 2: Assign quality scores and classify segments.

    Process:
    1. Load Phase1Checkpoint
    2. For each segment:
       - Extract frames
       - Calculate motion score (25% weight)
       - Calculate scene change score (60% weight)
       - Calculate composition score (15% weight)
       - Compute final quality score
       - Assign classification tags
    3. Check minimum quality threshold (7/10 per FR-007, clarifications)
    4. Save Phase2Checkpoint

    Quality Formula (clarifications):
    quality_score = (0.6 * scene_score) + (0.25 * motion_score) + (0.15 * composition_score)

    Classification Tags (research.md):
    - high-action: motion_score >= 7
    - static: motion_score <= 3
    - dynamic-scene: scene_score >= 6
    - visually-rich: composition_score >= 8
    - highlight-candidate: motion >= 6 AND scene >= 6
    - neutral: default

    TODO: Implement ranking pipeline
    """

    def __init__(self, config: PipelineConfig, progress: ProgressReporter):
        """Initialize Phase 2.

        Args:
            config: Pipeline configuration
            progress: Progress reporter
        """
        self.config = config
        self.progress = progress
        self.motion_detector = MotionDetector()
        self.scene_detector = SceneDetector()
        self.composition_analyzer = CompositionAnalyzer()

        # Quality score weights (clarifications)
        self.score_weights = {
            'scene': 0.6,
            'motion': 0.25,
            'composition': 0.15
        }

    def execute(self, phase1_checkpoint: Phase1Checkpoint) -> Phase2Checkpoint:
        """Execute ranking phase.

        Args:
            phase1_checkpoint: Checkpoint from Phase 1

        Returns:
            Phase2Checkpoint with scored segments

        Raises:
            RuntimeError: If no segments above threshold (FR-007)
        """
        start_time = time.time()
        logger.info(f"Starting Phase 2: Ranking {len(phase1_checkpoint.segments)} segments")
        self.progress.update("Phase 2: Ranking - Scoring segments")

        scored_segments = []
        logger.info(f"\n{'='*60}")
        logger.info("SCORING SEGMENTS")
        logger.info(f"{'='*60}")

        for i, segment in enumerate(phase1_checkpoint.segments):
            if (i + 1) % 10 == 0 or (i + 1) == len(phase1_checkpoint.segments):
                self.progress.update(f"Scoring segment {i+1}/{len(phase1_checkpoint.segments)}")

            # Extract frames and score segment
            scored_segment = self.score_segment(segment, segment_index=i+1)
            scored_segments.append(scored_segment)

        # Count segments above threshold
        segments_above_threshold = sum(
            1 for seg in scored_segments
            if seg.quality_score and seg.quality_score >= self.config.min_quality_threshold
        )

        # Print summary table
        logger.info(f"\n{'='*60}")
        logger.info("SEGMENT SCORES SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Threshold: {self.config.min_quality_threshold}/10 | Passed: {segments_above_threshold}/{len(scored_segments)}")
        logger.info(f"Scoring weights: Scene={self.score_weights['scene']*100:.0f}% Motion={self.score_weights['motion']*100:.0f}% Composition={self.score_weights['composition']*100:.0f}%")
        logger.info(f"{'='*60}")

        # FR-007: Must have at least one segment above threshold
        if segments_above_threshold == 0:
            # Calculate score ranges to help user adjust threshold
            all_scores = [seg.quality_score for seg in scored_segments if seg.quality_score]
            if all_scores:
                max_score = max(all_scores)
                min_score = min(all_scores)
                avg_score = sum(all_scores) / len(all_scores)

                raise RuntimeError(
                    f"No segments above quality threshold ({self.config.min_quality_threshold}/10). "
                    f"Actual scores range: {min_score:.1f}-{max_score:.1f} (avg: {avg_score:.1f}). "
                    f"Try lowering --min-quality to {max_score:.1f} or below. (FR-007)"
                )
            else:
                raise RuntimeError(
                    f"No segments above quality threshold ({self.config.min_quality_threshold}/10). "
                    "Try lowering the --min-quality threshold or check video content. (FR-007)"
                )

        phase_duration = time.time() - start_time

        checkpoint = Phase2Checkpoint(
            input_video_paths=phase1_checkpoint.input_video_paths,
            phase_duration_seconds=phase_duration,
            segments=scored_segments,
            min_quality_threshold=self.config.min_quality_threshold,
            segments_above_threshold=segments_above_threshold,
            score_weights=self.score_weights
        )

        logger.info(f"Phase 2 complete: {segments_above_threshold} segments passed threshold in {phase_duration:.1f}s")
        self.progress.update("Phase 2: Ranking complete")
        return checkpoint

    def score_segment(self, segment: Segment, segment_index: int = 0) -> Segment:
        """Score a single segment with motion, scene, and composition analysis.

        Args:
            segment: Segment to score
            segment_index: Index of segment (for logging)

        Returns:
            Segment with quality scores and classifications
        """
        # Extract frames for this segment
        frames = self.extract_segment_frames(segment)

        if len(frames) < 2:
            logger.warning(f"Segment {segment_index} has insufficient frames, assigning minimum scores")
            segment.motion_score = 1.0
            segment.scene_score = 1.0
            segment.composition_score = 1.0
            segment.quality_score = 1.0
            segment.classifications = ["neutral"]
            segment.included = False
            return segment

        # Calculate individual scores using analysis modules
        motion_score = self.motion_detector.analyze_segment(frames)
        scene_score = self.scene_detector.analyze_segment(frames)
        composition_score = self.composition_analyzer.analyze_segment(frames)

        # Calculate weighted quality score
        quality_score = self.calculate_quality_score(motion_score, scene_score, composition_score)

        # Update segment with scores
        segment.motion_score = round(motion_score, 1)
        segment.scene_score = round(scene_score, 1)
        segment.composition_score = round(composition_score, 1)
        segment.quality_score = round(quality_score, 1)

        # Classify segment
        segment.classifications = self.classify_segment(motion_score, scene_score, composition_score)

        # Mark as included if above threshold
        segment.included = quality_score >= self.config.min_quality_threshold

        # Log detailed scores for verification and adjustment
        status = "✓ PASS" if segment.included else "✗ FAIL"
        logger.info(f"{status} Segment {segment_index}: {segment.video_id} [{segment.start_time:.1f}s-{segment.end_time:.1f}s] "
                    f"→ Quality={segment.quality_score:.1f}/10 "
                    f"(Motion={segment.motion_score:.1f} Scene={segment.scene_score:.1f} Comp={segment.composition_score:.1f})")

        return segment

    def extract_segment_frames(self, segment: Segment) -> List:
        """Extract frames from a segment for analysis.

        Args:
            segment: Segment to extract frames from

        Returns:
            List of frames as numpy arrays
        """
        # Calculate timestamps to extract (sample at configured rate)
        sample_interval = 1.0 / self.config.sample_rate_fps
        timestamps = []
        t = segment.start_time
        while t < segment.end_time:
            timestamps.append(t)
            t += sample_interval

        # Find the video file path from segment's video_id
        video_path = None
        for input_path in self.config.input_videos:
            video_id = Path(input_path).stem
            if video_id == segment.video_id:
                video_path = input_path
                break

        if not video_path:
            logger.error(f"Could not find video file for segment {segment.video_id}")
            return []

        # Extract frames at timestamps
        frames = extract_frames_at_timestamps(video_path, timestamps, self.config.resize_to_hd)

        # Filter out None frames
        frames = [f for f in frames if f is not None]

        return frames

    def calculate_quality_score(
        self,
        motion_score: float,
        scene_score: float,
        composition_score: float
    ) -> float:
        """Calculate final quality score using weighted formula.

        Args:
            motion_score: Motion score (1-10)
            scene_score: Scene change score (1-10)
            composition_score: Composition score (1-10)

        Returns:
            Quality score (1-10)

        Formula (clarifications):
        quality = (0.6 * scene) + (0.25 * motion) + (0.15 * composition)
        """
        quality = (
            self.score_weights['scene'] * scene_score +
            self.score_weights['motion'] * motion_score +
            self.score_weights['composition'] * composition_score
        )
        return round(quality, 1)

    def classify_segment(
        self,
        motion_score: float,
        scene_score: float,
        composition_score: float
    ) -> List[str]:
        """Assign classification tags based on scores.

        Args:
            motion_score: Motion score (1-10)
            scene_score: Scene change score (1-10)
            composition_score: Composition score (1-10)

        Returns:
            List of classification tags

        Tags (research.md):
        - high-action: motion >= 7
        - static: motion <= 3
        - dynamic-scene: scene >= 6
        - visually-rich: composition >= 8
        - highlight-candidate: motion >= 6 AND scene >= 6
        - neutral: default
        """
        tags = []

        if motion_score >= 7:
            tags.append("high-action")
        if motion_score <= 3:
            tags.append("static")
        if scene_score >= 6:
            tags.append("dynamic-scene")
        if composition_score >= 8:
            tags.append("visually-rich")
        if motion_score >= 6 and scene_score >= 6:
            tags.append("highlight-candidate")
        if not tags:
            tags.append("neutral")

        return tags
