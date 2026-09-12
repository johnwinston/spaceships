"""Circle layout generator for plotter output.

This module creates layouts with patterns arranged in concentric circles
on standard paper sizes. Each pattern position gets its own set of
concentric circles instead of grid cells.
"""

import math
from pathlib import Path
from typing import Tuple, List
from xml.etree import ElementTree as ET


class CircleLayout:
    """Creates circular layouts of SVG patterns on standard paper sizes.

    Arranges multiple patterns in concentric circles with each pattern
    position marked by a few concentric circles, optimized for pen plotter
    output on standard paper sizes.
    """

    # DPI constant for pixel to mm conversion (96 DPI standard)
    DPI = 96.0
    MM_PER_INCH = 25.4

    def __init__(
        self,
        num_positions: int,
        paper_width_mm: float,
        paper_height_mm: float,
        num_circles: int = 3,
        circle_spacing_mm: float = 5.0,
        edge_margin_mm: float = 25.4  # 1 inch default margin
    ):
        """Initialize circle layout.

        Args:
            num_positions: Number of pattern positions to arrange in circles
            paper_width_mm: Paper width in millimeters
            paper_height_mm: Paper height in millimeters
            num_circles: Number of concentric circles per pattern position (default: 3)
            circle_spacing_mm: Spacing between concentric circles in mm (default: 5mm)
            edge_margin_mm: Edge margin from paper edge (default: 1 inch)
        """
        self.num_positions = num_positions
        self.paper_width_mm = paper_width_mm
        self.paper_height_mm = paper_height_mm
        self.num_circles = num_circles
        self.circle_spacing_mm = circle_spacing_mm
        self.edge_margin_mm = edge_margin_mm

    def generate(
        self,
        svg_files: List[Path],
        output_file: Path
    ) -> bool:
        """Generate circle layout SVG from input files.

        Args:
            svg_files: List of SVG file paths to arrange in circles
            output_file: Output SVG file path

        Returns:
            True if successful, False otherwise
        """
        if not svg_files:
            print("No SVG files to arrange in circles")
            return False

        # Limit to requested positions
        svg_files = svg_files[:self.num_positions]

        print(f"Creating circular layout with {len(svg_files)} patterns")
        print(f"  {self.num_circles} concentric circles per position")

        # Convert paper size to pixels
        paper_width_px = self._mm_to_px(self.paper_width_mm)
        paper_height_px = self._mm_to_px(self.paper_height_mm)
        edge_margin_px = self._mm_to_px(self.edge_margin_mm)

        # Calculate center of paper
        center_x = paper_width_px / 2
        center_y = paper_height_px / 2

        # Calculate working area (inside margins)
        working_width = paper_width_px - 2 * edge_margin_px
        working_height = paper_height_px - 2 * edge_margin_px

        # Maximum radius for arranging patterns (use smaller dimension)
        max_radius = min(working_width, working_height) / 2

        # Find maximum pattern dimensions
        max_width_px = 0
        max_height_px = 0
        try:
            for svg_file in svg_files:
                tree = ET.parse(svg_file)
                root = tree.getroot()
                w = self._parse_dimension(root.get('width', '0'))
                h = self._parse_dimension(root.get('height', '0'))
                max_width_px = max(max_width_px, w)
                max_height_px = max(max_height_px, h)

            pattern_width_px = max_width_px
            pattern_height_px = max_height_px
        except Exception as e:
            print(f"Error parsing SVG files: {e}")
            return False

        pattern_width_mm = self._px_to_mm(pattern_width_px)
        pattern_height_mm = self._px_to_mm(pattern_height_px)

        print(f"  Max pattern size: {pattern_width_mm:.2f}mm × {pattern_height_mm:.2f}mm")

        # Calculate circle radius for each pattern (based on pattern size)
        pattern_radius_px = max(pattern_width_px, pattern_height_px) / 2
        circle_spacing_px = self._mm_to_px(self.circle_spacing_mm)
        outer_circle_radius = pattern_radius_px + (self.num_circles - 1) * circle_spacing_px

        # Calculate arrangement radius (leave space for patterns and circles)
        arrangement_radius = max_radius - outer_circle_radius

        print(f"  Arrangement radius: {self._px_to_mm(arrangement_radius):.2f}mm")

        # Create SVG
        svg = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.paper_width_mm:.2f}mm" height="{self.paper_height_mm:.2f}mm" '
            f'viewBox="0 0 {paper_width_px:.2f} {paper_height_px:.2f}">',
            f'  <!-- Circular Layout with {len(svg_files)} patterns -->'
        ]

        # Calculate positions around circles
        positions = self._calculate_positions(
            len(svg_files),
            center_x,
            center_y,
            arrangement_radius
        )

        # Add each pattern with its concentric circles
        for idx, svg_file in enumerate(svg_files):
            pos_x, pos_y = positions[idx]

            try:
                tree = ET.parse(svg_file)
                root = tree.getroot()

                # Get actual pattern dimensions
                actual_width_px = self._parse_dimension(root.get('width', '0'))
                actual_height_px = self._parse_dimension(root.get('height', '0'))

                # Center pattern at position
                pattern_x = pos_x - actual_width_px / 2
                pattern_y = pos_y - actual_height_px / 2

                # Add group for this pattern and its circles
                svg.append(f'  <g id="pattern_{idx}">')

                # Add concentric circles (draw from outer to inner)
                for circle_idx in range(self.num_circles - 1, -1, -1):
                    radius = pattern_radius_px + circle_idx * circle_spacing_px
                    svg.append(
                        f'    <circle cx="{pos_x:.2f}" cy="{pos_y:.2f}" '
                        f'r="{radius:.2f}" '
                        f'fill="none" stroke="blue" stroke-width="0.5"/>'
                    )

                # Add the pattern
                svg.append(
                    f'    <g transform="translate({pattern_x:.2f}, {pattern_y:.2f})">'
                )

                # Copy all child elements from the pattern
                for child in root:
                    elem_str = ET.tostring(child, encoding='unicode')
                    svg.append('      ' + elem_str)

                svg.append('    </g>')
                svg.append('  </g>')

            except Exception as e:
                print(f"Error processing {svg_file}: {e}")
                continue

        svg.append('</svg>')

        # Write output
        try:
            with open(output_file, 'w') as f:
                f.write('\n'.join(svg))

            print(f"\nCircle layout saved to: {output_file}")
            print(f"Paper size: {self.paper_width_mm:.2f}mm × {self.paper_height_mm:.2f}mm")
            print(f"Edge margin: {self.edge_margin_mm:.2f}mm")
            return True

        except Exception as e:
            print(f"Error writing output file: {e}")
            return False

    def _calculate_positions(
        self,
        num_patterns: int,
        center_x: float,
        center_y: float,
        radius: float
    ) -> List[Tuple[float, float]]:
        """Calculate positions for patterns arranged in circles.

        Arranges patterns evenly around concentric circles. If there's only
        one pattern, it goes in the center.

        Args:
            num_patterns: Number of patterns to position
            center_x: X coordinate of paper center
            center_y: Y coordinate of paper center
            radius: Maximum radius for arrangement

        Returns:
            List of (x, y) positions
        """
        if num_patterns == 0:
            return []

        if num_patterns == 1:
            # Single pattern in center
            return [(center_x, center_y)]

        positions = []

        # Arrange patterns in concentric circles
        # Use a simple strategy: distribute evenly around one or more circles

        if num_patterns <= 6:
            # Single circle arrangement
            angle_step = 2 * math.pi / num_patterns
            for i in range(num_patterns):
                angle = i * angle_step - math.pi / 2  # Start at top
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                positions.append((x, y))
        else:
            # Multiple concentric circles
            # Inner circle: 6 patterns
            # Outer circle: remaining patterns
            inner_count = min(6, num_patterns)
            outer_count = num_patterns - inner_count

            inner_radius = radius * 0.5
            outer_radius = radius

            # Inner circle
            angle_step = 2 * math.pi / inner_count
            for i in range(inner_count):
                angle = i * angle_step - math.pi / 2
                x = center_x + inner_radius * math.cos(angle)
                y = center_y + inner_radius * math.sin(angle)
                positions.append((x, y))

            # Outer circle
            if outer_count > 0:
                angle_step = 2 * math.pi / outer_count
                for i in range(outer_count):
                    angle = i * angle_step - math.pi / 2
                    x = center_x + outer_radius * math.cos(angle)
                    y = center_y + outer_radius * math.sin(angle)
                    positions.append((x, y))

        return positions

    def calculate_pattern_size(self) -> Tuple[float, float]:
        """Calculate the size each pattern should be to fit nicely.

        Returns:
            Tuple of (pattern_width_mm, pattern_height_mm)
        """
        # Calculate available space considering margins and circles
        working_width = self.paper_width_mm - 2 * self.edge_margin_mm
        working_height = self.paper_height_mm - 2 * self.edge_margin_mm

        max_dimension = min(working_width, working_height)

        # Account for circle spacing
        total_circle_spacing = self.circle_spacing_mm * (self.num_circles - 1)

        # Estimate pattern size (conservative)
        if self.num_positions <= 6:
            # Single circle arrangement
            pattern_size_mm = (max_dimension / 4) - total_circle_spacing
        else:
            # Multiple circles
            pattern_size_mm = (max_dimension / 6) - total_circle_spacing

        return pattern_size_mm, pattern_size_mm

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

        import re
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
