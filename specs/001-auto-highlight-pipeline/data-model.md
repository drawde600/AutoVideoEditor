# Data Model: Automatic Video Highlight Pipeline

**Feature**: 001-auto-highlight-pipeline
**Date**: 2025-10-25
**Purpose**: Entity definitions, relationships, and validation rules

---

## Entity Overview

```
VideoSource (input)
    ↓
Segment[] (extracted)
    ↓
Phase1Checkpoint → Phase2Checkpoint → Phase3Checkpoint → Phase4Checkpoint → Phase5Checkpoint
    ↓                                                                              ↓
PipelineConfig (settings)                                                  HighlightReel (output)
    ↓
ProgressReport (runtime)
LogFile (persistent)
```

---

## Core Entities

### 1. VideoSource

**Purpose**: Represents an input MP4 video file to be processed (one of potentially multiple source videos).

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `video_id` | `str` | Yes | Unique identifier | Unique ID for this video source |
| `file_path` | `str` | Yes | Must exist, `.mp4` extension | Absolute path to input video file |
| `duration_seconds` | `float` | Yes | > 0 | Total video duration in seconds |
| `resolution` | `Tuple[int, int]` | Yes | Width > 0, Height > 0 | Video resolution (width, height) |
| `frame_rate` | `float` | Yes | > 0, typically 24-60 | Frames per second |
| `has_audio` | `bool` | Yes | - | Whether video contains audio track |
| `audio_codec` | `str` | No | - | Audio codec (e.g., "aac", "mp3") |
| `video_codec` | `str` | No | - | Video codec (e.g., "h264") |
| `file_size_bytes` | `int` | Yes | >= 0 | File size in bytes |
| `srt_file_path` | `str` | No | File exists if provided | Path to GPS-enabled SRT subtitle file (optional) |

**Validation Rules**:
- FR-029: File must be MP4 format
- FR-037: If SRT file provided, system should parse GPS data
- Must be readable by OpenCV VideoCapture
- SC-004: Combined duration of all videos ≤ 4 hours (14400 seconds)
- SC-004: Resolution ≤ 1920x1080 (1080p)

**Lifecycle**:
- Created: At pipeline start (Phase 1 initialization)
- Read: Throughout all phases
- Modified: Never (immutable)

**Example**:
```python
VideoSource(
    video_id="video-001",
    file_path="/path/to/drone_video_1.mp4",
    duration_seconds=3600.5,
    resolution=(1920, 1080),
    frame_rate=30.0,
    has_audio=True,
    audio_codec="aac",
    video_codec="h264",
    file_size_bytes=2684354560,
    srt_file_path="/path/to/drone_video_1.srt"  # Optional GPS SRT file
)
```

---

### 2. Segment

**Purpose**: Represents an extracted clip from a source video with quality metrics.

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `segment_id` | `str` | Yes | Unique UUID | Unique identifier for segment |
| `video_id` | `str` | Yes | Must match VideoSource.video_id | Identifier of source video this segment belongs to |
| `start_time` | `float` | Yes | >= 0, < video duration | Start timestamp in seconds (relative to source video) |
| `end_time` | `float` | Yes | > start_time, <= video duration | End timestamp in seconds (relative to source video) |
| `duration` | `float` | Yes | 5.0 <= duration <= 15.0 | Segment duration (FR-002) |
| `quality_score` | `float` | No | 1.0 <= score <= 10.0 | Overall quality score (1-10) |
| `motion_score` | `float` | No | 1.0 <= score <= 10.0 | Motion analysis score |
| `scene_score` | `float` | No | 1.0 <= score <= 10.0 | Scene change score |
| `composition_score` | `float` | No | 1.0 <= score <= 10.0 | Visual composition score |
| `classifications` | `List[str]` | Yes | Valid tags only | Segment classification tags |
| `included` | `bool` | Yes | - | Whether segment is included in final reel |
| `manually_edited` | `bool` | Yes | Default False | Flag indicating manual user edit |
| `gps_coordinates` | `List[Tuple[float, float]]` | No | Valid lat/lon pairs | GPS path coordinates [(lat, lon), ...] |
| `gps_elevations` | `List[float]` | No | - | Elevation values in meters corresponding to coordinates |
| `gps_timestamps` | `List[float]` | No | - | Timestamps for each GPS point (relative to segment start) |
| `location_name` | `str` | No | - | Reverse-geocoded location (e.g., "San Francisco, USA") - populated in Phase 4 |

**Validation Rules**:
- FR-002: Duration must be 5-15 seconds
- FR-005: Quality score calculated from motion, scene, composition
- FR-008: Scores can be manually modified in checkpoint
- Derived: `duration = end_time - start_time`

