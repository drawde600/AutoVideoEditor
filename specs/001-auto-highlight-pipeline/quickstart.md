# Quickstart Guide: Automatic Video Highlight Pipeline

**Feature**: 001-auto-highlight-pipeline
**Date**: 2025-10-25
**Audience**: End users and developers

---

## Prerequisites

### System Requirements
- Python 3.11 or higher
- FFmpeg installed and available in PATH
- Minimum 4GB RAM (8GB recommended for 1080p videos)
- Disk space: ~2x source video size for working files

### Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify FFmpeg installation**:
   ```bash
   ffmpeg -version
   ```
   If not installed, download from: https://ffmpeg.org/download.html

---

## Usage Scenarios

### 1. Basic: Full Pipeline Execution

**Scenario**: Process multiple drone videos totaling 2 hours into a 3-minute highlight reel automatically.

**Command**:
```bash
python src/main.py \
  --input /path/to/drone_video_1.mp4 /path/to/drone_video_2.mp4 /path/to/drone_video_3.mp4 \
  --output ./output \
  --duration 180
```

**Parameters**:
- `--input`: Path(s) to one or more input MP4 video files (space-separated)
- `--output`: Output directory for results (default: `./output`)
- `--duration`: Target highlight duration in seconds (default: auto-calculated from combined duration)

**Output Files**:
```
output/
├── videos/
│   └── combined_highlight.mp4       # Final highlight reel from all input videos
├── checkpoints/
│   ├── phase1_segmentation.json     # Extracted segments from all videos
│   ├── phase2_ranking.json          # Scored segments from all videos
│   ├── phase3_assembly.json         # Selected segments across all videos
│   ├── phase4_composition.json      # Composition settings
│   └── phase5_audio.json            # Audio settings
└── logs/
    └── pipeline_<timestamp>.log     # Detailed execution log
```

**Expected Runtime**: ~10-15 minutes for combined 2-hour 1080p videos (per SC-001)

**Console Output Example**:
```
[  1.5%] Processing video 1/3: drone_video_1.mp4 | Elapsed: 8.2s
[  2.5%] Extracting frames from video 1 | Elapsed: 15.2s | Remaining: ~595s
[  5.0%] Processing video 2/3: drone_video_2.mp4 | Elapsed: 30.1s
[ 10.0%] Processing video 3/3: drone_video_3.mp4 | Elapsed: 60.3s
[ 15.0%] Phase 1: Segmentation complete (120 segments from 3 videos) | Elapsed: 90.3s
[ 18.3%] Scoring segment 15/120 | Elapsed: 110.1s | Remaining: ~490s
[ 35.0%] Phase 2: Ranking complete (87 segments above threshold) | Elapsed: 210.5s
[ 38.0%] Selecting segments for target duration 180s across all videos | Elapsed: 228.3s
[ 40.0%] Phase 3: Assembly complete (15 segments selected, 177.5s total) | Elapsed: 240.1s
[100.0%] Pipeline complete! | Elapsed: 600.2s
```

---

### 2. Manual Override: Edit Checkpoint and Resume

**Scenario**: Generate initial highlight, then manually adjust segment selection by editing JSON checkpoint.

**Step 1**: Run full pipeline once:
```bash
python src/main.py --input video.mp4 --output ./output --duration 180
```

**Step 2**: Edit checkpoint file to customize segments:
```bash
# Open checkpoint in text editor
nano ./output/checkpoints/phase2_ranking.json
```

**Example Edit**: Boost quality score for a specific segment:
```json
{
  "segment_id": "550e8400-e29b-41d4-a716-446655440000",
  "start_time": 125.0,
  "end_time": 137.5,
  "duration": 12.5,
  "quality_score": 9.5,  // ← Changed from 7.8 to 9.5
  "manually_edited": true // ← Set to true
}
```

Or exclude a segment entirely:
```json
{
  "segment_id": "660e8400-e29b-41d4-a716-446655440001",
  "included": false  // ← Changed from true to false
}
```

**Step 3**: Resume pipeline from Phase 3 (assembly):
```bash
python src/main.py \
  --input video.mp4 \
  --output ./output \
  --duration 180 \
  --resume-from 3
```

