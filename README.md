# AutoVideoEditor

**Automatic Video Highlight Pipeline** - Transform hours of drone footage into professional highlight reels automatically.

## Overview

AutoVideoEditor is a Python-based automatic video editor that processes multiple MP4 videos into curated highlight reels. Using computer vision and intelligent segment analysis, it automatically identifies the most interesting moments from your footage and assembles them into polished videos with GPS overlays, transitions, and audio mixing.

## Key Features

- **Multi-Video Processing** - Combine multiple drone videos into a single highlight reel
- **Smart Segment Selection** - Analyzes motion, scene changes, and visual composition to identify interesting content
- **GPS Overlays** - Mini-map with flight paths, altitude display, and location names (city/country)
- **5-Phase Pipeline** - Segmentation → Ranking → Assembly → Composition → Audio
- **Manual Override** - JSON checkpoints at each phase allow manual refinement
- **Non-Destructive** - Original videos preserved, all edits via checkpoints

## Current Status

**📋 Specification Phase Complete**

The project is currently in the planning stage using the [SpecKit framework](https://github.com/anthropics/speckit) for specification-driven development.

✅ **Completed:**
- Feature specification with user stories and requirements
- Technical research and design decisions
- Data model with GPS data support
- Implementation architecture
- JSON checkpoint schemas
- Usage documentation

📝 **Next Step:** Task breakdown and implementation

## Quick Example

```bash
# Process multiple drone videos into 3-minute highlight
python -m autovideo \
  --input drone_flight1.mp4 drone_flight2.mp4 drone_flight3.mp4 \
  --duration 180 \
  --output-dir ./output

# For 4K videos, add --resize-to-hd for faster processing
python -m autovideo \
  --input 4k_drone_footage.mp4 \
  --duration 300 \
  --resize-to-hd
```

**Output:**
- `output/highlight.mp4` - Final highlight reel
- `output/checkpoints/` - JSON checkpoints for each phase
- `output/logs/` - Detailed processing logs

## Technology Stack

- **Python 3.11+** - Core language
- **OpenCV** - Video analysis (motion, scene detection, composition)
- **FFmpeg** - Video encoding, assembly, effects, audio mixing
- **OpenStreetMap** - Map tiles for GPS overlays
- **Geocoding API** - Reverse lookup for location names

## Pipeline Phases

1. **Segmentation** - Extract 5-15 second clips from non-repetitive content
2. **Ranking** - Score segments based on motion, scene changes, composition
3. **Assembly** - Select best segments to meet target duration
4. **Composition** - Apply transitions, GPS overlays, text
5. **Audio** - Normalize levels, mix background music

## GPS Overlay Features

When drone videos include GPS-enabled SRT files:
- 📍 Mini-map with OpenStreetMap tiles
- 🛫 Flight path visualization
- 📏 Altitude display
- 🌍 Location names (e.g., "San Francisco, California, USA")

All GPS settings customizable via JSON checkpoints.

## Documentation

Detailed documentation available in [`specs/001-auto-highlight-pipeline/`](specs/001-auto-highlight-pipeline/):

- [**spec.md**](specs/001-auto-highlight-pipeline/spec.md) - Complete feature specification
- [**plan.md**](specs/001-auto-highlight-pipeline/plan.md) - Implementation architecture
- [**research.md**](specs/001-auto-highlight-pipeline/research.md) - Technical decisions
- [**data-model.md**](specs/001-auto-highlight-pipeline/data-model.md) - Entity definitions
- [**quickstart.md**](specs/001-auto-highlight-pipeline/quickstart.md) - Usage guide
- [**contracts/**](specs/001-auto-highlight-pipeline/contracts/) - JSON checkpoint schemas

## Development Workflow

This project uses the **SpecKit** framework for specification-driven development:

1. **Specify** (`/speckit.specify`) - Create feature specification
2. **Clarify** (`/speckit.clarify`) - Resolve ambiguities
3. **Plan** (`/speckit.plan`) - Generate implementation plan
4. **Tasks** (`/speckit.tasks`) - Create task breakdown
5. **Implement** (`/speckit.implement`) - Execute tasks

See [CLAUDE.md](CLAUDE.md) for complete workflow documentation.

## Project Structure

```
AutoVideoEditor/
├── specs/001-auto-highlight-pipeline/  # Feature specification & planning
│   ├── spec.md                         # Feature specification
│   ├── plan.md                         # Implementation plan
│   ├── research.md                     # Technical decisions
│   ├── data-model.md                   # Entity definitions
│   ├── quickstart.md                   # Usage guide
│   └── contracts/                      # JSON schemas (5 phases)
├── .claude/                            # SpecKit workflow commands
├── .specify/                           # Scripts and templates
└── CLAUDE.md                           # Development workflow guide
```

## Quality Scoring Algorithm

Segments are scored 1-10 based on visual analysis:

- **Motion** (40%) - Frame differencing to detect dynamic content
- **Scene Changes** (30%) - Histogram comparison for cuts/transitions
- **Composition** (30%) - Edge density and color diversity

Audio is **not** used in scoring to support silent drone footage.

## Use Cases

- **Drone Videography** - Automatically create highlight reels from long flights
- **Action Cameras** - Extract exciting moments from hours of footage
- **Travel Videos** - Combine multiple location videos with GPS context
- **Content Creation** - Rapid video editing for social media

## Contributing

This project is in early development. Contributions welcome once the implementation phase begins!

## License

[License to be determined]

## Credits

Built with [Claude Code](https://claude.com/claude-code) using specification-driven development.

---

**Status:** 📋 Specification Complete | 🚧 Implementation Pending
