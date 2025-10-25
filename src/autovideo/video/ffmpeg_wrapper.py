"""FFmpeg wrapper for video processing operations."""

import subprocess
import shutil
import tempfile
import os
from typing import List, Optional
from pathlib import Path


class FFmpegWrapper:
    """Wrapper for FFmpeg subprocess operations.

    Based on research.md:
    - Use subprocess.run() for direct control
    - Capture stderr for error messages
    - Raise RuntimeError with FFmpeg error on failure
    """

    @staticmethod
    def check_ffmpeg_available() -> bool:
        """Check if FFmpeg is available in PATH.

        Returns:
            True if FFmpeg is available, False otherwise
        """
        return shutil.which('ffmpeg') is not None

    @staticmethod
    def validate_mp4(file_path: str) -> bool:
        """Validate MP4 file headers using FFprobe.

        Args:
            file_path: Path to MP4 file

        Returns:
            True if valid MP4, False otherwise
        """
        try:
            # Use ffprobe to check if file is valid
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            # If ffprobe succeeds and outputs 'video', file is valid
            return result.returncode == 0 and 'video' in result.stdout.lower()

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return False

    @staticmethod
    def extract_segment(
        input_path: str,
        output_path: str,
        start_time: float,
        duration: float
    ) -> None:
        """Extract a segment from video using FFmpeg.

        Args:
            input_path: Input video file path
            output_path: Output segment file path
            start_time: Start time in seconds
            duration: Duration in seconds

        Raises:
            RuntimeError: If FFmpeg command fails
        """
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file
            '-ss', str(start_time),  # Seek to start time
            '-i', input_path,  # Input file
            '-t', str(duration),  # Duration to extract
            '-c', 'copy',  # Copy streams without re-encoding (fast)
            '-avoid_negative_ts', 'make_zero',  # Handle timestamp issues
            output_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg segment extraction failed: {e.stderr}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"FFmpeg segment extraction timed out for {input_path}"
            )

    @staticmethod
    def concatenate_videos(
        input_paths: List[str],
        output_path: str,
        transition_type: str = "cut"
    ) -> None:
        """Concatenate multiple video segments.

        Args:
            input_paths: List of input video file paths
            output_path: Output video file path
            transition_type: Transition type (cut, fade, dissolve)

        Raises:
            RuntimeError: If FFmpeg command fails
        """
        if not input_paths:
            raise ValueError("No input videos to concatenate")

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # For MVP, only support "cut" transitions (simple concat)
        if transition_type != "cut":
            raise NotImplementedError(
                f"Transition type '{transition_type}' not yet implemented. "
                "Only 'cut' transitions supported in MVP."
            )

        # Create temporary concat file
        concat_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False,
            encoding='utf-8'
        )

        try:
            # Write file paths to concat file
            for path in input_paths:
                # Use absolute paths and escape single quotes
                abs_path = str(Path(path).absolute()).replace("'", "'\\''")
                concat_file.write(f"file '{abs_path}'\n")
            concat_file.close()

            # Run FFmpeg concat
            cmd = [
                'ffmpeg',
                '-y',  # Overwrite output
                '-f', 'concat',  # Concat demuxer
                '-safe', '0',  # Allow absolute paths
                '-i', concat_file.name,  # Concat file
                '-c', 'copy',  # Copy streams without re-encoding
                output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                check=True
            )

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg concatenation failed: {e.stderr}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "FFmpeg concatenation timed out"
            )
        finally:
            # Clean up concat file
            try:
                os.unlink(concat_file.name)
            except:
                pass

    @staticmethod
    def normalize_audio(
        input_path: str,
        output_path: str,
        target_db: float = -16.0
    ) -> None:
        """Normalize audio levels using loudnorm filter.

        Args:
            input_path: Input video file path
            output_path: Output video file path
            target_db: Target loudness in dB LUFS (default -16)

        Raises:
            RuntimeError: If FFmpeg command fails
        """
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            'ffmpeg',
            '-y',
            '-i', input_path,
            '-af', f'loudnorm=I={target_db}:TP=-1.5:LRA=11',
            '-c:v', 'copy',  # Copy video stream
            '-c:a', 'aac',   # Re-encode audio
            '-b:a', '192k',  # Audio bitrate
            output_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg audio normalization failed: {e.stderr}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "FFmpeg audio normalization timed out"
            )

    @staticmethod
    def mix_audio(
        video_path: str,
        music_path: str,
        output_path: str,
        music_volume: float = 0.3
    ) -> None:
        """Mix background music with original audio.

        Args:
            video_path: Input video file path
            music_path: Background music file path
            output_path: Output video file path
            music_volume: Music volume relative to original (0-1)

        Raises:
            RuntimeError: If FFmpeg command fails
        """
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            'ffmpeg',
            '-y',
            '-i', video_path,
            '-i', music_path,
            '-filter_complex',
            f'[1:a]volume={music_volume}[music];[0:a][music]amix=inputs=2:duration=first',
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            output_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg audio mixing failed: {e.stderr}"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                "FFmpeg audio mixing timed out"
            )
