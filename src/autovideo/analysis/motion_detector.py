"""Motion detection using frame differencing."""

import cv2
import numpy as np
from typing import List


class MotionDetector:
    """Detects motion between video frames using frame differencing.

    Based on research.md:
    - Frame differencing with binary thresholding
    - Threshold: 25 (on 0-255 scale)
    - Returns motion score 1-10

    TODO: Implement cv2.absdiff for frame differencing
    TODO: Apply cv2.threshold with threshold=25
    TODO: Calculate motion percentage from non-zero pixels
    TODO: Normalize to 1-10 scale
    """

    def __init__(self, threshold: int = 25):
        """Initialize motion detector.

        Args:
            threshold: Binary threshold for motion detection (0-255)
        """
        self.threshold = threshold

    def detect_motion(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Detect motion between two frames.

        Args:
            frame1: First frame (numpy array)
            frame2: Second frame (numpy array)

        Returns:
            Motion score (1-10)
        """
        # Convert to grayscale
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        # Compute absolute difference
        diff = cv2.absdiff(gray1, gray2)

        # Apply binary threshold
        _, thresh = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)

        # Calculate percentage of pixels with motion
        motion_pixels = np.count_nonzero(thresh)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        motion_ratio = motion_pixels / total_pixels

        # Scale to 1-10 (non-linear to emphasize high-motion segments)
        # motion_ratio typically ranges 0-0.3, so multiply by 30 to get 0-10 range
        score = min(10.0, max(1.0, motion_ratio * 30 + 1))
        return score

    def analyze_segment(self, frames: List[np.ndarray]) -> float:
        """Analyze motion across all frames in a segment.

        Args:
            frames: List of video frames

        Returns:
            Average motion score for segment (1-10)
        """
        if len(frames) < 2:
            return 1.0  # No motion with single frame

        scores = []
        for i in range(len(frames) - 1):
            score = self.detect_motion(frames[i], frames[i + 1])
            scores.append(score)

        return float(np.mean(scores))
