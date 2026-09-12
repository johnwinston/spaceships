"""SVG file generation for pen plotter output.

This module creates SVG files optimized for pen plotters,
with proper physical dimensions and coordinate systems.
"""

from typing import Set, Tuple, Optional, List


class SVGGenerator:
    """Generates SVG files for Game of Life patterns.

    Creates plotter-ready SVG files with hatched or solid fills,
    proper physical dimensions (mm), and clean coordinate systems.
    """

    # DPI constant for pixel to mm conversion (96 DPI standard)
    DPI = 96.0
    MM_PER_INCH = 25.4

    def __init__(self, cell_size: float = 10.0, padding: int = 1, margin: float = 30.0,
                 use_circles: bool = False, num_circles: int = 3, show_grid: bool = True,
                 circle_with_dot: bool = False, border_width_mm: Optional[float] = None,
                 border_height_mm: Optional[float] = None,
                 unified_bounds: Optional[Tuple[int, int, int, int]] = None,
                 show_artwork_borders: bool = False,
                 cut_line_width_mm: Optional[float] = None,
                 cut_line_height_mm: Optional[float] = None,
                 gap_in: float = 0.5,
                 num_panels: int = 1,
                 panel_index: int = 0,
                 frame_width_mm: Optional[float] = None):
        """Initialize SVG generator.

        Args:
            cell_size: Size of each cell in pixels
            padding: Number of empty cells around the pattern
            margin: Margin around the entire SVG in pixels
            use_circles: If True, use concentric circles instead of hatches/fills
            num_circles: Number of concentric circles per cell (default: 3)
            show_grid: If True, show grid lines (default: True)
            circle_with_dot: If True, start with a filled dot in the center (default: False)
            border_width_mm: Optional fixed border width in mm
            border_height_mm: Optional fixed border height in mm
            unified_bounds: Optional (min_x, min_y, max_x, max_y) for unified grid across
                           multiple generations (for artwork panels)
            show_artwork_borders: If True, draw 6mm solid border around grid plus
                                 dashed cut line (for artwork panels)
            cut_line_width_mm: Optional width of cut line in mm (if None, calculated from border)
            cut_line_height_mm: Optional height of cut line in mm (if None, calculated from border)
            gap_in: Gap in inches for cut line positioning (default: 0.5)
            num_panels: Total number of panels (for interior cut line calculation)
            panel_index: Index of current panel (0 = rightmost/gen 0, increases leftward)
            frame_width_mm: Full frame width in mm (for interior cut line calculation)
        """
        self.cell_size = cell_size
        self.padding = padding
        self.margin = margin
        self.use_circles = use_circles
        self.num_circles = num_circles
        self.show_grid = show_grid
        self.circle_with_dot = circle_with_dot
        self.border_width_mm = border_width_mm
        self.border_height_mm = border_height_mm
        self.unified_bounds = unified_bounds
        self.show_artwork_borders = show_artwork_borders
        self.cut_line_width_mm = cut_line_width_mm
        self.cut_line_height_mm = cut_line_height_mm
        self.gap_in = gap_in
        self.num_panels = num_panels
        self.panel_index = panel_index
        self.frame_width_mm = frame_width_mm

    def generate(
        self,
        live_cells: Set[Tuple[int, int]],
        hatch_generator: Optional[object] = None
    ) -> str:
        """Generate SVG for a pattern.

        Args:
            live_cells: Set of (x, y) coordinates for live cells
            hatch_generator: Optional HatchGenerator for crosshatch fills

        Returns:
            SVG file content as string
        """
        # Use unified bounds if provided, otherwise calculate from current cells
        if self.unified_bounds is not None:
            min_x, min_y, max_x, max_y = self.unified_bounds
            pattern_width = max_x - min_x + 1
            pattern_height = max_y - min_y + 1
        elif not live_cells:
            return self._generate_empty_svg()
        else:
            # Find bounds of the pattern
            min_x = min(x for x, y in live_cells)
            max_x = max(x for x, y in live_cells)
            min_y = min(y for x, y in live_cells)
            max_y = max(y for x, y in live_cells)
            pattern_width = max_x - min_x + 1
            pattern_height = max_y - min_y + 1

        # Grid dimensions with padding
        grid_width = pattern_width + 2 * self.padding
        grid_height = pattern_height + 2 * self.padding

        # Calculate SVG dimensions
        if self.border_width_mm is not None and self.border_height_mm is not None:
            # SVG is the specified dimensions, pattern centered with 5mm margin
            svg_width_mm = self.border_width_mm
            svg_height_mm = self.border_height_mm
            svg_width = self._mm_to_px(svg_width_mm)
            svg_height = self._mm_to_px(svg_height_mm)

            # 5mm margin (same as grid cut line margin)
            margin_mm = 5.0
            margin_px = self._mm_to_px(margin_mm)

            # Pattern grid dimensions in pixels
            pattern_grid_width_px = grid_width * self.cell_size
            pattern_grid_height_px = grid_height * self.cell_size

            # Center the pattern within the SVG (accounting for margin)
            offset_x = (svg_width - pattern_grid_width_px) / 2
            offset_y = (svg_height - pattern_grid_height_px) / 2
        else:
            # Original behavior: size to pattern with margin
            svg_width = grid_width * self.cell_size + 2 * self.margin
            svg_height = grid_height * self.cell_size + 2 * self.margin
            svg_width_mm = self._px_to_mm(svg_width)
            svg_height_mm = self._px_to_mm(svg_height)
            offset_x = self.margin
            offset_y = self.margin

        svg = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{svg_width_mm:.2f}mm" height="{svg_height_mm:.2f}mm" '
            f'viewBox="0 0 {svg_width} {svg_height}">',
            f'  <g transform="translate({offset_x}, {offset_y})">'
        ]

        # Draw live cells - circles, hatched, or filled
        if self.use_circles:
            svg.extend(self._generate_circle_cells(
                live_cells, min_x, min_y
            ))
        elif hatch_generator:
            svg.extend(self._generate_hatched_cells(
                live_cells, min_x, min_y, hatch_generator
            ))
        else:
            svg.extend(self._generate_filled_cells(
                live_cells, min_x, min_y
            ))

        # Draw grid lines (internal only, no outer border)
        if self.show_grid:
            svg.extend(self._generate_grid_lines(grid_width, grid_height))

        # Draw artwork borders if enabled (5mm solid + 0.5" dashed cut line)
        if self.show_artwork_borders:
            svg.extend(self._generate_artwork_borders(grid_width, grid_height))

        svg.append('  </g>')

        # Draw border rectangle at SVG edges if dimensions specified
        if self.border_width_mm is not None and self.border_height_mm is not None:
            svg.append(
                f'  <rect x="0" y="0" width="{svg_width}" height="{svg_height}" '
                f'fill="none" stroke="black" stroke-width="1"/>'
            )

        svg.append('</svg>')

        return '\n'.join(svg)

    def _generate_circle_cells(
        self,
        live_cells: Set[Tuple[int, int]],
        min_x: int,
        min_y: int
    ) -> List[str]:
        """Generate concentric circles for live cells.

        Args:
            live_cells: Set of live cell coordinates
            min_x, min_y: Minimum coordinates for normalization

        Returns:
            List of SVG lines
        """
        svg_lines = ['    <g id="live-cells-circles" stroke="black" stroke-width="0.5" fill="none">']

        # Calculate radius of cell (circles should fit within cell)
        max_radius = self.cell_size / 2

        for x, y in live_cells:
            # Calculate center of cell
            norm_x = (x - min_x + self.padding) * self.cell_size + self.cell_size / 2
            norm_y = (y - min_y + self.padding) * self.cell_size + self.cell_size / 2

            # Draw center dot if requested
            if self.circle_with_dot:
                # Small filled circle in the center (about 1/8 of cell size)
                dot_radius = self.cell_size / 16
                svg_lines.append(
                    f'      <circle cx="{norm_x:.2f}" cy="{norm_y:.2f}" '
                    f'r="{dot_radius:.2f}" fill="black" stroke="none"/>'
                )

            # Draw concentric circles from outer to inner
            for i in range(self.num_circles):
                # Evenly space circles within the cell
                radius = max_radius * (self.num_circles - i) / self.num_circles
                svg_lines.append(
                    f'      <circle cx="{norm_x:.2f}" cy="{norm_y:.2f}" '
                    f'r="{radius:.2f}"/>'
                )

        svg_lines.append('    </g>')
        return svg_lines

    def _generate_hatched_cells(
        self,
        live_cells: Set[Tuple[int, int]],
        min_x: int,
        min_y: int,
        hatch_generator: object
    ) -> List[str]:
        """Generate hatched fill for live cells.

        Args:
            live_cells: Set of live cell coordinates
            min_x, min_y: Minimum coordinates for normalization
            hatch_generator: HatchGenerator instance

        Returns:
            List of SVG lines
        """
        # Generate rectangles for hatching
        rectangles = []
        for x, y in live_cells:
            norm_x = (x - min_x + self.padding) * self.cell_size
            norm_y = (y - min_y + self.padding) * self.cell_size
            rectangles.append((norm_x, norm_y, self.cell_size, self.cell_size))

        # Generate hatch paths
        hatch_paths = hatch_generator.generate_for_rectangles(
            rectangles,
            connect_segments=True,
            connection_radius=3.0
        )

        svg_lines = [
            '    <g id="live-cells-hatched" stroke="black" stroke-width="0.5" fill="none">'
        ]

        # Convert paths to SVG path format
        for path in hatch_paths:
            if not path:
                continue

            path_data = []
            for cmd in path:
                if cmd[0] == 'M':
                    path_data.append(f'M {cmd[1]:.2f},{cmd[2]:.2f}')
                elif cmd[0] == 'L':
                    path_data.append(f'L {cmd[1]:.2f},{cmd[2]:.2f}')
                elif cmd[0] == 'C':
                    path_data.append(
                        f'C {cmd[1]:.2f},{cmd[2]:.2f} '
                        f'{cmd[3]:.2f},{cmd[4]:.2f} '
                        f'{cmd[5]:.2f},{cmd[6]:.2f}'
                    )

            if path_data:
                svg_lines.append(f'      <path d="{" ".join(path_data)}"/>')

        svg_lines.append('    </g>')
        return svg_lines

    def _generate_filled_cells(
        self,
        live_cells: Set[Tuple[int, int]],
        min_x: int,
        min_y: int
    ) -> List[str]:
        """Generate solid fill for live cells.

        Args:
            live_cells: Set of live cell coordinates
            min_x, min_y: Minimum coordinates for normalization

        Returns:
            List of SVG lines
        """
        svg_lines = ['    <g id="live-cells">']

        for x, y in live_cells:
            norm_x = (x - min_x + self.padding) * self.cell_size
            norm_y = (y - min_y + self.padding) * self.cell_size
            svg_lines.append(
                f'      <rect x="{norm_x}" y="{norm_y}" '
                f'width="{self.cell_size}" height="{self.cell_size}" '
                f'fill="black" stroke="none"/>'
            )

        svg_lines.append('    </g>')
        return svg_lines

    def _generate_grid_lines(self, grid_width: int, grid_height: int) -> List[str]:
        """Generate grid lines including outer border.

        Args:
            grid_width: Width of grid in cells
            grid_height: Height of grid in cells

        Returns:
            List of SVG lines
        """
        svg_lines = [
            '    <g id="grid" stroke="black" stroke-width="1">'
        ]

        total_width = grid_width * self.cell_size
        total_height = grid_height * self.cell_size

        # Draw outer border rectangle (twice for double tracing)
        svg_lines.append(
            f'      <rect x="0" y="0" width="{total_width}" height="{total_height}" '
            f'fill="none" stroke="black" stroke-width="1"/>'
        )
        svg_lines.append(
            f'      <rect x="0" y="0" width="{total_width}" height="{total_height}" '
            f'fill="none" stroke="black" stroke-width="1"/>'
        )

        # Vertical lines (twice for double tracing)
        for i in range(1, grid_width + 1):
            x = i * self.cell_size
            svg_lines.append(
                f'      <line x1="{x}" y1="0" '
                f'x2="{x}" y2="{total_height}"/>'
            )
            svg_lines.append(
                f'      <line x1="{x}" y1="0" '
                f'x2="{x}" y2="{total_height}"/>'
            )

        # Horizontal lines (internal only, twice for double tracing)
        for i in range(1, grid_height):
            y = i * self.cell_size
            svg_lines.append(
                f'      <line x1="0" y1="{y}" '
                f'x2="{total_width}" y2="{y}"/>'
            )
            svg_lines.append(
                f'      <line x1="0" y1="{y}" '
                f'x2="{total_width}" y2="{y}"/>'
            )

        svg_lines.append('    </g>')
        return svg_lines

    def _generate_artwork_borders(self, grid_width: int, grid_height: int) -> List[str]:
        """Generate artwork borders: 6mm solid border + dashed cut line + interior cut lines.

        Args:
            grid_width: Width of grid in cells
            grid_height: Height of grid in cells

        Returns:
            List of SVG lines
        """
        total_width = grid_width * self.cell_size
        total_height = grid_height * self.cell_size

        # Convert margins to pixels
        border_margin_px = self._mm_to_px(6.0)  # 6mm solid border

        svg_lines = ['    <!-- Artwork borders -->']

        # Solid border 6mm outside the grid
        solid_x = -border_margin_px
        solid_y = -border_margin_px
        solid_width = total_width + 2 * border_margin_px
        solid_height = total_height + 2 * border_margin_px

        svg_lines.append(
            f'    <rect x="{solid_x:.2f}" y="{solid_y:.2f}" '
            f'width="{solid_width:.2f}" height="{solid_height:.2f}" '
            f'fill="none" stroke="black" stroke-width="1"/>'
        )

        # Dashed cut line - if dimensions provided, use them; otherwise calculate from border
        gap_px = self._mm_to_px(self.gap_in * self.MM_PER_INCH)

        if self.cut_line_width_mm is not None and self.cut_line_height_mm is not None:
            # Use specified cut line dimensions (frame dimensions)
            cut_width_px = self._mm_to_px(self.cut_line_width_mm)
            cut_height_px = self._mm_to_px(self.cut_line_height_mm)

            # Position cut line with gap on all edges
            # The cut line should be gap distance from the solid border
            cut_x = -border_margin_px - gap_px
            cut_y = -border_margin_px - gap_px
        else:
            # Default: use gap value outside the solid border
            cut_x = solid_x - gap_px
            cut_y = solid_y - gap_px
            cut_width_px = solid_width + 2 * gap_px
            cut_height_px = solid_height + 2 * gap_px

        svg_lines.append(
            f'    <rect x="{cut_x:.2f}" y="{cut_y:.2f}" '
            f'width="{cut_width_px:.2f}" height="{cut_height_px:.2f}" '
            f'fill="none" stroke="red" stroke-width="0.5" stroke-dasharray="5,5"/>'
        )

        # Interior cut lines for multi-panel artwork
        # These are vertical lines at the midpoint between adjacent panels
        if self.num_panels > 1 and self.frame_width_mm is not None:
            # Calculate the interior gap (space between solid borders of adjacent panels)
            # panel_width = (frame_width - 2*gap) / num_panels
            # solid_border_width = pattern_width + 2*border_margin
            # interior_gap = panel_width - solid_border_width
            frame_width_px = self._mm_to_px(self.frame_width_mm)
            panel_width_px = (frame_width_px - 2 * gap_px) / self.num_panels
            interior_gap_px = panel_width_px - solid_width

            # Cut line extends from top of solid border to bottom of solid border
            cut_line_top = solid_y
            cut_line_bottom = solid_y + solid_height

            svg_lines.append('    <!-- Interior cut lines -->')

            # Right cut line for this panel (at right edge of panel's allocation)
            # Position: solid_border_right + interior_gap/2
            right_cut_x = solid_x + solid_width + interior_gap_px / 2
            svg_lines.append(
                f'    <line x1="{right_cut_x:.2f}" y1="{cut_line_top:.2f}" '
                f'x2="{right_cut_x:.2f}" y2="{cut_line_bottom:.2f}" '
                f'stroke="red" stroke-width="0.5" stroke-dasharray="5,5"/>'
            )

            # Left cut line only for leftmost panel (highest index)
            if self.panel_index == self.num_panels - 1:
                left_cut_x = solid_x - interior_gap_px / 2
                svg_lines.append(
                    f'    <line x1="{left_cut_x:.2f}" y1="{cut_line_top:.2f}" '
                    f'x2="{left_cut_x:.2f}" y2="{cut_line_bottom:.2f}" '
                    f'stroke="red" stroke-width="0.5" stroke-dasharray="5,5"/>'
                )

        return svg_lines

    def _generate_empty_svg(self) -> str:
        """Generate SVG for an empty pattern.

        Returns:
            SVG file content as string
        """
        grid_size = self.cell_size * 10
        svg_width = grid_size + 2 * self.margin
        svg_height = grid_size + 2 * self.margin

        svg_width_mm = self._px_to_mm(svg_width)
        svg_height_mm = self._px_to_mm(svg_height)

        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width_mm:.2f}mm" height="{svg_height_mm:.2f}mm" viewBox="0 0 {svg_width} {svg_height}">
  <rect width="{svg_width}" height="{svg_height}" fill="white"/>
  <g transform="translate({self.margin}, {self.margin})">
    <rect width="{grid_size}" height="{grid_size}" fill="white" stroke="black" stroke-width="1"/>
    <text x="{grid_size//2}" y="{grid_size//2}" text-anchor="middle" font-family="Arial" font-size="14">Empty pattern</text>
  </g>