**Result**: Pipeline uses modified scores/inclusions from Phase 2 checkpoint instead of recalculating.

---

### 3. Individual Phase: Run Single Phase Only

**Scenario**: Re-run composition phase with different transition effects without re-analyzing video.

**Prerequisites**: Must have completed all previous phases (checkpoints exist).

**Command**:
```bash
python src/main.py \
  --input video.mp4 \
  --output ./output \
  --phase 4
```

**Before running**: Optionally edit `phase4_composition.json` to change settings:
```json
{
  "transition_type": "fade",  // ← Changed from "cut" to "fade"
  "transition_duration": 0.5  // ← Added fade duration
}
```

**Result**: New video generated with updated transitions, using existing segment selection from Phase 3.

**Supported Phase Numbers**:
- `1`: Segmentation
- `2`: Ranking & Classification
- `3`: Assembly
- `4`: Composition
- `5`: Audio

---

### 4. Logging Levels: Adjust Verbosity

**Scenario**: Reduce console output for automated processing, or increase for debugging.

**Minimal** (errors only):
```bash
python src/main.py --input video.mp4 --verbosity minimal
```

**Moderate** (warnings + errors):
```bash
python src/main.py --input video.mp4 --verbosity moderate
```

**Detailed** (default - progress + warnings + errors):
```bash
python src/main.py --input video.mp4 --verbosity detailed
```

**Verbose** (debug output):
```bash
python src/main.py --input video.mp4 --verbosity verbose
```

**Log Files**: All verbosity levels write full debug logs to `output/logs/` (FR-033).

---

## Advanced Usage

### Custom Quality Threshold

**Scenario**: Increase quality bar to only include highest-quality segments.

```bash
python src/main.py \
  --input video.mp4 \
  --duration 180 \
  --min-quality 6.0  # Default is 3.0
```

**Result**: Only segments with quality score ≥ 6.0 are considered. If none meet threshold, pipeline fails per FR-007.

---

### Custom Frame Sampling Rate

**Scenario**: Speed up processing by analyzing fewer frames (lower accuracy) or improve accuracy by analyzing more frames (slower).

```bash
# Faster: Analyze 1 frame every 2 seconds
python src/main.py --input video.mp4 --sample-rate 0.5

# Default: Analyze 1 frame per second
python src/main.py --input video.mp4 --sample-rate 1.0

# Slower, more accurate: Analyze 2 frames per second
python src/main.py --input video.mp4 --sample-rate 2.0
```

---

### Auto-Calculate Target Duration

**Scenario**: Let pipeline determine optimal highlight duration based on video length.

```bash
python src/main.py --input video.mp4
# No --duration specified, defaults to min(300s, video_duration * 0.1)
```

**Examples**:
- 30-minute video → 180s (3 minutes) highlight
- 5-hour video → 300s (5 minutes) highlight (capped)

---

## Checkpoint Manual Editing Guide

### Checkpoint File Locations

All checkpoints stored in: `output/checkpoints/`

### Common Edits

#### 1. Exclude a Segment
Edit `phase2_ranking.json`:
```json
{
  "segment_id": "abc123...",
  "included": false  // ← Set to false
}
```

#### 2. Force-Include a Segment
Edit `phase2_ranking.json`:
```json
{
  "segment_id": "def456...",
  "quality_score": 10.0,  // ← Boost score
  "included": true,
  "manually_edited": true
}
```

#### 3. Change Segment Order
Edit `phase3_assembly.json`:
```json
{
  "selected_segments": [
    "segment-id-3",  // ← Reorder these IDs
    "segment-id-1",
    "segment-id-2"
  ]
}
```

#### 4. Add Text Overlay
Edit `phase4_composition.json`:
```json
{
  "text_overlays": [
    {
      "segment_id": "abc123...",
      "text": "Epic Moment!",
      "position": [10, 10],
      "font_size": 48,
      "start_offset": 0.5,
      "duration": 2.0,
      "color": "#FFFFFF"
    }
  ]
}
```

