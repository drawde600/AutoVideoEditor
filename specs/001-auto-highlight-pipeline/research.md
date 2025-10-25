# Research: Automatic Video Highlight Pipeline

**Feature**: 001-auto-highlight-pipeline
**Date**: 2025-10-25
**Purpose**: Technical decisions and implementation patterns for video processing pipeline

---

## 1. OpenCV Integration Patterns for Frame Analysis

### Decision
Use **OpenCV VideoCapture with frame sampling** for efficient video analysis.

### Rationale
- VideoCapture provides cross-platform video reading support
- Frame sampling (1fps) reduces processing time by 24-60x compared to analyzing every frame
- Sufficient accuracy for segment-level analysis (5-15 second segments)
- Low memory footprint - process frames sequentially, not loading entire video

### Implementation Pattern
```python
import cv2

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
sample_rate = fps  # Sample 1 frame per second

frame_count = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    if frame_count % sample_rate == 0:
        # Analyze this frame
        analyze_frame(frame)

    frame_count += 1

cap.release()
```

### Alternatives Considered
- **PyAV**: More control but steeper learning curve, overkill for frame extraction
- **MoviePy**: Higher-level but slower performance, designed for editing not analysis
- **FFmpeg direct extraction**: Requires subprocess management, OpenCV cleaner for analysis

---

## 2. FFmpeg Subprocess Management Best Practices

### Decision
Use **subprocess.run() with explicit command templates** for FFmpeg operations.

### Rationale
- Direct control over FFmpeg commands for precise video operations
- Better error handling via stderr capture
- Cross-platform compatibility (Windows, Linux, macOS)
- No dependency on Python wrappers with incomplete feature support

### Implementation Pattern
```python
import subprocess
import json

def run_ffmpeg(command, capture_output=True):
    """Execute FFmpeg command with error handling"""
    try:
        result = subprocess.run(
            command,
            capture_output=capture_output,
            text=True,
            check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"FFmpeg error: {e.stderr}")

# Example: Extract segment
def extract_segment(input_path, output_path, start_time, duration):
    command = [
        'ffmpeg',
        '-i', input_path,
        '-ss', str(start_time),
        '-t', str(duration),
        '-c', 'copy',  # Copy codec (fast, no re-encoding)
        '-y',  # Overwrite output
        output_path
    ]
    run_ffmpeg(command)
```

### Command Templates Needed
1. **Segment extraction**: `-ss` (start) + `-t` (duration) + `-c copy`
2. **Concatenation**: `concat` demuxer with file list
3. **Audio normalization**: `loudnorm` filter
4. **Text overlay**: `drawtext` filter
5. **Subtitle overlay**: `-vf subtitles=file.srt`
6. **Transition effects**: `xfade` filter between clips

### Alternatives Considered
- **ffmpeg-python**: Pythonic but adds abstraction layer, harder to debug
- **PyAV**: Lower-level, better for custom codecs but complex for standard operations

---

## 3. Motion Detection Algorithms

### Decision
Use **frame differencing with binary thresholding** for motion detection.

### Rationale
- Simple, fast, and effective for highlight detection use case
- Works well with 1fps sampling for segment-level analysis
- Low computational cost (important for 2-hour videos)
- Sufficient for distinguishing static vs dynamic content

### Implementation Pattern
```python
import cv2
import numpy as np

def calculate_motion_score(frame1, frame2):
    """Calculate motion score between consecutive frames (0-10)"""
    # Convert to grayscale
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    # Compute absolute difference
    diff = cv2.absdiff(gray1, gray2)

    # Apply threshold to get binary motion mask
    _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

    # Calculate percentage of pixels with motion
    motion_pixels = np.count_nonzero(thresh)
    total_pixels = thresh.shape[0] * thresh.shape[1]
    motion_ratio = motion_pixels / total_pixels

    # Scale to 1-10 (non-linear to emphasize high-motion segments)
    score = min(10, int(motion_ratio * 100) + 1)
    return score
```

### Alternatives Considered
- **Optical Flow**: More accurate but 10-20x slower, overkill for segment-level analysis
- **Background Subtraction**: Good for stationary camera, but gaming/vlogs have moving cameras
- **Deep Learning (action recognition)**: High accuracy but requires GPU, slow, complex

---

## 4. Scene Change Detection Techniques

### Decision
Use **histogram comparison with Chi-Square distance** for scene change detection.

### Rationale
- Detects significant visual changes (cuts, transitions, new scenes)
- Color histogram captures overall visual composition
- Chi-Square provides normalized distance metric (0-1 range)
- Fast computation, works well with frame sampling