</svg>'''

    @classmethod
    def calculate_cell_size(
        cls,
        pattern_width: int,
        pattern_height: int,
        target_width_mm: Optional[float] = None,
        target_height_mm: Optional[float] = None,
        padding: int = 1,
        margin: float = 30.0
    ) -> float:
        """Calculate cell size to achieve target dimensions.

        Args:
            pattern_width: Width of pattern in cells
            pattern_height: Height of pattern in cells
            target_width_mm: Target width in mm (None = auto)
            target_height_mm: Target height in mm (None = auto)
            padding: Number of padding cells
            margin: Margin in pixels

        Returns:
            Cell size in pixels
        """
        if not target_width_mm and not target_height_mm:
            return 10.0

        grid_width = pattern_width + 2 * padding
        grid_height = pattern_height + 2 * padding

        cell_size = 10.0

        if target_width_mm:
            # Convert mm to pixels
            target_width_px = cls._mm_to_px(target_width_mm)
            cell_size_from_width = (target_width_px - 2 * margin) / grid_width
            cell_size = cell_size_from_width

        if target_height_mm:
            target_height_px = cls._mm_to_px(target_height_mm)
            cell_size_from_height = (target_height_px - 2 * margin) / grid_height

            # If both specified, use the smaller to ensure it fits
            if target_width_mm:
                cell_size = min(cell_size_from_width, cell_size_from_height)
            else:
                cell_size = cell_size_from_height

        return cell_size

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
