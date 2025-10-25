"""Phase 5: Audio - Normalize audio and mix background music."""

import time
import shutil
from pathlib import Path

from ..models.checkpoint import Phase4Checkpoint, Phase5Checkpoint
from ..models.pipeline_config import PipelineConfig
from ..video.ffmpeg_wrapper import FFmpegWrapper
from ..utils.logger import get_logger
from ..utils.progress import ProgressReporter

logger = get_logger(__name__)


class Phase5Audio:
    """Phase 5: Audio processing and mixing.

    Process (Basic for MVP):
    1. Load Phase4 output video
    2. Optionally normalize audio levels
    3. Save final output
    4. Create Phase5Checkpoint

    Advanced (User Story 4):
    - Mix background music (FR-026)
    - Audio ducking (FR-027)
    """

    def __init__(self, config: PipelineConfig, progress: ProgressReporter):
        """Initialize Phase 5.

        Args:
            config: Pipeline configuration
            progress: Progress reporter
        """
        self.config = config
        self.progress = progress
        self.ffmpeg = FFmpegWrapper()

    def execute(
        self,
        phase4_checkpoint: Phase4Checkpoint,
        input_video_path: str,
        output_path: str,
        normalize: bool = False,
        background_music: str = None
    ) -> Phase5Checkpoint:
        """Execute audio phase.

        Args:
            phase4_checkpoint: Checkpoint from Phase 4
            input_video_path: Path to composed video from Phase 4
            output_path: Final output path
            normalize: Whether to normalize audio (default: False for MVP)
            background_music: Path to background music file (US4, not implemented)

        Returns:
            Phase5Checkpoint
        """
        start_time = time.time()
        logger.info("Starting Phase 5: Audio processing")
        self.progress.update("Phase 5: Audio - Processing audio")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # For MVP: If no audio processing needed, just copy the file
        if not normalize and not background_music:
            logger.info("No audio processing requested, copying video to final output")
            self.progress.update("Phase 5: Audio - Copying to final output")
            shutil.copy2(input_video_path, output_path)
            logger.info(f"Copied video to: {output_path}")

        # If normalization requested
        elif normalize and not background_music:
            logger.info("Normalizing audio levels")
            self.progress.update("Phase 5: Audio - Normalizing audio")
            self.ffmpeg.normalize_audio(
                input_path=input_video_path,
                output_path=output_path,
                target_db=-16.0
            )
            logger.info(f"Normalized audio saved to: {output_path}")

        # If background music requested (US4 - not fully implemented in MVP)
        elif background_music:
            if not Path(background_music).exists():
                raise FileNotFoundError(f"Background music file not found: {background_music}")

            logger.info("Mixing background music")
            self.progress.update("Phase 5: Audio - Mixing background music")

            # If also normalizing, do it first to a temp file
            if normalize:
                import tempfile
                temp_file = tempfile.mktemp(suffix='.mp4')
                self.ffmpeg.normalize_audio(
                    input_path=input_video_path,
                    output_path=temp_file,
                    target_db=-16.0
                )
                input_for_mixing = temp_file
            else:
                input_for_mixing = input_video_path

            # Mix background music
            self.ffmpeg.mix_audio(
                video_path=input_for_mixing,
                music_path=background_music,
                output_path=output_path,
                music_volume=0.3
            )

            # Clean up temp file if created
            if normalize:
                try:
                    Path(temp_file).unlink()
                except:
                    pass

            logger.info(f"Mixed audio saved to: {output_path}")

        phase_duration = time.time() - start_time

        checkpoint = Phase5Checkpoint(
            input_video_paths=phase4_checkpoint.input_video_paths,
            phase_duration_seconds=phase_duration,
            normalize_audio=normalize,
            background_music_file=background_music
        )

        logger.info(f"Phase 5 complete: Final video created in {phase_duration:.1f}s")
        self.progress.update("Phase 5: Audio complete")
        return checkpoint
