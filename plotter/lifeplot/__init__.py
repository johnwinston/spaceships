"""Game of Life pattern processor for pen plotters.

This package provides modular components for processing Game of Life patterns
and generating plotter-ready SVG files with crosshatch fills.

Modules:
    rle_parser: Parse and serialize RLE format patterns
    game_of_life: Simulate Game of Life evolution
    hatching: Generate crosshatch patterns
    svg_generator: Create plotter-ready SVG files
    grid_layout: Arrange multiple patterns on paper with cut lines
    circle_layout: Arrange patterns in concentric circles
"""

from .rle_parser import RLEParser
from .game_of_life import PatternEvolver
from .hatching import HatchGenerator
from .svg_generator import SVGGenerator
from .grid_layout import GridLayout, StandardPaperSizes, InfoGridLayout
from .circle_layout import CircleLayout

__all__ = [
    'RLEParser',
    'PatternEvolver',
    'HatchGenerator',
    'SVGGenerator',
    'GridLayout',
    'StandardPaperSizes',
    'InfoGridLayout',
    'CircleLayout',
]

__version__ = '1.0.0'