**Classification Tags** (from research.md):
- `high-action`: Motion score ≥ 7
- `static`: Motion score ≤ 3
- `dynamic-scene`: Scene change score ≥ 6
- `visually-rich`: Composition score ≥ 8
- `highlight-candidate`: Motion ≥ 6 AND scene ≥ 6
- `neutral`: Default if no other tags

**State Transitions**:
```
Created (Phase 1)
    ↓
Scored (Phase 2)
    ↓
Selected/Rejected (Phase 3)
    ↓
Composed (Phase 4)
    ↓
Final (Phase 5)
```

**Example**:
```python
Segment(
    segment_id="550e8400-e29b-41d4-a716-446655440000",
    video_id="video-001",
    start_time=125.0,
    end_time=137.5,
    duration=12.5,
    quality_score=7.8,
    motion_score=8.2,
    scene_score=7.5,
    composition_score=7.7,
    classifications=["high-action", "highlight-candidate"],
    included=True,
    manually_edited=False,
    gps_coordinates=[(37.7749, -122.4194), (37.7750, -122.4195), (37.7751, -122.4196)],
    gps_elevations=[50.2, 52.1, 54.3],
    gps_timestamps=[0.0, 6.25, 12.5],
    location_name="San Francisco, California, USA"  # Populated in Phase 4
)
```

---

### 3. Checkpoint (Base)

**Purpose**: Persists pipeline state at each phase for manual override and resume capability.

**Fields** (common to all checkpoint types):

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `phase` | `int` | Yes | 1-5 | Phase number (1=Segmentation, 2=Ranking, etc.) |
| `timestamp` | `datetime` | Yes | - | When checkpoint was created |
| `input_video_paths` | `List[str]` | Yes | Must exist | Paths to all source videos |
| `pipeline_version` | `str` | Yes | SemVer format | Version of pipeline that created this |
| `phase_duration_seconds` | `float` | Yes | >= 0 | Time taken to complete this phase |

**Validation Rules**:
- FR-026: Must be valid JSON
- FR-027: Must pass schema validation before use
- Must include phase-specific data (see below)

**Checkpoint Types**: See sections 3.1 - 3.5 below

---

### 3.1 Phase1Checkpoint (Segmentation)

**Purpose**: Stores extracted segments with timestamps.

**Phase-Specific Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `segments` | `List[Segment]` | Yes | Length > 0 | Extracted segments (partial fields) |
| `total_segments` | `int` | Yes | > 0 | Count of segments extracted |
| `sample_rate_fps` | `float` | Yes | > 0 | Frame sampling rate used |

**Segment Fields Present**: `segment_id`, `start_time`, `end_time`, `duration` (no scores yet)

**Example**:
```json
{
  "phase": 1,
  "timestamp": "2025-10-25T14:30:00Z",
  "input_video_path": "/path/to/video.mp4",
  "pipeline_version": "1.0.0",
  "phase_duration_seconds": 45.3,
  "segments": [
    {
      "segment_id": "550e8400-e29b-41d4-a716-446655440000",
      "start_time": 0.0,
      "end_time": 12.0,
      "duration": 12.0
    }
  ],
  "total_segments": 120,
  "sample_rate_fps": 1.0
}
```

---

### 3.2 Phase2Checkpoint (Ranking & Classification)

**Purpose**: Stores segments with quality scores and classifications.

**Phase-Specific Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `segments` | `List[Segment]` | Yes | Length > 0 | Scored segments (full fields) |
| `min_quality_threshold` | `float` | Yes | >= 1.0 | Minimum quality score to proceed |
| `segments_above_threshold` | `int` | Yes | > 0 (else FR-007 error) | Count of segments meeting threshold |
| `score_weights` | `Dict[str, float]` | Yes | Sum = 1.0 | Weights used (motion, scene, composition) |

**Segment Fields Present**: All fields including scores, classifications

**Validation Rules**:
- FR-007: If `segments_above_threshold == 0`, pipeline must fail
- Scores must be in 1-10 range

**Example**:
```json
{
  "phase": 2,
  "timestamp": "2025-10-25T14:32:15Z",
  "input_video_path": "/path/to/video.mp4",
  "pipeline_version": "1.0.0",
  "phase_duration_seconds": 135.7,
  "segments": [
    {
      "segment_id": "550e8400-e29b-41d4-a716-446655440000",
      "start_time": 0.0,
      "end_time": 12.0,
      "duration": 12.0,
      "quality_score": 7.8,
      "motion_score": 8.2,
      "scene_score": 7.5,
      "composition_score": 7.7,
      "classifications": ["high-action", "highlight-candidate"],
      "included": true,
      "manually_edited": false
    }
  ],
  "min_quality_threshold": 7.0,
  "segments_above_threshold": 87,
  "score_weights": {
    "scene": 0.6,
    "motion": 0.25,
    "composition": 0.15
  }
}
```

