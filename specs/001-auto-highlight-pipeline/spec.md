# Feature Specification: Automatic Video Highlight Pipeline

**Feature Branch**: `001-auto-highlight-pipeline`
**Created**: 2025-10-25
**Status**: Draft
**Input**: User description: "Build a Python-based automatic video editor that processes one or more long MP4 videos into curated highlight reels. The system is designed as a 5-phase pipeline with JSON checkpoints at each phase, allowing manual overrides and non-destructive editing."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Basic Highlight Reel Generation (Priority: P1)

A content creator has multiple drone video files totaling 2 hours of footage and wants to create a 3-minute highlight reel automatically from all videos, without manually scrubbing through each file.

**Why this priority**: This is the core MVP functionality that delivers immediate value - automated extraction of interesting segments from multiple long-form video files and combining them into a single highlight reel.

**Independent Test**: Can be fully tested by providing multiple MP4 video files and receiving a shorter highlight reel as output. Success is validated by confirming the output video exists, plays correctly, contains segments from multiple source videos, and is shorter than the combined input duration.

**Acceptance Scenarios**:

1. **Given** multiple MP4 video files totaling 2 hours, **When** the user runs the pipeline with target duration of 3 minutes, **Then** the system produces a 3-minute highlight video containing the most interesting segments from across all input videos
2. **Given** multiple videos with varying quality (some with repetitive content like static sky shots or slow pans), **When** the segmentation phase runs, **Then** boring segments are excluded and only interesting moments from all videos are considered for the final highlight reel
3. **Given** a processed multi-video highlight, **When** the user views the output, **Then** all selected clips are 5-15 seconds long and represent distinct moments from different source videos, seamlessly assembled together

---

### User Story 2 - Manual Override and Refinement (Priority: P2)

A user has generated an initial highlight reel but wants to manually adjust which segments are included, exclude certain clips, or force-include specific moments the algorithm missed.

**Why this priority**: Automated selection won't always be perfect. Manual override capability ensures users maintain creative control and can refine results to match their vision.

**Independent Test**: Can be tested by generating a highlight reel (using Story 1), then modifying the JSON checkpoint files to change segment selection, and re-running the pipeline to verify the changes are respected.

**Acceptance Scenarios**:

1. **Given** JSON checkpoint files from a completed pipeline run, **When** the user manually edits segment scores or classifications, **Then** re-running the pipeline uses the modified values instead of recalculating
2. **Given** a segment marked for exclusion in the checkpoint, **When** the assembly phase runs, **Then** that segment does not appear in the final video regardless of its quality score
3. **Given** a segment with a manually boosted quality score, **When** the ranking phase is bypassed, **Then** the assembly phase prioritizes this segment appropriately

---

### User Story 3 - Enhanced Composition with Effects (Priority: P3)

A user wants their drone highlight reel to include professional touches like smooth transitions between clips, GPS-enabled mini-map overlays showing flight paths and locations, altitude displays, and text overlays announcing each segment.

**Why this priority**: This enhances production quality but is not essential for basic functionality. Many users will be satisfied with just clip selection and assembly. GPS overlays are particularly valuable for drone footage to show where the video was captured.

**Independent Test**: Can be tested by processing drone videos with GPS-enabled SRT files through all phases and verifying that the output includes visible transitions, mini-map overlays with location data, and text overlays that were not present in the source video.

**Acceptance Scenarios**:

1. **Given** multiple segments in the assembly, **When** the composition phase runs, **Then** smooth transitions (fade, dissolve, or cut) appear between each clip
2. **Given** drone video segments with GPS SRT files, **When** the composition phase runs, **Then** a mini-map overlay appears showing the drone's flight path and current position using OpenStreetMap style
3. **Given** segments with GPS elevation data, **When** the composition phase runs, **Then** altitude information is displayed on the video overlay
4. **Given** segments with GPS coordinates, **When** the composition phase runs with internet connectivity, **Then** reverse-geocoded location names (city/country) are displayed on the video
5. **Given** configuration for text overlays, **When** the composition phase runs, **Then** each segment displays customizable text (e.g., timestamps, descriptions) at specified positions

---

### User Story 4 - Audio Enhancement and Mixing (Priority: P4)

A user wants to add background music, normalize audio levels across clips, and optionally add narration or sound effects to create a polished final product.

