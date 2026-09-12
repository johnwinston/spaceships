"""Grid layout generator for plotter output.

This module creates grid layouts with multiple patterns arranged
on standard paper sizes, with cut lines for easy separation.
"""

import re
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional
from xml.etree import ElementTree as ET


class StandardPaperSizes:
    """Standard paper sizes in millimeters (width, height)."""

    LETTER = (215.9, 279.4)      # 8.5 × 11 inches
    LEGAL = (215.9, 355.6)       # 8.5 × 14 inches
    A4 = (210.0, 297.0)          # A4
    A3 = (297.0, 420.0)          # A3
    CUSTOM_11X14 = (279.4, 355.6)  # 11 × 14 inches

    _SIZES = {
        'letter': LETTER,
        'legal': LEGAL,
        'a4': A4,
        'a3': A3,
        '11x14': CUSTOM_11X14,
    }

    @classmethod
    def get_size(cls, name: str) -> Tuple[float, float]:
        """Get paper size by name.

        Args:
            name: Paper size name (letter, legal, a4, a3, 11x14)

        Returns:
            Tuple of (width_mm, height_mm)

        Raises:
            ValueError: If paper size name is unknown
        """
        name_lower = name.lower()
        if name_lower not in cls._SIZES:
            raise ValueError(
                f"Unknown paper size: {name}. "
                f"Valid options: {', '.join(cls._SIZES.keys())}"
            )
        return cls._SIZES[name_lower]