---

### 3.3 Phase3Checkpoint (Assembly)

**Purpose**: Stores selected segments and ordering for highlight reel.

**Phase-Specific Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `selected_segments` | `List[str]` | Yes | Segment IDs | Ordered list of segment IDs to include |
| `target_duration` | `float` | Yes | > 0 | User-specified target duration |
| `actual_duration` | `float` | Yes | > 0 | Actual duration of selected segments |
| `selection_algorithm` | `str` | Yes | - | Algorithm used ("greedy", "knapsack", etc.) |
| `variety_score` | `float` | No | 0-1 | Measure of temporal distribution |

**Validation Rules**:
- FR-011: Selected segments should be temporally distributed
- FR-012: Selected segments in chronological order
- FR-012: If `actual_duration < target_duration` and source < target, warning issued

**Example**:
```json
{
  "phase": 3,
  "timestamp": "2025-10-25T14:34:45Z",
  "input_video_path": "/path/to/video.mp4",
  "pipeline_version": "1.0.0",
  "phase_duration_seconds": 5.2,
  "selected_segments": [
    "550e8400-e29b-41d4-a716-446655440000",
    "660e8400-e29b-41d4-a716-446655440001"
  ],
  "target_duration": 180.0,
  "actual_duration": 177.5,
  "selection_algorithm": "greedy_variety",
  "variety_score": 0.82
}
```

---

### 3.4 Phase4Checkpoint (Composition)

**Purpose**: Stores composition settings (transitions, overlays, subtitles).

**Phase-Specific Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `transition_type` | `str` | Yes | "cut", "fade", "dissolve" | Transition effect between clips |
| `transition_duration` | `float` | No | > 0 | Duration of transition in seconds |
| `text_overlays` | `List[TextOverlay]` | No | - | Text overlay configurations |
| `subtitle_file` | `str` | No | File exists | Path to subtitle file (SRT) |
| `subtitle_style` | `Dict` | No | - | Subtitle styling options |
| `gps_overlay_enabled` | `bool` | No | - | Whether to render GPS mini-map overlays (default: auto-detect from GPS data) |
| `gps_overlay_config` | `GPSOverlayConfig` | No | - | GPS overlay configuration (position, size, style) |

**TextOverlay** sub-entity:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `segment_id` | `str` | Yes | Valid segment | Segment to apply overlay to |
| `text` | `str` | Yes | Non-empty | Text content |
| `position` | `Tuple[int, int]` | Yes | >= 0 | (x, y) position in pixels |
| `font_size` | `int` | Yes | > 0 | Font size in points |
| `start_offset` | `float` | Yes | >= 0 | Delay after segment start (seconds) |
| `duration` | `float` | Yes | > 0 | Overlay duration (seconds) |

**GPSOverlayConfig** sub-entity:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `map_position` | `str` | No | "top-left", "top-right", "bottom-left", "bottom-right" | Position of mini-map overlay (default: "bottom-right") |
| `map_size` | `Tuple[int, int]` | No | Width, height > 0 | Size of mini-map in pixels (default: 300x200) |
| `map_style` | `str` | No | "street", "satellite", "terrain" | Map tile style (default: "street" for OpenStreetMap) |
| `show_path` | `bool` | No | - | Whether to draw flight path (default: true) |
| `show_position_marker` | `bool` | No | - | Whether to show current position marker (default: true) |
| `show_altitude` | `bool` | No | - | Whether to display altitude text (default: true if elevation data available) |
| `show_location_name` | `bool` | No | - | Whether to display reverse-geocoded location (default: true) |
| `path_color` | `str` | No | Hex color | Flight path line color (default: "#FF0000" red) |
| `marker_color` | `str` | No | Hex color | Current position marker color (default: "#0000FF" blue) |

**Example**:
```json
{
  "phase": 4,
  "timestamp": "2025-10-25T14:36:00Z",
  "input_video_paths": ["/path/to/drone_video_1.mp4", "/path/to/drone_video_2.mp4"],
  "pipeline_version": "1.0.0",
  "phase_duration_seconds": 42.1,
  "transition_type": "cut",
  "transition_duration": 0.0,
  "text_overlays": [
    {
      "segment_id": "550e8400-e29b-41d4-a716-446655440000",
      "text": "Epic Moment",
      "position": [10, 10],
      "font_size": 24,
      "start_offset": 0.5,
      "duration": 2.0
    }
  ],
  "subtitle_file": null,
  "subtitle_style": null,
  "gps_overlay_enabled": true,
  "gps_overlay_config": {
    "map_position": "bottom-right",
    "map_size": [300, 200],
    "map_style": "street",
    "show_path": true,
    "show_position_marker": true,
    "show_altitude": true,
    "show_location_name": true,
    "path_color": "#FF0000",
    "marker_color": "#0000FF"
  }
}
```

