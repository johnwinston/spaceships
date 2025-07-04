# Quick Start Guide

Get up and running with the Spaceship Trading Card generator in just a few minutes!

## ⚡ 30-Second Setup

1. **Clone and setup:**
   ```bash
   git clone --recursive <your-repo-url>
   cd spaceship-trading-cards
   python setup.py
   ```

2. **Run the tool:**
   ```bash
   python main.py
   ```

3. **Follow the interactive prompts** to discover spaceships and create trading cards!

## 🎯 Example: Finding Period-4 Spaceships

Want to find some period-4 spaceships? Here's what to do:

1. Run `python main.py`
2. When prompted "Run spaceship discovery", enter `y`
3. Enter period: `4`
4. Enter number of spaceships: `5`
5. Let the tool work its magic!
6. Review the patterns when prompted
7. Create trading cards when prompted

## 📁 Output Locations

After running, check these folders:
- `gifs/` - Animated patterns
- `qrs/` - QR codes for sharing
- `card_fronts/` - Front sides of trading cards
- `card_backs/` - Back sides of trading cards

## 🔧 Troubleshooting

**"ntzfind not found"**: Run `make` in `submodules/ntzfind/`

**"Missing dependencies"**: Run `pip install -r requirements.txt`

**"Submodules missing"**: Run `git submodule update --init --recursive`

**Need help?** Check the full [README.md](README.md) for detailed instructions.

## 🎨 Tips

- Start with small periods (2-4) for faster results
- Review patterns carefully - not all discoveries are interesting!
- Trading cards look best when printed on cardstock
- Share your QR codes with the Game of Life community

Happy spaceship hunting! 🚀