class GridLayout:
    """Creates grid layouts of SVG patterns on standard paper sizes.

    Arranges multiple patterns in a grid with cut lines for separation,
    optimized for pen plotter output on standard paper sizes.
    """

    # DPI constant for pixel to mm conversion (96 DPI standard)
    DPI = 96.0
    MM_PER_INCH = 25.4

    def __init__(
        self,
        rows: int,
        cols: int,
        paper_width_mm: float,
        paper_height_mm: float,
        min_spacing_mm: float = 25.4,  # 1 inch minimum
        edge_margin_mm: float = 0.0    # No edge margin by default
    ):
        """Initialize grid layout.

        Args:
            rows: Number of rows in grid
            cols: Number of columns in grid
            paper_width_mm: Paper width in millimeters
            paper_height_mm: Paper height in millimeters
            min_spacing_mm: Minimum spacing between patterns in mm (default: 1 inch)
            edge_margin_mm: Edge margin to subtract from paper size (default: 0)
        """
        self.rows = rows
        self.cols = cols
        # Optionally reduce paper size by edge margins
        if edge_margin_mm > 0:
            self.paper_width_mm = paper_width_mm - (2 * edge_margin_mm)
            self.paper_height_mm = paper_height_mm - (2 * edge_margin_mm)
        else:
            self.paper_width_mm = paper_width_mm
            self.paper_height_mm = paper_height_mm
        self.min_spacing_mm = min_spacing_mm
        self.edge_margin_mm = edge_margin_mm

    def generate(
        self,
        svg_files: List[Path],
        output_file: Path
    ) -> bool:
        """Generate grid layout SVG from input files.

        Args:
            svg_files: List of SVG file paths to arrange in grid
            output_file: Output SVG file path

        Returns:
            True if successful, False otherwise
        """
        if not svg_files:
            print("No SVG files to arrange in grid")
            return False

        # Limit to grid size
        max_patterns = self.rows * self.cols
        svg_files = svg_files[:max_patterns]

        print(f"Creating {self.rows}×{self.cols} grid with {len(svg_files)} patterns")

        # Use calculated pattern size for consistent spacing
        # (Individual SVGs may vary slightly due to different cell counts)
        pattern_width_mm, pattern_height_mm = self.calculate_pattern_size()
        pattern_width_px = self._mm_to_px(pattern_width_mm)
        pattern_height_px = self._mm_to_px(pattern_height_mm)

        print(f"Using calculated pattern size: {pattern_width_mm:.2f}mm × {pattern_height_mm:.2f}mm")

        # Convert paper size and spacing to pixels
        paper_width_px = self._mm_to_px(self.paper_width_mm)
        paper_height_px = self._mm_to_px(self.paper_height_mm)
        spacing_px = self._mm_to_px(self.min_spacing_mm)

        # Cut margin: 5mm on each side of each pattern
        cut_margin_px = self._mm_to_px(5.0)

        # Add margins (5mm on all sides)
        left_margin_px = self._mm_to_px(5.0)
        right_margin_px = self._mm_to_px(5.0)
        top_margin_px = self._mm_to_px(5.0)
        bottom_margin_px = self._mm_to_px(5.0)

        # Calculate total grid dimensions including cut margins
        # Patterns are sized to fit with cut margins, so we need to add cut margin space
        cut_margin_total_px = self._mm_to_px(10.0)  # 5mm on each side
        total_grid_width = self.cols * (pattern_width_px + cut_margin_total_px) + (self.cols - 1) * spacing_px
        total_grid_height = self.rows * (pattern_height_px + cut_margin_total_px) + (self.rows - 1) * spacing_px

        # Calculate horizontal offset (right-align with margins)
        available_width = paper_width_px - left_margin_px - right_margin_px
        if total_grid_width > available_width:
            # Content is too wide, use left margin only
            offset_x = left_margin_px
        else:
            # Right-align with right margin
            offset_x = paper_width_px - right_margin_px - total_grid_width

        # Calculate vertical offset (center vertically with margins)
        available_height = paper_height_px - top_margin_px - bottom_margin_px
        if total_grid_height > available_height:
            # Content is too tall, use top margin only
            offset_y = top_margin_px
        else:
            # Center vertically with margins
            offset_y = top_margin_px + (available_height - total_grid_height) / 2

        print(f"PATTERN GRID - offset_x: {offset_x:.2f}px, offset_y: {offset_y:.2f}px")
        print(f"PATTERN GRID - total_grid_width: {total_grid_width:.2f}px, total_grid_height: {total_grid_height:.2f}px")

        # Create SVG
        svg = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.paper_width_mm:.2f}mm" height="{self.paper_height_mm:.2f}mm" '
            f'viewBox="0 0 {paper_width_px:.2f} {paper_height_px:.2f}">',
            f'  <!-- {self.rows}×{self.cols} Grid Layout, right-aligned -->'
        ]

        # Add patterns aligned to the right and track their positions
        pattern_idx = 0
        pattern_positions = []  # List of (x, y, width, height) for each pattern

        for row in range(self.rows):
            for col in range(self.cols):
                if pattern_idx >= len(svg_files):
                    break

                # Position patterns in grid with space for cut margins
                # Each cell gets: pattern + cut margin (10mm) + spacing
                cell_x = offset_x + col * (pattern_width_px + cut_margin_total_px + spacing_px) + cut_margin_px
                cell_y = offset_y + row * (pattern_height_px + cut_margin_total_px + spacing_px) + cut_margin_px

                svg_file = svg_files[pattern_idx]

                try:
                    tree = ET.parse(svg_file)
                    root = tree.getroot()

                    # Get actual pattern dimensions
                    actual_width_px = self._parse_dimension(root.get('width', '0'))
                    actual_height_px = self._parse_dimension(root.get('height', '0'))

                    # Center pattern within cell
                    center_offset_x = (pattern_width_px - actual_width_px) / 2
                    center_offset_y = (pattern_height_px - actual_height_px) / 2

                    x = cell_x + center_offset_x
                    y = cell_y + center_offset_y

                    # Store pattern position for cut line generation
                    pattern_positions.append((x, y, actual_width_px, actual_height_px))

                    svg.append(
                        f'  <g id="pattern_{row}_{col}" '
                        f'transform="translate({x:.2f}, {y:.2f})">'
                    )

                    # Copy all child elements
                    for child in root:
                        elem_str = ET.tostring(child, encoding='unicode')
                        svg.append('    ' + elem_str)

                    svg.append('  </g>')

                    pattern_idx += 1

                except Exception as e:
                    print(f"Error processing {svg_file}: {e}")
                    continue

        # Add cut lines 2mm from pattern borders
        svg.extend(self._generate_cut_lines_from_patterns(
            pattern_positions,
            paper_width_px,
            paper_height_px
        ))

        svg.append('</svg>')

        # Write output
        try:
            with open(output_file, 'w') as f:
                f.write('\n'.join(svg))

            print(f"\nGrid layout saved to: {output_file}")
            print(f"Paper size: {self.paper_width_mm:.2f}mm × {self.paper_height_mm:.2f}mm")
            print(f"Pattern spacing: {self.min_spacing_mm}mm")
            return True

        except Exception as e:
            print(f"Error writing output file: {e}")
            return False

    def _generate_cut_lines_from_patterns(
        self,
        pattern_positions: List[Tuple[float, float, float, float]],
        paper_width_px: float,
        paper_height_px: float
    ) -> List[str]:
        """Generate cut lines 5mm from each pattern's border.

        Args:
            pattern_positions: List of (x, y, width, height) for each pattern
            paper_width_px: Paper width in pixels
            paper_height_px: Paper height in pixels

        Returns:
            List of SVG lines for cut lines
        """
        svg_lines = [
            '  <!-- Cut lines (5mm from pattern borders) -->',
            '  <g id="cut-lines" stroke="red" stroke-width="0.5" '
            'stroke-dasharray="5,5" fill="none">'
        ]

        # Convert 5mm to pixels
        cut_margin_px = self._mm_to_px(5.0)

        # Draw rectangle around each pattern, 5mm from its border
        for idx, (x, y, width, height) in enumerate(pattern_positions):
            # Calculate cut line rectangle (5mm outside pattern border)
            cut_x = x - cut_margin_px
            cut_y = y - cut_margin_px
            cut_width = width + 2 * cut_margin_px
            cut_height = height + 2 * cut_margin_px

            svg_lines.append(
                f'    <rect x="{cut_x:.2f}" y="{cut_y:.2f}" '
                f'width="{cut_width:.2f}" height="{cut_height:.2f}"/>'
            )

        svg_lines.append('  </g>')
        return svg_lines

    def calculate_pattern_size(self) -> Tuple[float, float]:
        """Calculate the size each pattern should be to fit the grid.

        Pattern size accounts for spacing and 5mm cut margins on each side,
        so grid with cut lines fits perfectly on paper.

        Returns:
            Tuple of (pattern_width_mm, pattern_height_mm)
        """
        # Cut margin: 5mm on each side = 10mm total per pattern
        cut_margin_total = 10.0

        # Safety margin to account for rounding and slight oversizing
        safety_margin = 1.5  # mm per pattern

        # Calculate space used by gaps between patterns
        total_spacing_width = self.min_spacing_mm * (self.cols - 1)
        total_spacing_height = self.min_spacing_mm * (self.rows - 1)

        # Calculate space used by cut margins (10mm per pattern) plus safety margin
        total_cut_margins_width = (cut_margin_total + safety_margin) * self.cols
        total_cut_margins_height = (cut_margin_total + safety_margin) * self.rows

        # Remaining space divided among patterns (excluding cut margins and safety)
        pattern_width_mm = (self.paper_width_mm - total_spacing_width - total_cut_margins_width) / self.cols
        pattern_height_mm = (self.paper_height_mm - total_spacing_height - total_cut_margins_height) / self.rows

        return pattern_width_mm, pattern_height_mm

    @classmethod
    def _parse_dimension(cls, dim_str: str) -> float:
        """Parse dimension string that may include units (mm, in, px, etc.).

        Args:
            dim_str: Dimension string (e.g., "100mm", "4in", "200")

        Returns:
            Dimension in pixels
        """
        if not dim_str:
            return 0.0

        match = re.match(r'([\d.]+)(mm|in|cm|px|pt)?', str(dim_str))
        if match:
            value = float(match.group(1))
            unit = match.group(2)

            if unit == 'mm':
                return cls._mm_to_px(value)
            elif unit == 'in':
                return value * cls.DPI
            elif unit == 'cm':
                return cls._mm_to_px(value * 10)
            elif unit == 'pt':
                return value * cls.DPI / 72
            else:  # px or no unit
                return value

        return 0.0

    @classmethod
    def _px_to_mm(cls, pixels: float) -> float:
        """Convert pixels to millimeters.

        Args:
            pixels: Size in pixels

        Returns:
            Size in millimeters
        """
        return pixels * cls.MM_PER_INCH / cls.DPI

    @classmethod
    def _mm_to_px(cls, mm: float) -> float:
        """Convert millimeters to pixels.

        Args:
            mm: Size in millimeters

        Returns:
            Size in pixels
        """
        return mm * cls.DPI / cls.MM_PER_INCH


