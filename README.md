# Conway's Game of Life Spaceship Trading Cards

A Python tool that discovers spaceships in Conway's Game of Life and generates beautiful trading cards featuring the patterns, complete with QR codes linking to online pattern databases.

## Features

- **Spaceship Discovery**: Uses ntzfind to automatically search for new spaceships in Conway's Game of Life
- **Pattern Analysis**: Converts patterns to APG codes for cataloging and identification
- **QR Code Generation**: Creates QR codes linking to online pattern databases
- **Trading Card Creation**: Generates beautiful trading card-style images featuring the discovered patterns
- **Batch Processing**: Processes multiple patterns efficiently with automated workflows

## Prerequisites

- Python 3.7+
- [Golly](http://golly.sourceforge.net/) (for pattern visualization and manipulation)
- Git (for submodule management)

## Installation

1. **Clone the repository with submodules:**
   ```bash
   git clone --recursive https://github.com/your-username/your-repo-name.git
   cd your-repo-name
   ```

2. **If you've already cloned without submodules, initialize them:**
   ```bash
   git submodule update --init --recursive
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Compile ntzfind (required for spaceship discovery):**
   ```bash
   cd submodules/ntzfind
   make
   cd ../..
   ```

## Quick Start

Run the interactive main script:

```bash
python main.py
```

The script will guide you through four main operations:

1. **Auto-ntzfind**: Search for new spaceships with specified period
2. **RLE to APG**: Convert pattern files to APG codes and generate QR codes  
3. **Cleanup**: Review and select patterns to keep
4. **Combine**: Generate trading cards from selected patterns

## Project Structure

```
├── main.py                 # Interactive main script
├── src/                    # Core modules
│   ├── auto_ntzfind.py    # Spaceship discovery using ntzfind
│   ├── rle2apgcode.py     # Pattern conversion and QR generation
│   ├── cleanup.py         # Pattern review and selection
│   ├── combine.py         # Trading card generation
│   └── automons.py        # Golly automation utilities
├── submodules/            # External dependencies
│   ├── ntzfind/          # Spaceship search tool
│   └── lifelib/          # Pattern library and utilities
├── template.pdf           # Trading card template
└── requirements.txt       # Python dependencies
```

## Workflow

### 1. Discovering Spaceships

The auto-ntzfind module searches for spaceships with a given period:

```python
# Searches for 10 spaceships with period 4
AUTO_NTZFIND(iterations=10, period=4).run()
```

### 2. Processing Patterns

Convert discovered patterns to standardized formats:

```python
# Converts RLE files to APG codes and generates QR codes
RLE2APGCODE(lifelib, period=4).run()
```

### 3. Reviewing Results

Use the cleanup module to review and select the best patterns:

```python
# Interactive pattern selection interface
CLEANUP(period=4).select_patterns()
```

### 4. Creating Trading Cards

Generate final trading card images:

```python
# Combines patterns with card templates
COMBINE(period=4).run()
```

## Output

The tool generates several types of output:

- **GIF animations** of discovered spaceships (`gifs/` directory)
- **QR codes** linking to pattern databases (`qrs/` directory)  
- **Trading card fronts** with pattern info (`card_fronts/` directory)
- **Trading card backs** with QR codes (`card_backs/` directory)
- **Pattern sheets** for printing multiple cards
- **patterns.json** with metadata for all discovered patterns

## Dependencies

### Python Packages
- `numpy`: Numerical computations
- `pillow`: Image processing for trading cards
- `qrcode`: QR code generation
- `imageio`: GIF creation and manipulation
- `unique-names-generator`: Random pattern naming

### External Tools
- **ntzfind**: High-performance spaceship search tool by Tom Rokicki
- **lifelib**: Comprehensive Game of Life pattern library by Adam Goucher
- **Golly**: Pattern editor and simulator

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is open source and available under the [MIT License](LICENSE).

## Acknowledgments

- Tom Rokicki for the ntzfind spaceship search tool
- Adam Goucher for the lifelib pattern library
- The Conway's Game of Life community for continued pattern discovery
