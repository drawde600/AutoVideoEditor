"""Visual composition analysis using edge density and color diversity."""

import cv2
import numpy as np
from typing import List


class CompositionAnalyzer:
    """Analyzes visual composition quality of video frames.

    Based on research.md:
    - Edge density using cv2.Canny
    - Color diversity using histogram
    - Brightness analysis
    - Returns composition score 1-10

    TODO: Implement edge detection with cv2.Canny
    TODO: Calculate color diversity from histogram
    TODO: Analyze brightness distribution
    TODO: Combine metrics into composition score
    """

    def analyze_frame(self, frame: np.ndarray) -> float:
        """Analyze composition quality of a single frame.

        Args:
            frame: Video frame (numpy array)

        Returns:
            Composition score (1-10)
        """
        # Calculate edge density
        edge_density = self.calculate_edge_density(frame)
        edge_score = min(10.0, edge_density * 100)

        # Calculate color diversity
        color_diversity = self.calculate_color_diversity(frame)
        color_score = min(10.0, color_diversity * 20)

        # Calculate brightness
        brightness = self.calculate_brightness(frame)
        # Prefer moderate brightness (40-220 range on 0-255 scale)
        brightness_score = 10.0 if 40 < brightness < 220 else 5.0

        # Weighted combination per research.md
        composition_score = (
            edge_score * 0.5 +
            color_score * 0.3 +
            brightness_score * 0.2
        )

        return max(1.0, min(10.0, composition_score))

    def calculate_edge_density(self, frame: np.ndarray) -> float:
        """Calculate edge density using Canny edge detector.

        Args:
            frame: Video frame

        Returns:
            Edge density (0-1)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Canny edge detection
        edges = cv2.Canny(gray, 50, 150)

        # Calculate edge density
        edge_pixels = np.count_nonzero(edges)
        total_pixels = edges.size
        edge_density = edge_pixels / total_pixels

        return edge_density

    def calculate_color_diversity(self, frame: np.ndarray) -> float:
        """Calculate color diversity from histogram.

        Args:
            frame: Video frame

        Returns:
            Color diversity score (0-1)
        """
        # Resize to small size for faster unique color counting
        small = cv2.resize(frame, (50, 50))

        # Count unique colors in reduced palette
        reshaped = small.reshape(-1, small.shape[2])
        unique_colors = len(np.unique(reshaped, axis=0))

        # Normalize to 0-1 range (max unique colors in 50x50 = 2500)
        diversity = min(1.0, unique_colors / 1000.0)

        return diversity

    def calculate_brightness(self, frame: np.ndarray) -> float:
        """Calculate average brightness.

        Args:
            frame: Video frame

        Returns:
            Brightness value (0-255)
        """
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Calculate mean brightness
        brightness = np.mean(gray)

        return brightness

    def analyze_segment(self, frames: List[np.ndarray]) -> float:
        """Analyze composition across all frames in a segment.

        Args:
            frames: List of video frames

        Returns:
            Average composition score for segment (1-10)
        """
        if not frames:
            return 1.0

        scores = []
        for frame in frames:
            score = self.analyze_frame(frame)
            scores.append(score)

        return float(np.mean(scores))