### Implementation Pattern
```python
import cv2

def calculate_scene_change_score(frame1, frame2):
    """Calculate scene change score between frames (0-10)"""
    # Calculate color histograms
    hist1 = cv2.calcHist([frame1], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    hist2 = cv2.calcHist([frame2], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])

    # Normalize histograms
    cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

    # Compare using Chi-Square
    score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CHISQR)

    # Normalize to 1-10 scale (scene changes typically 0.1-1.0 range)
    normalized_score = min(10, int(score * 10) + 1)
    return normalized_score
```

### Scene Change Threshold
- Threshold: Chi-Square distance > 0.3 indicates scene change
- Use for segmentation boundaries (start new segment on scene change)

### Alternatives Considered
- **Edge-based detection**: Sensitive to noise, less reliable
- **Deep learning (shot boundary detection)**: Overkill, slow
- **Correlation-based**: Similar performance, Chi-Square more standard

---

## 5. Visual Composition Scoring Heuristics

### Decision
Use **multi-factor composition score** combining edge density, color diversity, and rule-of-thirds alignment.

### Rationale
- Edge density indicates visual complexity/interest
- Color diversity measures visual richness
- Rule-of-thirds (optional) captures compositional quality
- Combined score provides holistic quality assessment

### Implementation Pattern
```python
import cv2
import numpy as np

def calculate_composition_score(frame):
    """Calculate visual composition score (0-10)"""
    # 1. Edge density (Canny edge detection)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.count_nonzero(edges) / edges.size
    edge_score = min(10, int(edge_density * 100))

    # 2. Color diversity (unique colors in reduced palette)
    small = cv2.resize(frame, (50, 50))
    unique_colors = len(np.unique(small.reshape(-1, small.shape[2]), axis=0))
    color_score = min(10, unique_colors // 100 + 1)

    # 3. Brightness variance (avoid too dark/bright)
    brightness = np.mean(gray)
    brightness_score = 10 if 40 < brightness < 220 else 5

    # Weighted combination
    composition_score = int(
        edge_score * 0.5 +
        color_score * 0.3 +
        brightness_score * 0.2
    )

    return max(1, min(10, composition_score))
```

### Alternatives Considered
- **Deep learning aesthetics models**: High accuracy but slow, requires GPU
- **Simple contrast/sharpness**: Less comprehensive
- **SIFT/SURF features**: Overkill for quality scoring

---

## 6. Quality Score Combination Formula

### Decision
**Weighted average**: Scene Changes (60%), Motion (25%), Composition (15%)

### Rationale
- Scene changes are primary indicator of "interesting" content (new visual content, transitions)
- Motion indicates action and dynamics but secondary to scene variety
- Composition ensures visual quality baseline
- Weights prioritize visual variety and content changes over raw motion

### Implementation Pattern
```python
def calculate_segment_quality_score(segment_frames):
    """Calculate overall quality score for a segment (1-10)"""
    motion_scores = []
    scene_scores = []
    composition_scores = []

    prev_frame = None
    for frame in segment_frames:
        if prev_frame is not None:
            motion_scores.append(calculate_motion_score(prev_frame, frame))
            scene_scores.append(calculate_scene_change_score(prev_frame, frame))
        composition_scores.append(calculate_composition_score(frame))
        prev_frame = frame

    # Average scores across segment
    avg_motion = np.mean(motion_scores) if motion_scores else 5
    avg_scene = np.mean(scene_scores) if scene_scores else 5
    avg_composition = np.mean(composition_scores) if composition_scores else 5

    # Weighted combination
    final_score = (
        avg_scene * 0.6 +
        avg_motion * 0.25 +
        avg_composition * 0.15
    )

    return round(final_score, 1)
```

### Minimum Quality Threshold
- Threshold: 7.0 (segments below this fail as "no interesting content")
- Configurable via CLI: `--min-quality 7.0`

---

## 7. JSON Schema Validation Approaches

### Decision
Use **Pydantic models** for checkpoint validation and serialization.

### Rationale
- Type safety with Python type hints
- Automatic validation on model instantiation
- JSON serialization/deserialization built-in
- Better error messages than raw jsonschema
- Native Python integration (no external schema files to maintain)