---

### 3.5 Phase5Checkpoint (Audio)

**Purpose**: Stores audio mixing and normalization settings.

**Phase-Specific Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `normalize_audio` | `bool` | Yes | - | Whether to normalize audio levels |
| `normalization_target_db` | `float` | No | -30 to 0 | Target loudness (dB) |
| `background_music_file` | `str` | No | File exists | Path to background music |
| `background_music_volume` | `float` | No | 0.0 - 1.0 | Music volume relative to original |
| `fade_music_at_speech` | `bool` | No | - | Reduce music during speech/high audio |
| `output_audio_codec` | `str` | Yes | Valid codec | Audio codec for output ("aac", "mp3") |

**Example**:
```json
{
  "phase": 5,
  "timestamp": "2025-10-25T14:38:30Z",
  "input_video_path": "/path/to/video.mp4",
  "pipeline_version": "1.0.0",
  "phase_duration_seconds": 67.9,
  "normalize_audio": true,
  "normalization_target_db": -16.0,
  "background_music_file": "/path/to/music.mp3",
  "background_music_volume": 0.3,
  "fade_music_at_speech": true,
  "output_audio_codec": "aac"
}
```

---

### 4. PipelineConfig

**Purpose**: User settings controlling pipeline behavior.

**Fields**:

| Field | Type | Required | Validation | Default | Description |
|-------|------|----------|------------|---------|-------------|
| `input_videos` | `List[str]` | Yes | Files exist | - | Paths to one or more input videos |
| `output_directory` | `str` | Yes | Directory exists | `./output` | Output directory for files |
| `target_duration` | `float` | Yes | > 0 | See note | Target highlight duration (seconds) |
| `min_quality_threshold` | `float` | No | 1.0 - 10.0 | 7.0 | Minimum quality score |
| `sample_rate_fps` | `float` | No | > 0 | 1.0 | Frame sampling rate |
| `logging_verbosity` | `str` | No | Valid level | "detailed" | "minimal", "moderate", "detailed", "verbose" |
| `resume_from_phase` | `int` | No | 1-5 | 1 | Phase to resume from (or start from) |
| `checkpoint_directory` | `str` | No | - | `{output}/checkpoints` | Where to save/load checkpoints |

