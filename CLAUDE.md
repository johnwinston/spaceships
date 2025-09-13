# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automons is a Conway's Game of Life spaceship discovery and trading card generation system. It consists of a pipeline that:
1. Uses ntzfind to discover cellular automata spaceships with custom rules
2. Converts patterns between formats (Life 1.05 → RLE → APGcode)
3. Generates animated GIFs and QR codes for discovered patterns
4. Creates collectible trading cards with rarity tiers based on period

## Key Commands

### Main Pipeline Commands
```bash
# Run full pipeline (search + convert + combine)
python main.py all <period> <iterations> [--no-clear]

# Find spaceships only (without clearing existing files)
python main.py auto-ntzfind <period> <iterations> [--no-clear]

# Convert existing RLEs to APGcode/GIFs/QRs
python main.py rle2apgcode <period>

# Generate trading cards from existing patterns
python main.py combine <period>

# Interactive pattern selection UI
python main.py select <period>

# Clear generated files for a period
python main.py clear-files <period>
```

### Docker Pipeline (Apple Silicon)
```bash
# Default: convert RLEs for period 4
bash run_docker_pipeline.sh

# Find spaceships then convert for period 6
bash run_docker_pipeline.sh auto-ntzfind 6 12

# Full pipeline for period 4, finding 12 ships
bash run_docker_pipeline.sh all 4 12 --no-clear
```

### Dependencies Installation
```bash
pip install -r requirements.txt
```

## Architecture

### Core Components

**main.py**: CLI entry point with argparse-based command routing to pipeline stages

**src/auto_ntzfind.py**: 
- Generates random cellular automaton rules (B/S notation)
- Spawns ntzfind subprocess to search for spaceships
- Validates results (length 13-18 lines) and saves as Life 1.05 format

**src/automons.py**: 
- Golly script that converts Life 1.05 files to RLE format
- Auto-detects period directories and processes all .lif files

**src/rle2apgcode.py**:
- Uses lifelib to load CA rules and convert RLE patterns to APGcode
- Generates animated GIFs with random colors
- Creates QR codes linking to Catagolue database
- Outputs patterns.json metadata

**src/cleanup.py**:
- File management for Golly directories
- Interactive Tkinter GUI for pattern curation
- Deletes unwanted GIFs/QRs based on user selection

**src/combine.py**:
- Trading card generation system
- Rarity tiers: period 4=common, 5=uncommon, 6=rare, 7+=legendary
- Merges patterns with card templates and generates print sheets

### Directory Structure

```
golly/Scripts/Python/
├── ntzfind_patterns/<period>/  # Life 1.05 files from ntzfind
└── rles/<period>/              # RLE files converted by Golly

./
├── gifs/<period>/              # Animated pattern GIFs
├── qrs/<period>/               # QR codes linking to Catagolue
├── data/<period>/patterns.json # Pattern metadata
├── card_fronts/<period>/       # Individual card fronts
├── card_backs/<period>/        # Individual card backs
└── card_backgrounds/<rarity>/  # Final print sheets
```

### Dependencies

**External Tools**:
- ntzfind binary (submodules/ntzfind/) for spaceship search
- Golly application for pattern format conversion

**Python Libraries**:
- lifelib: Cellular automaton rule loading and APGcode generation
- PIL/Pillow: Image processing for cards and GIFs
- qrcode: QR code generation
- tkinter: Pattern selection GUI
- numpy: ntzfind parameter generation

### Environment Variables

**GOLLY_DIR**: Path to local Golly installation (defaults to macOS path)

## Development Notes

- The system expects specific Golly directory structure for file I/O
- Pattern validation filters spaceships by generation count (13-18 lines)
- Trading card rarity is hardcoded by period number
- Docker setup forces x86_64 architecture for ntzfind compatibility
- lifelib shared objects are cleaned up after each pattern to prevent conflicts