### Implementation Pattern
```python
from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime

class Segment(BaseModel):
    """Segment model with validation"""
    start_time: float = Field(..., ge=0, description="Start timestamp in seconds")
    end_time: float = Field(..., gt=0, description="End timestamp in seconds")
    duration: float = Field(..., ge=5, le=15, description="Segment duration (5-15 sec)")
    quality_score: Optional[float] = Field(None, ge=1, le=10)
    classifications: List[str] = Field(default_factory=list)
    included: bool = True

    @validator('end_time')
    def end_after_start(cls, v, values):
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError('end_time must be after start_time')
        return v

class Phase1Checkpoint(BaseModel):
    """Phase 1: Segmentation checkpoint"""
    phase: int = 1
    timestamp: datetime
    input_video: str
    segments: List[Segment]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

# Usage
checkpoint = Phase1Checkpoint(
    timestamp=datetime.now(),
    input_video="video.mp4",
    segments=[...]
)
checkpoint_json = checkpoint.json()  # Serialize
loaded = Phase1Checkpoint.parse_raw(checkpoint_json)  # Deserialize + validate
```

### Alternatives Considered
- **jsonschema library**: More verbose, requires separate schema files
- **dataclasses + manual validation**: No automatic validation
- **attrs**: Similar to Pydantic but less feature-rich

---

## 8. Progress Reporting Patterns

### Decision
Use **callback-based progress reporting** with percentage completion and operation descriptions.

### Rationale
- Decouples progress reporting from business logic
- Supports multiple output targets (console, file, GUI future)
- Provides both coarse (phase) and fine (operation) granularity
- Enables time estimation based on past phases

### Implementation Pattern
```python
from typing import Callable, Optional
import time

class ProgressReporter:
    """Thread-safe progress reporting"""

    def __init__(self, total_operations: int, callback: Optional[Callable] = None):
        self.total_operations = total_operations
        self.completed_operations = 0
        self.current_operation = ""
        self.start_time = time.time()
        self.callback = callback or self._default_callback

    def update(self, operation: str, increment: int = 1):
        """Update progress with operation description"""
        self.current_operation = operation
        self.completed_operations += increment

        percentage = (self.completed_operations / self.total_operations) * 100
        elapsed = time.time() - self.start_time

        # Estimate remaining time
        if self.completed_operations > 0:
            rate = elapsed / self.completed_operations
            remaining = rate * (self.total_operations - self.completed_operations)
        else:
            remaining = 0

        self.callback(percentage, operation, elapsed, remaining)

    def _default_callback(self, percentage, operation, elapsed, remaining):
        """Default console output"""
        print(f"[{percentage:5.1f}%] {operation} | Elapsed: {elapsed:.1f}s | Remaining: ~{remaining:.1f}s")

# Usage in pipeline phase
reporter = ProgressReporter(total_operations=100)
for i, segment in enumerate(segments):
    reporter.update(f"Analyzing segment {i+1}/{len(segments)}")
    analyze_segment(segment)
```

### Console Output Format
```
[  5.2%] Extracting frames from video | Elapsed: 12.3s | Remaining: ~223.1s
[ 15.8%] Detecting motion in segment 15/100 | Elapsed: 45.2s | Remaining: ~240.5s
[100.0%] Phase 1 complete | Elapsed: 287.4s | Remaining: ~0.0s
```

### Alternatives Considered
- **tqdm library**: Great for simple loops, less flexible for complex operations
- **Rich library**: Beautiful output but heavy dependency
- **Simple print statements**: No structure, hard to parse

---

## 9. Python Logging Configuration

### Decision
Use **Python logging module with YAML configuration** for multi-level output.

### Rationale
- Built-in to Python, no extra dependencies
- Supports multiple handlers (console, file) simultaneously
- Configurable log levels per module
- YAML config allows runtime customization without code changes

### Implementation Pattern

**config/logging.yaml**:
```yaml
version: 1
disable_existing_loggers: false

formatters:
  simple:
    format: '%(levelname)s: %(message)s'
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: simple
    stream: ext://sys.stdout

  file:
    class: logging.FileHandler
    level: DEBUG
    formatter: detailed
    filename: output/logs/pipeline.log
    mode: 'a'

loggers:
  autovideo:
    level: DEBUG
    handlers: [console, file]
    propagate: false

root:
  level: WARNING
  handlers: [console, file]
```

**Python code**:
```python
import logging
import logging.config
import yaml

def setup_logging(config_path='config/logging.yaml', verbosity='detailed'):
    """Setup logging from YAML config"""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Override console level based on verbosity arg
    level_map = {
        'minimal': logging.ERROR,
        'moderate': logging.WARNING,
        'detailed': logging.INFO,
        'verbose': logging.DEBUG
    }
    config['handlers']['console']['level'] = level_map.get(verbosity, logging.INFO)

    logging.config.dictConfig(config)

# Usage
setup_logging(verbosity='detailed')
logger = logging.getLogger('autovideo.phases.segmentation')
logger.info("Starting segmentation phase")
logger.debug(f"Processing frame {frame_num}")
```

