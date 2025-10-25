"""Command-line interface for AutoVideo pipeline."""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional

from .models.pipeline_config import PipelineConfig
from .models.checkpoint import Phase1Checkpoint, Phase2Checkpoint, Phase3Checkpoint, Phase4Checkpoint, Phase5Checkpoint
from .phases.phase1_segmentation import Phase1Segmentation
from .phases.phase2_ranking import Phase2Ranking
from .phases.phase3_assembly import Phase3Assembly
from .phases.phase4_composition import Phase4Composition
from .phases.phase5_audio import Phase5Audio
from .utils.logger import setup_logging, get_logger
from .utils.progress import ProgressReporter
from .video.ffmpeg_wrapper import FFmpegWrapper

# Module-level logger (will be configured later)
logger = None


class PipelineOrchestrator:
    """Orchestrates the 5-phase video highlight pipeline.

    Phases:
    1. Segmentation - Extract 5-15s segments
    2. Ranking - Score and classify segments
    3. Assembly - Select and order segments
    4. Composition - Apply transitions and effects (MVP: placeholder)
    5. Audio - Normalize and mix audio (MVP: placeholder)
    """

    def __init__(self, config: PipelineConfig):
        """Initialize pipeline orchestrator.

        Args:
            config: Pipeline configuration
        """
        self.config = config
        self.progress = ProgressReporter(verbose=True)

        # Checkpoints
        self.phase1_checkpoint: Optional[Phase1Checkpoint] = None
        self.phase2_checkpoint: Optional[Phase2Checkpoint] = None
        self.phase3_checkpoint: Optional[Phase3Checkpoint] = None
        self.phase4_checkpoint: Optional[Phase4Checkpoint] = None
        self.phase5_checkpoint: Optional[Phase5Checkpoint] = None

        # FFmpeg wrapper
        self.ffmpeg = FFmpegWrapper()

    def run(self) -> str:
        """Run the complete pipeline.

        Returns:
            Path to final output video (for MVP, returns checkpoint path)
        """
        global logger
        logger.info("=" * 60)
        logger.info("AutoVideo Highlight Pipeline - Starting")
        logger.info("=" * 60)
        logger.info(f"Input videos: {len(self.config.input_videos)}")
        logger.info(f"Target duration: {self.config.target_duration}s")
        logger.info(f"Min quality threshold: {self.config.min_quality_threshold}")
        logger.info(f"Sample rate: {self.config.sample_rate_fps} fps")
        if self.config.resize_to_hd:
            logger.info("Resize to HD: ENABLED (4K frames will be resized to 1920x1080 for faster processing)")

        self.progress.start("Initializing pipeline")

        try:
            # Check FFmpeg availability
            if not self.ffmpeg.check_ffmpeg_available():
                raise RuntimeError(
                    "FFmpeg not found in PATH. Please install FFmpeg to use this tool.\n"
                    "Download from: https://ffmpeg.org/download.html"
                )
            logger.info("✓ FFmpeg found")

            # Create output directories
            self._create_output_dirs()

            # Run Phase 1: Segmentation
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 1: SEGMENTATION")
            logger.info("=" * 60)
            self.run_phase1()
            self._save_checkpoint(self.phase1_checkpoint, "phase1")

            # Run Phase 2: Ranking
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 2: RANKING")
            logger.info("=" * 60)
            self.run_phase2()
            self._save_checkpoint(self.phase2_checkpoint, "phase2")

            # Run Phase 3: Assembly
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 3: ASSEMBLY")
            logger.info("=" * 60)
            self.run_phase3()
            self._save_checkpoint(self.phase3_checkpoint, "phase3")

            # Run Phase 4: Composition
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 4: COMPOSITION")
            logger.info("=" * 60)
            # Create intermediate output path for Phase 4
            phase4_output = self.config.output_directory / "intermediate_composed.mp4"
            self.run_phase4(str(phase4_output))
            self._save_checkpoint(self.phase4_checkpoint, "phase4")

            # Run Phase 5: Audio
            logger.info("\n" + "=" * 60)
            logger.info("PHASE 5: AUDIO")
            logger.info("=" * 60)
            # Determine final output path from config or use default
            final_output = self.config.output_directory / "highlight.mp4"
            self.run_phase5(str(phase4_output), str(final_output))
            self._save_checkpoint(self.phase5_checkpoint, "phase5")

            # Final summary
            logger.info("\n" + "=" * 60)
            logger.info("✅ PIPELINE COMPLETE!")
            logger.info("=" * 60)
            logger.info("✓ Phase 1: Segmentation complete")
            logger.info("✓ Phase 2: Ranking complete")
            logger.info("✓ Phase 3: Assembly complete")
            logger.info("✓ Phase 4: Composition complete")
            logger.info("✓ Phase 5: Audio complete")
            logger.info(f"\n✓ Processed {len(self.config.input_videos)} input video(s)")
            logger.info(f"✓ Extracted {self.phase1_checkpoint.total_segments} total segments")
            logger.info(f"✓ Selected {len(self.phase3_checkpoint.selected_segments)} best segments")
            logger.info(f"✓ Final duration: {self.phase3_checkpoint.actual_duration:.1f}s")
            logger.info(f"\n🎬 Final video: {final_output}")

            self.progress.complete("Pipeline execution complete")

            return str(final_output)

        except Exception as e:
            logger.error(f"\n❌ Pipeline failed: {e}", exc_info=True)
            logger.error("\nCheckpoints saved up to the failed phase.")
            raise

    def run_phase1(self) -> None:
        """Run Phase 1: Segmentation."""
        phase1 = Phase1Segmentation(self.config, self.progress)
        self.phase1_checkpoint = phase1.execute()

        logger.info(f"✓ Extracted {self.phase1_checkpoint.total_segments} segments")
        logger.info(f"✓ Phase duration: {self.phase1_checkpoint.phase_duration_seconds:.1f}s")

    def run_phase2(self) -> None:
        """Run Phase 2: Ranking."""
        if not self.phase1_checkpoint:
            raise RuntimeError("Phase 1 must complete before Phase 2")

        phase2 = Phase2Ranking(self.config, self.progress)
        self.phase2_checkpoint = phase2.execute(self.phase1_checkpoint)

        logger.info(f"✓ Scored {len(self.phase2_checkpoint.segments)} segments")
        logger.info(f"✓ {self.phase2_checkpoint.segments_above_threshold} segments above threshold")
        logger.info(f"✓ Phase duration: {self.phase2_checkpoint.phase_duration_seconds:.1f}s")

    def run_phase3(self) -> None:
        """Run Phase 3: Assembly."""
        if not self.phase2_checkpoint:
            raise RuntimeError("Phase 2 must complete before Phase 3")

        phase3 = Phase3Assembly(self.config, self.progress)
        self.phase3_checkpoint = phase3.execute(self.phase2_checkpoint)

        logger.info(f"✓ Selected {len(self.phase3_checkpoint.selected_segments)} segments")
        logger.info(f"✓ Actual duration: {self.phase3_checkpoint.actual_duration:.1f}s " +
                   f"(target: {self.phase3_checkpoint.target_duration}s)")
        logger.info(f"✓ Variety score: {self.phase3_checkpoint.variety_score:.2f}")
        logger.info(f"✓ Phase duration: {self.phase3_checkpoint.phase_duration_seconds:.1f}s")

    def run_phase4(self, output_path: str) -> None:
        """Run Phase 4: Composition.

        Args:
            output_path: Path for composed video output
        """
        if not self.phase2_checkpoint or not self.phase3_checkpoint:
            raise RuntimeError("Phase 2 and 3 must complete before Phase 4")

        phase4 = Phase4Composition(self.config, self.progress)
        self.phase4_checkpoint = phase4.execute(
            phase2_checkpoint=self.phase2_checkpoint,
            phase3_checkpoint=self.phase3_checkpoint,
            output_path=output_path,
            transition_type="cut"
        )

        logger.info(f"✓ Composed video created")
        logger.info(f"✓ Transition type: {self.phase4_checkpoint.transition_type}")
        logger.info(f"✓ Phase duration: {self.phase4_checkpoint.phase_duration_seconds:.1f}s")

    def run_phase5(self, input_path: str, output_path: str) -> None:
        """Run Phase 5: Audio.

        Args:
            input_path: Path to composed video from Phase 4
            output_path: Final output path
        """
        if not self.phase4_checkpoint:
            raise RuntimeError("Phase 4 must complete before Phase 5")

        phase5 = Phase5Audio(self.config, self.progress)
        self.phase5_checkpoint = phase5.execute(
            phase4_checkpoint=self.phase4_checkpoint,
            input_video_path=input_path,
            output_path=output_path,
            normalize=False  # MVP: no normalization by default
        )

        logger.info(f"✓ Final video created: {output_path}")
        logger.info(f"✓ Audio normalized: {self.phase5_checkpoint.normalize_audio}")
        logger.info(f"✓ Phase duration: {self.phase5_checkpoint.phase_duration_seconds:.1f}s")

    def _create_output_dirs(self) -> None:
        """Create output directories."""
        self.config.output_directory.mkdir(parents=True, exist_ok=True)
        self.config.checkpoint_directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory: {self.config.output_directory}")
        logger.info(f"Checkpoint directory: {self.config.checkpoint_directory}")

    def _save_checkpoint(self, checkpoint, phase_name: str) -> None:
        """Save checkpoint to JSON file.

        Args:
            checkpoint: Checkpoint to save
            phase_name: Phase name (e.g., 'phase1')
        """
        filename = f"{phase_name}_{checkpoint.__class__.__name__.lower()}.json"
        filepath = self.config.checkpoint_directory / filename

        with open(filepath, 'w') as f:
            json.dump(checkpoint.model_dump(mode='json'), f, indent=2, default=str)

        logger.debug(f"Checkpoint saved: {filepath}")

    def _progress_callback(self, message: str) -> None:
        """Progress callback handler.

        Args:
            message: Progress message
        """
        # Additional progress handling can be added here
        pass


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Optional argument list (for testing)

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="AutoVideo - Automatic Video Highlight Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with single video
  python -m autovideo --input video.mp4 --output highlights.mp4 --duration 180

  # Multiple videos with custom quality threshold
  python -m autovideo --input video1.mp4 video2.mp4 --duration 300 --min-quality 8.0

  # 4K video with resize for faster processing
  python -m autovideo --input 4k_drone.mp4 --duration 300 --resize-to-hd

  # Verbose logging
  python -m autovideo --input video.mp4 --output out.mp4 --verbosity verbose
        """
    )

    # Required arguments
    parser.add_argument(
        '--input', '-i',
        nargs='+',
        required=True,
        help='Input video file(s) (MP4 format)'
    )

    # Optional arguments
    parser.add_argument(
        '--output', '-o',
        default='output/highlight.mp4',
        help='Output video file path (default: output/highlight.mp4)'
    )

    parser.add_argument(
        '--duration', '-d',
        type=float,
        default=300.0,
        help='Target highlight duration in seconds (default: 300s = 5min)'
    )

    parser.add_argument(
        '--min-quality',
        type=float,
        default=7.0,
        help='Minimum quality score threshold 1-10 (default: 7.0)'
    )

    parser.add_argument(
        '--sample-rate',
        type=float,
        default=1.0,
        help='Frame sampling rate in fps (default: 1.0)'
    )

    parser.add_argument(
        '--verbosity',
        choices=['minimal', 'moderate', 'detailed', 'verbose'],
        default='detailed',
        help='Logging verbosity level (default: detailed)'
    )

    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory for all generated files (default: output)'
    )

    parser.add_argument(
        '--resize-to-hd',
        action='store_true',
        help='Resize 4K frames to 1920x1080 for faster processing (recommended for 4K input)'
    )

    parser.add_argument(
        '--save-segments',
        action='store_true',
        help='Save individual segments as MP4 files for visual verification (stored in output/segments/)'
    )

    return parser.parse_args(args)


def main(args: Optional[List[str]] = None) -> int:
    """Main CLI entry point.

    Args:
        args: Optional argument list (for testing)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    global logger

    try:
        # Parse arguments
        parsed_args = parse_args(args)

        # Setup logging
        output_dir = Path(parsed_args.output_dir)
        log_file = output_dir / "logs" / "pipeline.log"
        setup_logging(
            verbosity=parsed_args.verbosity,
            log_file=str(log_file)
        )
        logger = get_logger(__name__)

        # Create pipeline configuration
        config = PipelineConfig(
            input_videos=[str(Path(v).absolute()) for v in parsed_args.input],
            output_directory=output_dir,
            target_duration=parsed_args.duration,
            min_quality_threshold=parsed_args.min_quality,
            sample_rate_fps=parsed_args.sample_rate,
            logging_verbosity=parsed_args.verbosity,
            checkpoint_directory=output_dir / "checkpoints",
            resize_to_hd=parsed_args.resize_to_hd,
            save_segments=parsed_args.save_segments
        )

        # Validate inputs
        for video_path in config.input_videos:
            if not Path(video_path).exists():
                logger.error(f"Input video not found: {video_path}")
                return 1
            if not video_path.lower().endswith('.mp4'):
                logger.error(f"Input must be MP4 format: {video_path}")
                return 1

        # Run pipeline
        orchestrator = PipelineOrchestrator(config)
        result_path = orchestrator.run()

        logger.info(f"\n✓ Success! Result saved to: {result_path}")
        return 0

    except KeyboardInterrupt:
        if logger:
            logger.warning("\n\n⚠ Pipeline interrupted by user")
        return 130

    except Exception as e:
        if logger:
            logger.error(f"\n\n❌ Pipeline failed: {e}")
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