**Why this priority**: Audio enhancement is important for professional content but can be done in post-production using other tools. It's a nice-to-have rather than essential.

**Independent Test**: Can be tested by running the audio phase with background music files and verifying that the output video includes the music track, has balanced audio levels, and preserves original audio where appropriate.

**Acceptance Scenarios**:

1. **Given** a highlight reel with varying audio levels across clips, **When** the audio mixing phase runs, **Then** all segments have normalized volume levels for consistent listening experience
2. **Given** a background music file, **When** the audio phase runs, **Then** the music is mixed under the original audio at an appropriate volume that doesn't overpower speech or important sounds
3. **Given** multiple audio sources (original, music, effects), **When** the final video is rendered, **Then** all audio tracks are synchronized and properly mixed with smooth transitions

---

### User Story 5 - Incremental Pipeline Execution (Priority: P5)

A user wants to run only specific phases of the pipeline (e.g., re-run composition with different effects without re-analyzing segments) or resume from a checkpoint after making manual adjustments.

**Why this priority**: This improves workflow efficiency for power users but isn't necessary for basic usage. Most users will run the full pipeline.

**Independent Test**: Can be tested by running the full pipeline once, then running individual phases with checkpoint files as input and verifying the output matches expectations without re-executing earlier phases.

**Acceptance Scenarios**:

1. **Given** completed checkpoint files from Phase 2, **When** the user runs only Phase 3 (Assembly), **Then** the system uses existing segment rankings without re-analyzing video content
2. **Given** a failed pipeline run that stopped at Phase 3, **When** the user fixes the issue and resumes, **Then** the pipeline continues from Phase 3 without repeating Phases 1-2
3. **Given** modified composition settings, **When** the user re-runs Phase 4 only, **Then** a new video is generated with updated effects while preserving segment selection from earlier phases

---

### Edge Cases

- **Corrupted/Invalid Files**: System validates MP4 headers at startup, skips invalid files with warning, processes remaining valid files (see FR-046)
- How does the system handle very large video files (>10GB) or very long durations (>4 hours)?
- What happens when insufficient disk space exists for output files?
- How does the system handle videos with multiple audio tracks or no audio?
- What happens when JSON checkpoint files are manually corrupted or contain invalid data?
- How does the system handle edge cases in segment boundaries (e.g., segments shorter than 5 seconds)?

## Clarifications

### Session 2025-10-25

- Q: How should the system calculate "quality scores" (1-10) for video segments in Phase 2? → A: Exclude audio in quality score, only motion, scene changes, composition
- Q: What should the system do when no "interesting" segments are detected (e.g., all segments score below a threshold)? → A: Fail with error message requiring manual intervention
- Q: Which Python video processing library should be used as the primary framework for video manipulation? → A: OpenCV + FFmpeg
- Q: What level of logging and progress reporting should the system provide during pipeline execution? → A: Default detailed progress with phase completion percentages, current operation descriptions, and warning/error logs saved to files, but allow changing the level at command line
- Q: How should the system handle videos shorter than the target highlight duration? → A: Use the entire video as the highlight reel and warn the user
- Q: What formula should combine motion, scene changes, and visual composition metrics into the final quality score (1-10)? → A: Scene change 60%, motion 25%, composition 15%
- Q: How should the system handle mid-phase failures (e.g., FFmpeg crash during assembly, out of memory during analysis)? → A: Halt pipeline, save checkpoint, log error details, preserve partial work
- Q: When processing multiple input videos, how should segments be ordered in the final highlight reel? → A: Merge chronologically by original timestamp across all videos
- Q: What minimum quality score threshold (1-10 scale) should determine "interesting" segments eligible for inclusion in the highlight reel? → A: Minimum quality score of 7/10
- Q: How should the system handle corrupted or invalid MP4 files at pipeline startup? → A: Validate headers, skip invalid files with warning, process valid ones

## Requirements *(mandatory)*

### Functional Requirements

**Phase 1: Segmentation**
- **FR-001**: System MUST analyze input MP4 video and detect segments with repetitive or static content
- **FR-002**: System MUST extract clips between 5-15 seconds in length from non-repetitive portions of the video
- **FR-003**: System MUST save segmentation results (timestamps, durations, metadata) to a JSON checkpoint file
- **FR-004**: System MUST support loading existing Phase 1 checkpoint to skip re-analysis