### Log Levels by Verbosity
- **minimal**: ERROR only (failures)
- **moderate**: WARNING + ERROR (issues + failures)
- **detailed** (default): INFO + WARNING + ERROR (progress + issues + failures)
- **verbose**: DEBUG + INFO + WARNING + ERROR (everything)

### Alternatives Considered
- **loguru**: Simpler but non-standard, harder to integrate with existing tools
- **structlog**: Great for structured logging but overkill for CLI tool
- **print statements**: No levels, no filtering, no file output

---

## 10. Segment Classification Approach

### Decision
Use **rule-based classification** with motion/scene patterns, not ML.

### Rationale
- Simpler to implement and debug
- No training data required
- Deterministic and explainable
- Sufficient for initial version (ML can be added later)

### Classification Rules
```python
def classify_segment(segment, motion_score, scene_score, composition_score):
    """Classify segment based on scoring patterns"""
    classifications = []

    if motion_score >= 7:
        classifications.append("high-action")
    elif motion_score <= 3:
        classifications.append("static")

    if scene_score >= 6:
        classifications.append("dynamic-scene")

    if composition_score >= 8:
        classifications.append("visually-rich")

    if motion_score >= 6 and scene_score >= 6:
        classifications.append("highlight-candidate")

    if not classifications:
        classifications.append("neutral")

    return classifications
```

### Classification Tags
- `high-action`: Motion score ≥ 7
- `static`: Motion score ≤ 3
- `dynamic-scene`: Scene change score ≥ 6
- `visually-rich`: Composition score ≥ 8
- `highlight-candidate`: Motion ≥ 6 AND scene ≥ 6
- `neutral`: Default if no other tags apply

---

## Summary of Technical Decisions

| Area | Decision | Key Benefit |
|------|----------|-------------|
| Frame Analysis | OpenCV VideoCapture + 1fps sampling | Fast, low memory |
| FFmpeg Integration | subprocess.run() with command templates | Direct control, better errors |
| Motion Detection | Frame differencing + thresholding | Simple, fast, effective |
| Scene Detection | Histogram comparison (Chi-Square) | Reliable cut detection |
| Composition Scoring | Edge density + color diversity | Holistic quality measure |
| Quality Formula | Weighted: Scene 60%, Motion 25%, Comp 15% | Prioritizes visual variety |
| Validation | Pydantic models | Type-safe, auto-validation |
| Progress Reporting | Callback-based with time estimation | Flexible, informative |
| Logging | Python logging + YAML config | Standard, configurable |
| Classification | Rule-based patterns | Simple, deterministic |

---

## Remaining Implementation Details

### FFmpeg Command Templates (to be implemented)

1. **Segment Extraction**:
   ```bash
   ffmpeg -i input.mp4 -ss START -t DURATION -c copy output.mp4
   ```

2. **Concatenation** (concat demuxer):
   ```bash
   # Create file_list.txt with segments
   ffmpeg -f concat -safe 0 -i file_list.txt -c copy output.mp4
   ```

3. **Audio Normalization** (loudnorm):
   ```bash
   ffmpeg -i input.mp4 -af loudnorm=I=-16:TP=-1.5:LRA=11 output.mp4
   ```

4. **Text Overlay** (drawtext):
   ```bash
   ffmpeg -i input.mp4 -vf "drawtext=text='Text':fontsize=24:x=10:y=10" output.mp4
   ```

5. **Subtitle Overlay**:
   ```bash
   ffmpeg -i input.mp4 -vf subtitles=subs.srt output.mp4
   ```

6. **Background Music Mixing**:
   ```bash
   ffmpeg -i video.mp4 -i music.mp3 -filter_complex "[0:a][1:a]amix=inputs=2:duration=first" output.mp4
   ```

### Performance Tuning Parameters

- **Frame sample rate**: Default 1fps, configurable via `--sample-rate`
- **Quality threshold**: Default 7.0, configurable via `--min-quality`
- **Segment duration**: Fixed 5-15 seconds per FR-002
- **Score weights**: Scene 0.6, Motion 0.25, Composition 0.15 (hardcoded initially)

---

**Research Status**: Complete
**Next Phase**: Generate data-model.md, contracts/, quickstart.md
