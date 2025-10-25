"""Progress reporting for pipeline execution."""

from typing import Callable, Optional
from dataclasses import dataclass
import time


@dataclass
class ProgressReport:
    """Real-time execution status during pipeline run.

    Attributes:
        current_phase: Phase currently executing (1-5)
        phase_name: Human-readable phase name
        percentage_complete: 0-100 completion percentage
        current_operation: Description of current operation
        elapsed_seconds: Time elapsed since start
        estimated_remaining_seconds: Estimated time remaining
    """
    current_phase: int
    phase_name: str
    percentage_complete: float
    current_operation: str
    elapsed_seconds: float
    estimated_remaining_seconds: Optional[float] = None


class ProgressReporter:
    """Simple progress reporter with console output.

    Usage:
        reporter = ProgressReporter()
        reporter.update("Processing video 1/5")
        reporter.update("Analyzing frames...")
    """

    def __init__(self, callback: Optional[Callable[[str], None]] = None, verbose: bool = True):
        """Initialize progress reporter.

        Args:
            callback: Optional callback function to receive progress updates
            verbose: Whether to print to console
        """
        self.callback = callback
        self.verbose = verbose
        self.start_time: Optional[float] = None

    def start(self, operation: str = "Starting pipeline") -> None:
        """Start progress tracking.

        Args:
            operation: Initial operation description
        """
        self.start_time = time.time()
        self.update(operation)

    def update(self, operation: str) -> None:
        """Update progress with current status.

        Args:
            operation: Description of current operation
        """
        if self.verbose:
            elapsed = ""
            if self.start_time:
                elapsed_sec = time.time() - self.start_time
                elapsed = f" [{elapsed_sec:.1f}s]"
            print(f"[Progress]{elapsed} {operation}")

        if self.callback:
            self.callback(operation)

    def complete(self, operation: str = "Pipeline complete") -> None:
        """Mark operation as complete.

        Args:
            operation: Completion message
        """
        if self.start_time:
            total_time = time.time() - self.start_time
            self.update(f"{operation} (total: {total_time:.1f}s)")
        else:
            self.update(operation)