**Phase 2: Ranking & Classification**
- **FR-005**: System MUST assign quality scores (1-10 scale) to each extracted segment using weighted formula: 60% scene changes + 25% motion analysis + 15% visual composition (audio excluded from scoring)
- **FR-006**: System MUST classify each segment with descriptive tags or categories
- **FR-007**: System MUST fail with a clear error message if no segments meet minimum quality threshold of 7/10 for interesting content
- **FR-008**: System MUST save ranking and classification results to a JSON checkpoint file
- **FR-009**: System MUST allow manual modification of scores and classifications in the checkpoint file
- **FR-010**: System MUST support loading existing Phase 2 checkpoint to skip re-ranking

**Phase 3: Assembly**
- **FR-011**: System MUST select segments to meet a target duration specified by the user
- **FR-012**: System MUST use the entire video as the highlight reel when source video is shorter than target duration, with a warning message to the user
- **FR-013**: System MUST optimize segment selection for both quality scores (minimum 7/10) and variety (avoid selecting all clips from one section)
- **FR-014**: System MUST assemble selected segments in chronological order based on original timestamps; when processing multiple videos, segments are merged chronologically across all source videos by timestamp
- **FR-015**: System MUST save assembly decisions (selected segments, ordering) to a JSON checkpoint file
- **FR-016**: System MUST support loading existing Phase 3 checkpoint to use pre-determined segment selection

**Phase 4: Composition**
- **FR-017**: System MUST apply cut transitions between assembled segments (additional transition types may be added in future phases)
- **FR-018**: System MUST support text overlay placement on clips with customizable content, position, and timing
- **FR-019**: System MUST generate or accept subtitle files and overlay them on the video
- **FR-020**: System MUST render mini-map overlay with OpenStreetMap style when GPS data is available for a segment
- **FR-021**: System MUST display flight path and current position marker on mini-map overlay
- **FR-022**: System MUST display altitude information when GPS elevation data is available
- **FR-023**: System MUST perform reverse geocoding to display location name (city/country) on video overlay
- **FR-024**: System MUST save composition settings including GPS overlay configuration to a JSON checkpoint file

**Phase 5: Audio**
- **FR-025**: System MUST normalize audio levels across all segments for consistent volume
- **FR-026**: System MUST support mixing background music into the final video
- **FR-027**: System MUST balance audio tracks (original audio, music, effects) to prevent overpowering
- **FR-028**: System MUST save audio mixing settings to a JSON checkpoint file

**GPS & Location Data** (Optional Feature)
- **FR-037**: System SHOULD parse GPS coordinates and elevation data from SRT subtitle files when available during Phase 1
- **FR-038**: System MUST allow manual GPS data entry or modification in checkpoint JSON files
- **FR-039**: System MUST support GPS data format: array of (latitude, longitude, elevation, timestamp) tuples

**General Requirements**
- **FR-029**: System MUST process one or more MP4 video files as input
- **FR-030**: System MUST produce MP4 video files as output
- **FR-046**: System MUST validate MP4 file headers at pipeline startup, skip corrupted or invalid files with warning message logged, and proceed with processing valid files only
- **FR-031**: System MUST preserve original video files (non-destructive editing)
- **FR-032**: System MUST create JSON checkpoint files after each phase for inspection and manual override
- **FR-033**: System MUST validate JSON checkpoint files before using them to detect corruption
- **FR-034**: System MUST provide clear error messages when processing fails
- **FR-035**: System MUST support running the full pipeline end-to-end or individual phases
- **FR-040**: System MUST allow specifying target duration for the final highlight reel
- **FR-041**: System MUST process segments from multiple input videos together, treating all videos as a single pool of content for highlight selection
- **FR-042**: System MUST display detailed progress reporting by default, including phase completion percentages and current operation descriptions
- **FR-043**: System MUST save warning and error logs to files for debugging and troubleshooting
- **FR-044**: System MUST accept command-line arguments to adjust logging verbosity level (minimal, moderate, detailed, verbose)
- **FR-045**: System MUST halt pipeline execution on mid-phase failures, save partial checkpoint with completed work, log error details to file, and preserve all intermediate files for recovery

### Key Entities