#### 5. Add Background Music
Edit `phase5_audio.json`:
```json
{
  "background_music_file": "/path/to/music.mp3",
  "background_music_volume": 0.3,  // 30% of original audio level
  "fade_music_at_speech": true
}
```

### Checkpoint Validation

**Before resuming**, validate checkpoint syntax:
```bash
python src/main.py --validate-checkpoint output/checkpoints/phase2_ranking.json
```

**Common Errors**:
- Missing required field → Pipeline shows: `ERROR: Missing field 'quality_score' in segment`
- Invalid value → Pipeline shows: `ERROR: quality_score must be 1.0-10.0, got 15.0`
- Corrupted JSON → Pipeline shows: `ERROR: Invalid JSON syntax at line 45`

---

## Troubleshooting

### Error: "FFmpeg not found"
**Cause**: FFmpeg not installed or not in PATH.
**Fix**: Install FFmpeg and ensure `ffmpeg -version` works in terminal.

### Error: "No segments above quality threshold"
**Cause**: Video content too static/boring (all segments scored below 3.0).
**Fix**:
1. Lower threshold: `--min-quality 2.0`
2. Or manually edit `phase1_segmentation.json` to adjust segment boundaries

### Error: "Video duration shorter than target"
**Cause**: Source video (e.g., 60s) shorter than target (e.g., 180s).
**Result**: Per FR-012, full video used as highlight with warning.

### Warning: "Insufficient disk space"
**Cause**: Less than 2x source video size available.
**Fix**: Free up disk space or change output directory.

### Slow Processing
**Cause**: High-resolution video or low sampling rate.
**Fixes**:
- Increase sampling rate: `--sample-rate 0.5` (analyze 1 frame per 2 seconds)
- Reduce resolution: Pre-process video to 720p before running pipeline

---

## CLI Reference

### Full Command Syntax

```bash
python src/main.py [OPTIONS]
```

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--input` | `str` | Required | Path to input MP4 video |
| `--output` | `str` | `./output` | Output directory |
| `--duration` | `float` | Auto | Target highlight duration (seconds) |
| `--min-quality` | `float` | `3.0` | Minimum quality threshold (1.0-10.0) |
| `--sample-rate` | `float` | `1.0` | Frame sampling rate (fps) |
| `--verbosity` | `str` | `detailed` | `minimal`, `moderate`, `detailed`, `verbose` |
| `--resume-from` | `int` | `1` | Phase to resume from (1-5) |
| `--phase` | `int` | None | Run single phase only (1-5) |
| `--validate-checkpoint` | `str` | None | Validate checkpoint file and exit |
| `--version` | - | - | Show pipeline version |
| `--help` | - | - | Show help message |

---

## Example Workflows

### Workflow 1: Gaming Stream Highlights

```bash
# 1. Generate initial highlights
python src/main.py --input stream.mp4 --duration 300

# 2. Review output/checkpoints/phase2_ranking.json
# 3. Manually boost scores for clutch moments
# 4. Re-run from assembly phase
python src/main.py --input stream.mp4 --resume-from 3
```

### Workflow 2: Vlog with Custom Overlays

```bash
# 1. Run full pipeline
python src/main.py --input vlog.mp4 --duration 120

# 2. Edit output/checkpoints/phase4_composition.json
#    Add text overlays for segment titles
# 3. Re-run composition phase only
python src/main.py --input vlog.mp4 --phase 4
```

### Workflow 3: Presentation Recording

```bash
# 1. Extract highlights with higher quality threshold
python src/main.py \
  --input presentation.mp4 \
  --duration 600 \
  --min-quality 5.0 \
  --sample-rate 2.0  # More accurate analysis

# 2. Add background music in Phase 5
#    Edit output/checkpoints/phase5_audio.json
# 3. Re-run audio phase
python src/main.py --input presentation.mp4 --phase 5
```

---

## Next Steps

- **For development**: See `plan.md` for architecture details
- **For testing**: See `tests/` directory for unit and integration tests
- **For troubleshooting**: Check `output/logs/pipeline_*.log` for detailed execution logs
- **For customization**: Modify checkpoint JSON files between phases

---

**Quickstart Status**: Complete
**Last Updated**: 2025-10-25