**Default Target Duration** (FR-030, Assumption #10):
- If not specified: `min(300, combined_video_duration * 0.1)` (5 minutes or 10% of combined duration, whichever is shorter)

**Validation Rules**:
- FR-031: `target_duration` must be specified by user or calculated from default
- FR-036: All input videos are processed together as a single pool
- If `resume_from_phase > 1`, corresponding checkpoint must exist

**Example**:
```python
PipelineConfig(
    input_videos=["/path/to/drone_video_1.mp4", "/path/to/drone_video_2.mp4"],
    output_directory="/path/to/output",
    target_duration=180.0,
    min_quality_threshold=7.0,
    sample_rate_fps=1.0,
    logging_verbosity="detailed",
    resume_from_phase=1,
    checkpoint_directory="/path/to/output/checkpoints"
)
```

---

### 5. HighlightReel (Output)

**Purpose**: Final assembled output video with metadata.

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `output_path` | `str` | Yes | `.mp4` extension | Path to output video file |
| `duration_seconds` | `float` | Yes | > 0 | Final video duration |
| `segment_count` | `int` | Yes | > 0 | Number of segments included |
| `source_video_path` | `str` | Yes | - | Original source video path |
| `creation_timestamp` | `datetime` | Yes | - | When reel was created |
| `pipeline_version` | `str` | Yes | SemVer | Pipeline version used |
| `file_size_bytes` | `int` | Yes | > 0 | Output file size |

**Validation Rules**:
- FR-024: Must be MP4 format
- FR-025: Source video must still exist (non-destructive)
- SC-005: Quality comparable to source (no visible artifacts)

**Example**:
```python
HighlightReel(
    output_path="/path/to/output/highlight.mp4",
    duration_seconds=177.5,
    segment_count=15,
    source_video_path="/path/to/video.mp4",
    creation_timestamp=datetime(2025, 10, 25, 14, 40, 0),
    pipeline_version="1.0.0",
    file_size_bytes=104857600
)
```

---

### 6. ProgressReport

**Purpose**: Real-time execution status during pipeline run.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `current_phase` | `int` | Yes | Phase currently executing (1-5) |
| `phase_name` | `str` | Yes | Human-readable phase name |
| `percentage_complete` | `float` | Yes | 0-100 completion percentage |
| `current_operation` | `str` | Yes | Description of current operation |
| `elapsed_seconds` | `float` | Yes | Time elapsed since start |
| `estimated_remaining_seconds` | `float` | No | Estimated time remaining |

**Lifecycle**:
- Created: At pipeline start
- Updated: Continuously during execution
- Disposed: At pipeline completion

**Example**:
```python
ProgressReport(
    current_phase=2,
    phase_name="Ranking & Classification",
    percentage_complete=45.2,
    current_operation="Scoring segment 54/120",
    elapsed_seconds=102.3,
    estimated_remaining_seconds=124.1
)
```

---

### 7. LogFile

**Purpose**: Persistent record of warnings, errors, and diagnostic information.

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `log_path` | `str` | Yes | Path to log file |
| `log_level` | `str` | Yes | "DEBUG", "INFO", "WARNING", "ERROR" |
| `created_at` | `datetime` | Yes | When log file was created |
| `pipeline_run_id` | `str` | Yes | Unique ID for this pipeline run |

**Log Entry Format** (in file):
```
2025-10-25 14:30:15 - autovideo.phases.segmentation - INFO - Starting segmentation phase
2025-10-25 14:30:16 - autovideo.analysis.motion_detector - DEBUG - Processing frame 30
2025-10-25 14:30:45 - autovideo.phases.segmentation - WARNING - Low motion detected in segment 5
2025-10-25 14:32:00 - autovideo.phases.ranking - ERROR - No segments above quality threshold
```

**Validation Rules**:
- FR-033: Log file must be created in output directory
- Log file rotated if size > 100MB

---

## Entity Relationships

### Composition Hierarchy

```
PipelineConfig
├── VideoSource (input)
├── Phase1Checkpoint
│   └── Segment[] (partial: no scores)
├── Phase2Checkpoint
│   └── Segment[] (full: with scores)
├── Phase3Checkpoint
│   └── selected_segments: str[] (references Segment IDs)
├── Phase4Checkpoint
│   └── TextOverlay[] (references Segment IDs)
├── Phase5Checkpoint
│   └── (no nested entities)
└── HighlightReel (output)
```

### Phase Dependencies

```
Phase 1 (Segmentation)
    ↓ (produces Phase1Checkpoint)
Phase 2 (Ranking) [consumes Phase1Checkpoint]
    ↓ (produces Phase2Checkpoint)
Phase 3 (Assembly) [consumes Phase2Checkpoint]
    ↓ (produces Phase3Checkpoint)
Phase 4 (Composition) [consumes Phase3Checkpoint]
    ↓ (produces Phase4Checkpoint)
Phase 5 (Audio) [consumes Phase4Checkpoint]
    ↓ (produces Phase5Checkpoint + HighlightReel)
```

---

## Validation Summary

| Entity | Key Validations | Related Requirements |
|--------|----------------|---------------------|
| VideoSource | MP4 format, ≤4 hours, ≤1080p | FR-023, SC-004 |
| Segment | 5-15 seconds, scores 1-10 | FR-002, FR-005 |
| Phase1Checkpoint | Valid JSON, segments present | FR-003, FR-027 |
| Phase2Checkpoint | Quality threshold met | FR-007, FR-008 |
| Phase3Checkpoint | Chronological order | FR-012 |
| Phase4Checkpoint | Valid transition types | FR-016 |
| Phase5Checkpoint | Valid audio settings | FR-019-023 |
| PipelineConfig | Valid paths, ranges | FR-031, FR-034 |
| HighlightReel | MP4, source preserved | FR-024, FR-025 |

---

## JSON Schema Locations

All checkpoint JSON schemas will be generated in:
- `specs/001-auto-highlight-pipeline/contracts/checkpoint-phase1.json`
- `specs/001-auto-highlight-pipeline/contracts/checkpoint-phase2.json`
- `specs/001-auto-highlight-pipeline/contracts/checkpoint-phase3.json`
- `specs/001-auto-highlight-pipeline/contracts/checkpoint-phase4.json`
- `specs/001-auto-highlight-pipeline/contracts/checkpoint-phase5.json`

**Schema Format**: JSON Schema Draft 7

---

**Data Model Status**: Complete
**Next Step**: Generate JSON Schema contracts