- **Video Source**: One or more input MP4 files to be processed, each including file path, duration, resolution, frame rate, audio properties, file creation/modification timestamp for chronological ordering, and optional SRT file path for GPS data
- **Segment**: An extracted clip from a source video, including source video identifier, start timestamp, end timestamp, duration, quality score, classifications/tags, inclusion status, and optional GPS coordinates/elevation data
- **GPS Data**: Optional location information for a segment, including coordinate path (latitude/longitude pairs), elevation values, and reverse-geocoded location name (city/country)
- **Checkpoint**: A JSON file persisting pipeline state, including phase number, timestamp, input parameters, GPS data, and phase-specific output data
- **Highlight Reel**: The final assembled output video, including selected segments, applied effects, composition settings, audio mix configuration, and GPS overlays where available
- **Pipeline Configuration**: User settings controlling pipeline behavior, including target duration, minimum quality threshold (default 7/10), transition preferences, audio mixing levels, GPS overlay settings, and logging verbosity
- **Progress Report**: Real-time execution status including current phase, completion percentage, current operation, and elapsed time
- **Log File**: Persistent record of warnings, errors, and diagnostic information saved to disk for troubleshooting

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can process multiple videos totaling 2 hours and receive a 3-minute highlight reel in under 15 minutes of processing time
- **SC-002**: At least 80% of selected segments in the highlight reel are subjectively rated as "interesting" by users
- **SC-003**: Users can successfully modify JSON checkpoint files and re-run the pipeline without errors in 100% of valid modification scenarios
- **SC-004**: The system handles multiple videos up to 4 hours combined duration and 1080p resolution without crashing or producing errors
- **SC-005**: Generated highlight reels maintain video quality comparable to the source (no visible compression artifacts or quality degradation)
- **SC-006**: Users can run individual pipeline phases in under 2 minutes for typical video processing tasks
- **SC-007**: The system correctly excludes repetitive/boring content (e.g., static sky shots, slow pans, static frames) in 90% of test cases

## Assumptions

1. **Video Format**: Input videos are assumed to be standard MP4 files with H.264 video codec and AAC audio codec (most common format for drone cameras and user-generated content)
2. **Content Type**: The system is optimized for content with variation (e.g., drone footage, vlogs, action cameras) rather than completely static footage
3. **Multiple Inputs**: The system can process one or more video files in a single pipeline run, treating all videos as a unified content pool
4. **Storage**: Users have sufficient disk space for both source videos and output files (approximately 2x combined source video size for working files)
5. **Processing Power**: Users have modern computers capable of video processing (multi-core CPU recommended but not required)
6. **User Skill Level**: Users can run command-line tools or a simple GUI interface and can edit JSON files with a text editor
7. **Audio Presence**: Input videos may or may not contain audio tracks; silent videos will process normally since quality scoring is based solely on visual analysis
8. **Language**: Subtitle generation (if implemented) assumes English audio content unless otherwise specified
9. **Segment Identification**: "Interesting" content is detected using heuristics based on motion analysis, scene changes, and visual composition
10. **Default Target Duration**: If not specified, the system defaults to a 5-minute highlight reel or 10% of combined source duration, whichever is shorter
11. **Transition Style**: Default transition between clips is a simple cut unless user specifies otherwise

## Dependencies

- **OpenCV**: Required for video frame analysis, motion detection, scene change detection, and visual composition analysis
- **FFmpeg**: Required for video encoding/decoding, format conversion, audio mixing, and final video assembly
- **Python Standard Library**: JSON file handling, file I/O operations, SRT file parsing, and general utilities
- **Mapping Libraries** (Optional for GPS overlays):
  - **Static map generation**: For rendering OpenStreetMap tiles as mini-map overlays
  - **Geocoding service**: For reverse-geocoding GPS coordinates to location names (requires internet connectivity during Phase 4)
  - **GPS path rendering**: For drawing flight paths on map tiles
- **Temporary Storage**: Disk space for intermediate processing files, checkpoint data, and cached map tiles
- **Internet Connectivity** (Optional): Required during Phase 4 composition if using reverse geocoding for location names

## Out of Scope

The following are explicitly not included in this feature:

- Real-time video processing or streaming
- Support for video formats other than MP4 (e.g., AVI, MOV, MKV)
- Advanced color grading or video filters
- Automatic generation of thumbnails or preview images
- Social media upload or publishing functionality
- Multi-track video editing (picture-in-picture, split screens)
- Live video input from cameras or capture devices
- Collaborative editing or cloud-based processing
- Mobile device support (initially desktop/server only)
- Video compression or format conversion beyond output requirements
