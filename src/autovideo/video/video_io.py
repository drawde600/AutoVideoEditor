"""Video I/O utilities using OpenCV."""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Generator
from pathlib import Path
import os

from ..models.video_source import VideoSource


class VideoReader:
    """Video frame reader using OpenCV VideoCapture."""

    def __init__(self, video_path: str, sample_rate_fps: float = 1.0, resize_to_hd: bool = False):
        """Initialize video reader.

        Args:
            video_path: Path to video file
            sample_rate_fps: Frame sampling rate (default 1.0 = 1 frame per second)
            resize_to_hd: If True, resize frames to 1920x1080 for faster processing
        """
        self.video_path = video_path
        self.sample_rate_fps = sample_rate_fps
        self.resize_to_hd = resize_to_hd
        self.cap: Optional[cv2.VideoCapture] = None
        self.video_fps: float = 0.0
        self.frame_skip: int = 1

    def open(self) -> None:
        """Open video file for reading."""
        self.cap = cv2.VideoCapture(self.video_path)

        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video file: {self.video_path}")

        # Get video FPS and calculate frame skip interval
        self.video_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if self.video_fps == 0:
            raise RuntimeError(f"Invalid FPS (0) for video: {self.video_path}")

        # Calculate how many frames to skip between samples
        # sample_rate_fps = 1.0 means sample 1 frame per second
        # If video is 30fps, we skip 30 frames to get 1fps
        self.frame_skip = max(1, int(self.video_fps / self.sample_rate_fps))

    def read_frames(self, start_time: float = 0.0, end_time: Optional[float] = None) -> Generator[np.ndarray, None, None]:
        """Read frames from video with sampling.

        Args:
            start_time: Start time in seconds (default 0)
            end_time: End time in seconds (None = end of video)

        Yields:
            Video frames as numpy arrays
        """
        if self.cap is None:
            raise RuntimeError("Video not opened. Call open() first.")

        # Seek to start time
        if start_time > 0:
            start_frame = int(start_time * self.video_fps)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # Calculate end frame if end_time specified
        end_frame = None
        if end_time is not None:
            end_frame = int(end_time * self.video_fps)

        frame_count = 0
        while True:
            ret, frame = self.cap.read()

            if not ret:
                break

            current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

            # Check if we've reached end_time
            if end_frame is not None and current_frame >= end_frame:
                break

            # Yield frame only at sample intervals
            if frame_count % self.frame_skip == 0:
                # Resize to HD if requested and frame is larger
                if self.resize_to_hd and (frame.shape[1] > 1920 or frame.shape[0] > 1080):
                    frame = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_AREA)
                yield frame

            frame_count += 1

    def get_video_info(self) -> VideoSource:
        """Get video metadata as VideoSource model.

        Returns:
            VideoSource instance with video properties
        """
        if self.cap is None:
            # Temporarily open to get info
            temp_cap = cv2.VideoCapture(self.video_path)
            if not temp_cap.isOpened():
                raise RuntimeError(f"Failed to open video file: {self.video_path}")
        else:
            temp_cap = self.cap

        try:
            # Extract video properties
            fps = temp_cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(temp_cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(temp_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(temp_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Calculate duration
            if fps > 0:
                duration_seconds = total_frames / fps
            else:
                raise RuntimeError(f"Invalid FPS for video: {self.video_path}")

            # Get file size
            file_size_bytes = os.path.getsize(self.video_path)

            # Get file timestamp for chronological ordering
            file_timestamp = os.path.getmtime(self.video_path)

            # Generate video ID from filename
            video_id = Path(self.video_path).stem

            # Detect audio codec (simplified - assume AAC for MP4)
            # In production, would use ffprobe for accurate detection
            has_audio = True  # Assume has audio
            audio_codec = "aac"  # Assume AAC for MP4
            video_codec = "h264"  # Assume H.264 for MP4

            # Check for SRT file (GPS data)
            srt_path = str(Path(self.video_path).with_suffix('.srt'))
            srt_file_path = srt_path if os.path.exists(srt_path) else None

            return VideoSource(
                video_id=video_id,
                file_path=self.video_path,
                duration_seconds=duration_seconds,
                resolution=(width, height),
                frame_rate=fps,
                has_audio=has_audio,
                audio_codec=audio_codec,
                video_codec=video_codec,
                file_size_bytes=file_size_bytes,
                file_timestamp=file_timestamp,
                srt_file_path=srt_file_path
            )
        finally:
            if self.cap is None and temp_cap:
                temp_cap.release()

    def close(self) -> None:
        """Close video file and release resources."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def extract_frames_at_timestamps(
    video_path: str,
    timestamps: List[float],
    resize_to_hd: bool = False
) -> List[np.ndarray]:
    """Extract specific frames at given timestamps.

    Args:
        video_path: Path to video file
        timestamps: List of timestamps in seconds
        resize_to_hd: If True, resize frames to 1920x1080

    Returns:
        List of frames as numpy arrays
    """
    frames = []
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video file: {video_path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)

        for timestamp in timestamps:
            frame_number = int(timestamp * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

            ret, frame = cap.read()
            if ret:
                # Resize to HD if requested and frame is larger
                if resize_to_hd and (frame.shape[1] > 1920 or frame.shape[0] > 1080):
                    frame = cv2.resize(frame, (1920, 1080), interpolation=cv2.INTER_AREA)
                frames.append(frame)
            else:
                # If frame extraction fails, add None placeholder
                frames.append(None)
    finally:
        cap.release()

    return frames