class InfoGridLayout:
    """Creates information grid layouts for the back of pattern sheets.
    
    Places text in each cell of a grid with specified information in corners.
    """

    # DPI constant for pixel to mm conversion (96 DPI standard)
    DPI = 96.0
    MM_PER_INCH = 25.4
    
    # Common Inkscape installation paths
    INKSCAPE_PATHS = [
        "/Applications/Inkscape.app/Contents/MacOS/inkscape",  # macOS app
        "/usr/local/bin/inkscape",  # Homebrew/MacPorts
        "/usr/bin/inkscape",  # Linux
        "inkscape",  # In PATH
    ]

    def __init__(
        self,
        rows: int,
        cols: int,
        paper_width_mm: float,
        paper_height_mm: float,
        min_spacing_mm: float = 25.4,
        edge_margin_mm: float = 0.0,
        auto_convert_text: bool = True
    ):
        """Initialize info grid layout.

        Args:
            rows: Number of rows in grid
            cols: Number of columns in grid
            paper_width_mm: Paper width in millimeters
            paper_height_mm: Paper height in millimeters
            min_spacing_mm: Minimum spacing between cells in mm
            edge_margin_mm: Edge margin to subtract from paper size
            auto_convert_text: If True, automatically convert text to paths using Inkscape
        """
        self.rows = rows
        self.cols = cols
        if edge_margin_mm > 0:
            self.paper_width_mm = paper_width_mm - (2 * edge_margin_mm)
            self.paper_height_mm = paper_height_mm - (2 * edge_margin_mm)
        else:
            self.paper_width_mm = paper_width_mm
            self.paper_height_mm = paper_height_mm
        self.min_spacing_mm = min_spacing_mm
        self.edge_margin_mm = edge_margin_mm
        self.auto_convert_text = auto_convert_text

    def generate(
        self,
        pattern_name: str,
        pattern_type: str,
        total_generations: int,
        output_file: Path,
        svg_files: List[Path]
    ) -> bool:
        """Generate information grid SVG.

        Args:
            pattern_name: Name of the pattern (e.g., "Doo-dah")
            pattern_type: Type of pattern (e.g., "Spaceship", "Oscillator")
            total_generations: Total number of generations/phases
            output_file: Output SVG file path
            svg_files: List of SVG files to match dimensions

        Returns:
            True if successful, False otherwise
        """
        # First, find maximum pattern dimensions to calculate grid positioning (same as pattern grid)
        max_width_px = 0
        max_height_px = 0
        pattern_dimensions = []  # Store individual dimensions for each pattern
        
        try:
            max_patterns = self.rows * self.cols
            for svg_file in svg_files[:max_patterns]:
                tree = ET.parse(svg_file)
                root = tree.getroot()
                w = self._parse_dimension(root.get('width', '0'))
                h = self._parse_dimension(root.get('height', '0'))
                pattern_dimensions.append((w, h))
                max_width_px = max(max_width_px, w)
                max_height_px = max(max_height_px, h)

            # Use max dimensions for grid layout calculations
            pattern_width_px = max_width_px
            pattern_height_px = max_height_px
            print(f"INFO GRID - Max dimensions: {max_width_px}px × {max_height_px}px from {len(pattern_dimensions)} patterns")
        except Exception as e:
            print(f"Error parsing SVG files: {e}")
            # Fallback to calculated cell size
            cell_width_mm, cell_height_mm = self.calculate_cell_size()
            pattern_width_px = self._mm_to_px(cell_width_mm)
            pattern_height_px = self._mm_to_px(cell_height_mm)
            pattern_dimensions = [(pattern_width_px, pattern_height_px)] * max_patterns

        spacing_px = self._mm_to_px(self.min_spacing_mm)
        paper_width_px = self._mm_to_px(self.paper_width_mm)
        paper_height_px = self._mm_to_px(self.paper_height_mm)

        # Add margins (5mm on left, 5mm + 1.25 inches on right)
        left_margin_px = self._mm_to_px(5.0)
        right_margin_px = self._mm_to_px(5.0 + 31.75)  # 5mm + 1.25 inches (31.75mm)

        # Calculate offset for right alignment with margins (using max dimensions)
        total_grid_width = self.cols * pattern_width_px + (self.cols - 1) * spacing_px
        # Ensure content stays within margins
        available_width = paper_width_px - left_margin_px - right_margin_px
        if total_grid_width > available_width:
            # Content is too wide, use left margin only
            offset_x = left_margin_px
        else:
            # Right-align with right margin
            offset_x = paper_width_px - right_margin_px - total_grid_width
        
        print(f"INFO GRID - offset_x: {offset_x:.2f}px, total_grid_width: {total_grid_width:.2f}px")

        # Convert cell dimensions to mm for display
        pattern_width_mm = self._px_to_mm(pattern_width_px)
        pattern_height_mm = self._px_to_mm(pattern_height_px)

        print(f"Creating {self.rows}×{self.cols} info grid")
        print(f"Max cell size: {pattern_width_mm:.2f}mm × {pattern_height_mm:.2f}mm (matching pattern grid)")

        # Create SVG
        svg = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.paper_width_mm:.2f}mm" height="{self.paper_height_mm:.2f}mm" '
            f'viewBox="0 0 {paper_width_px:.2f} {paper_height_px:.2f}">',
            f'  <!-- {self.rows}×{self.cols} Info Grid Layout (Horizontally Flipped for Back Side) -->',
            '  <!-- NOTE: Text elements use fonts and must be converted to paths before plotting. -->',
            '  <!-- Use Inkscape: Path > Object to Path, or Hershey Text extension for stroke fonts. -->',
            '  <style>',
            '    .info-text { font-family: "Times New Roman", Times, serif; font-size: 12px; fill: black; }',
            '    .cell-border { fill: none; stroke: black; stroke-width: 0.5; }',
            '  </style>',
            f'  <!-- Horizontal flip group for back-to-back alignment -->',
            f'  <g transform="scale(-1, 1) translate(-{paper_width_px:.2f}, 0)">'
        ]

        # Add cells with information
        cell_idx = 0
        for row in range(self.rows):
            for col in range(self.cols):
                if cell_idx >= total_generations or cell_idx >= len(pattern_dimensions):
                    break

                # Get individual pattern dimensions for this cell
                actual_width_px, actual_height_px = pattern_dimensions[cell_idx]
                
                # Position cells using max dimensions for grid spacing (same as pattern grid)
                cell_x = offset_x + col * (pattern_width_px + spacing_px)
                cell_y = row * (pattern_height_px + spacing_px)
                
                # Center the border within the grid cell (matching pattern grid centering)
                center_offset_x = (pattern_width_px - actual_width_px) / 2
                center_offset_y = (pattern_height_px - actual_height_px) / 2
                border_x = cell_x + center_offset_x
                border_y = cell_y + center_offset_y

                svg.append(f'  <g id="cell_{row}_{col}">')
                
                # Cell border using individual pattern dimensions (matches actual pattern size)
                svg.append(
                    f'    <rect class="cell-border" '
                    f'x="{border_x:.2f}" y="{border_y:.2f}" '
                    f'width="{actual_width_px:.2f}" height="{actual_height_px:.2f}"/>'
                )

                # Padding for text
                padding = 10

                # Top-left: Pattern name
                svg.append(
                    f'    <text class="info-text" '
                    f'x="{border_x + padding:.2f}" y="{border_y + padding + 10:.2f}" '
                    f'text-anchor="start">{pattern_name}</text>'
                )

                # Top-right: "Conway's Game of Life"
                svg.append(
                    f'    <text class="info-text" '
                    f'x="{border_x + actual_width_px - padding:.2f}" y="{border_y + padding + 10:.2f}" '
                    f'text-anchor="end">Conway\'s Game of Life</text>'
                )

                # Bottom-left: Fixed phase label
                svg.append(
                    f'    <text class="info-text" '
                    f'x="{border_x + padding:.2f}" y="{border_y + actual_height_px - padding:.2f}" '
                    f'text-anchor="start">Phase 1 of 21</text>'
                )

                # Bottom-right: Pattern type
                svg.append(
                    f'    <text class="info-text" '
                    f'x="{border_x + actual_width_px - padding:.2f}" y="{border_y + actual_height_px - padding:.2f}" '
                    f'text-anchor="end">{pattern_type}</text>'
                )

                svg.append('  </g>')
                cell_idx += 1

        # Add cut lines using max dimensions (same as pattern grid)
        svg.extend(self._generate_cut_lines(
            pattern_width_px,
            pattern_height_px,
            spacing_px,
            offset_x,
            paper_width_px,
            paper_height_px
        ))

        svg.append('  </g>')  # Close horizontal flip group
        svg.append('</svg>')

        # Write output
        try:
            with open(output_file, 'w') as f:
                f.write('\n'.join(svg))

            print(f"\nInfo grid saved to: {output_file}")
            
            # Automatically convert text to paths if enabled
            if self.auto_convert_text:
                if self._convert_text_to_paths(output_file):
                    print("  ✓ Text converted to paths (plotter-ready)")
                else:
                    print("  ⚠ Text conversion skipped - convert manually in Inkscape")
            
            return True

        except Exception as e:
            print(f"Error writing output file: {e}")
            return False

    def _generate_cut_lines(
        self,
        cell_width_px: float,
        cell_height_px: float,
        spacing_px: float,
        offset_x: float,
        paper_width_px: float,
        paper_height_px: float
    ) -> List[str]:
        """Generate cut lines for info grid."""
        svg_lines = [
            '  <!-- Cut lines -->',
            '  <g id="cut-lines" stroke="red" stroke-width="0.5" '
            'stroke-dasharray="5,5" fill="none">'
        ]

        # Vertical cut lines
        for col in range(1, self.cols):
            x = offset_x + col * (cell_width_px + spacing_px) - spacing_px / 2
            svg_lines.append(
                f'    <line x1="{x:.2f}" y1="0" '
                f'x2="{x:.2f}" y2="{paper_height_px:.2f}"/>'
            )

        # Right edge cut line
        svg_lines.append(
            f'    <line x1="{paper_width_px:.2f}" y1="0" '
            f'x2="{paper_width_px:.2f}" y2="{paper_height_px:.2f}"/>'
        )

        # Horizontal cut lines
        for row in range(1, self.rows):
            y = row * (cell_height_px + spacing_px) - spacing_px / 2
            svg_lines.append(
                f'    <line x1="{offset_x:.2f}" y1="{y:.2f}" '
                f'x2="{paper_width_px:.2f}" y2="{y:.2f}"/>'
            )

        svg_lines.append('  </g>')
        return svg_lines

    def calculate_cell_size(self) -> Tuple[float, float]:
        """Calculate the size each cell should be to fit the grid.

        Returns:
            Tuple of (cell_width_mm, cell_height_mm)
        """
        total_spacing_width = self.min_spacing_mm * (self.cols - 1)
        total_spacing_height = self.min_spacing_mm * (self.rows - 1)

        cell_width_mm = (self.paper_width_mm - total_spacing_width) / self.cols
        cell_height_mm = (self.paper_height_mm - total_spacing_height) / self.rows

        return cell_width_mm, cell_height_mm

    @classmethod
    def _parse_dimension(cls, dim_str: str) -> float:
        """Parse dimension string that may include units (mm, in, px, etc.).

        Args:
            dim_str: Dimension string (e.g., "100mm", "4in", "200")

        Returns:
            Dimension in pixels
        """
        if not dim_str:
            return 0.0

        match = re.match(r'([\d.]+)(mm|in|cm|px|pt)?', str(dim_str))
        if match:
            value = float(match.group(1))
            unit = match.group(2)

            if unit == 'mm':
                return cls._mm_to_px(value)
            elif unit == 'in':
                return value * cls.DPI
            elif unit == 'cm':
                return cls._mm_to_px(value * 10)
            elif unit == 'pt':
                return value * cls.DPI / 72
            else:  # px or no unit
                return value

        return 0.0

    @classmethod
    def _px_to_mm(cls, pixels: float) -> float:
        """Convert pixels to millimeters.

        Args:
            pixels: Size in pixels

        Returns:
            Size in millimeters
        """
        return pixels * cls.MM_PER_INCH / cls.DPI

    @classmethod
    def _mm_to_px(cls, mm: float) -> float:
        """Convert millimeters to pixels."""
        return mm * cls.DPI / cls.MM_PER_INCH
    
    @classmethod
    def _find_inkscape(cls) -> Optional[str]:
        """Find Inkscape executable.
        
        Returns:
            Path to Inkscape executable, or None if not found
        """
        for path in cls.INKSCAPE_PATHS:
            try:
                result = subprocess.run(
                    [path, "--version"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return None
    
    def _convert_text_to_paths(self, svg_file: Path) -> bool:
        """Convert text elements to paths using Inkscape.
        
        Args:
            svg_file: SVG file to convert (will be modified in-place)
            
        Returns:
            True if successful, False otherwise
        """
        inkscape_path = self._find_inkscape()
        if not inkscape_path:
            return False
        
        try:
            # Create temporary output file
            temp_file = svg_file.with_suffix('.tmp.svg')
            
            # Use Inkscape to convert text to paths
            result = subprocess.run(
                [
                    inkscape_path,
                    str(svg_file),
                    "--export-text-to-path",
                    "--export-plain-svg",
                    f"--export-filename={temp_file}"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and temp_file.exists():
                # Replace original with converted version
                temp_file.replace(svg_file)
                return True
            else:
                # Clean up temp file if it exists
                if temp_file.exists():
                    temp_file.unlink()
                return False
                
        except (subprocess.TimeoutExpired, Exception):
            return False
