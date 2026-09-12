#!/usr/bin/env python3
"""Simplified Game of Life pattern processor for pen plotters.

This script processes RLE pattern files and generates 3×3 grid layouts
with crosshatched fills optimized for AxiDraw on Letter paper.
"""

import math
import subprocess
import sys
from pathlib import Path

from lifeplot import RLEParser, PatternEvolver, HatchGenerator, SVGGenerator, GridLayout, StandardPaperSizes
from lifeplot.game_of_life import table_from_hex


class Config:
    """Configuration for pattern processing."""

    def __init__(self, large_scale: bool = False, custom_dimensions: tuple[float, float] | None = None,
                 max_iterations: int | None = None, artwork_mode: bool = False, artwork_size: float | None = None,
                 artwork_preview: bool = False, artwork_preview_height: float | None = None,
                 artwork_preview_width: float | None = None, gap: float = 0.5, artwork_rows: int = 1,
                 standard_preview: bool = False, rule_table: list[int] | None = None):
        # Fixed hatch settings
        self.hatch_spacing = 1.0
        self.hatch_angle = 45.0
        self.output_dir = Path("output_patterns")

        # Optional 512-entry transition table for isotropic rules
        # (None = Conway's B3/S23); see lifeplot/game_of_life.py
        self.rule_table = rule_table

        # Custom dimensions (width_mm, height_mm) override grid layout
        self.custom_dimensions = custom_dimensions
        self.max_iterations = max_iterations

        # Artwork panel mode: generates individual panels with unified grid
        # artwork_size: size in mm for longest dimension (None = use default 3×3 grid pattern size)
        self.artwork_mode = artwork_mode
        self.artwork_size = artwork_size
        self.artwork_preview = artwork_preview
        # Preview dimensions in inches
        self.artwork_preview_height = artwork_preview_height
        self.artwork_preview_width = artwork_preview_width
        # Gap size in inches (used for all edges)
        self.gap = gap
        # Number of rows for artwork panel layout (1 = single row, 2+ = multi-row grid)
        self.artwork_rows = artwork_rows
        # Standard preview: auto-calculate preview dimensions from pattern geometry
        self.standard_preview = standard_preview

        # Grid layout options (fixed for AxiDraw Letter size)
        if large_scale:
            self.grid_rows = 2
            self.grid_cols = 2
            self.scale_factor = 1.25  # 25% larger patterns
        else:
            self.grid_rows = 3
            self.grid_cols = 3
            self.scale_factor = 1.0
        self.grid_start = 0  # Starting pattern index (0-based)
        self.grid_count = self.grid_rows * self.grid_cols  # Number of patterns to include in grid
        self.paper_size = "letter"  # Letter (8.5×11 inches)
        self.spacing_mm = 4.0  # Minimum spacing between pattern borders
        self.large_scale = large_scale


class PatternProcessor:
    """Processes Game of Life patterns and generates SVG output."""

    def __init__(self, config: Config):
        self.config = config

    def process_file(self, input_file: Path):
        """Process a single RLE file."""
        print(f"\nProcessing: {input_file}")

        # Parse RLE file
        with open(input_file, 'r') as f:
            rle_content = f.read()

        try:
            width, height, live_cells = RLEParser.parse(rle_content)
        except ValueError as e:
            print(f"  Error parsing {input_file}: {e}")
            return

        print(f"  Initial pattern: {len(live_cells)} live cells")

        # Create output directories
        base_name = input_file.stem
        pattern_dir = self.config.output_dir / base_name
        pattern_dir.mkdir(parents=True, exist_ok=True)

        rle_dir = pattern_dir / "rle"
        rle_dir.mkdir(exist_ok=True)

        svg_dir = pattern_dir / "svg"
        svg_dir.mkdir(exist_ok=True)

        # Evolve pattern first to find maximum bounds
        evolver = PatternEvolver(rule_table=self.config.rule_table)
        if self.config.max_iterations is not None:
            # Generate specific number of iterations
            generations = self._evolve_n_iterations(live_cells, self.config.max_iterations)
        else:
            # Evolve until repetition or death
            generations = evolver.evolve(live_cells)

        # Calculate cell size based on maximum bounds across all generations
        cell_size = self._calculate_cell_size_from_generations(generations)

        print(f"  Cell size: {cell_size:.2f} pixels")
        print(f"  Hatch spacing: {self.config.hatch_spacing} pixels")

        # Create generators
        hatch_gen = HatchGenerator(
            spacing=self.config.hatch_spacing,
            angle=self.config.hatch_angle,
            crosshatch=True,
            inset=0.5
        )

        # Pass border dimensions if custom dimensions specified
        if self.config.custom_dimensions is not None:
            svg_gen = SVGGenerator(
                cell_size=cell_size,
                padding=1,
                margin=0.0,
                show_grid=True,
                border_width_mm=self.config.custom_dimensions[0],
                border_height_mm=self.config.custom_dimensions[1]
            )
        else:
            svg_gen = SVGGenerator(
                cell_size=cell_size,
                padding=1,
                margin=0.0,
                show_grid=True
            )

        # Save each generation
        for gen_num, cells in enumerate(generations):
            # Save RLE
            rle_file = rle_dir / f"{base_name}_gen{gen_num:04d}.rle"
            with open(rle_file, 'w') as f:
                f.write(RLEParser.to_rle(cells, width, height))

            # Save SVG
            svg_file = svg_dir / f"{base_name}_gen{gen_num:04d}.svg"
            with open(svg_file, 'w') as f:
                f.write(svg_gen.generate(cells, hatch_gen))

            print(f"  Generation {gen_num}: {len(cells)} cells")

        # Report results
        period = 0
        if self.config.max_iterations is not None:
            print(f"  Generated {len(generations)} iterations (requested: {self.config.max_iterations})")
        else:
            period = evolver.get_period()
            if period == 0:
                print(f"  Pattern died out at generation {len(generations)}")
            elif period == 1:
                print(f"  Pattern is a still life (period 1)")
            else:
                print(f"  Pattern repeats with period {period}")

        print(f"  Total generations: {len(generations)}")
        print(f"  Files saved in: {pattern_dir}")

        # Create artwork panels if requested
        if self.config.artwork_mode:
            self._create_artwork_panels(generations, base_name, period)
        # Create all necessary grid layouts to cover all generations (unless custom dimensions)
        elif self.config.custom_dimensions is None:
            self._create_all_grid_layouts(pattern_dir / "svg", base_name, len(generations))
        else:
            print(f"\n  Skipping grid layout (custom dimensions: {self.config.custom_dimensions[0]}mm × {self.config.custom_dimensions[1]}mm)")

    def _create_all_grid_layouts(self, svg_dir: Path, base_name: str, total_generations: int):
        """Create all necessary grid layouts to cover all generations.

        Args:
            svg_dir: Directory containing SVG files
            base_name: Base name for output files
            total_generations: Total number of generations available
        """
        patterns_per_sheet = self.config.grid_rows * self.config.grid_cols
        num_sheets = (total_generations + patterns_per_sheet - 1) // patterns_per_sheet

        print(f"\nGenerating {num_sheets} sheet(s) to cover {total_generations} generations:")

        for sheet_num in range(num_sheets):
            start = sheet_num * patterns_per_sheet
            count = min(patterns_per_sheet, total_generations - start)

            # Temporarily override config for this sheet
            original_start = self.config.grid_start
            original_count = self.config.grid_count

            self.config.grid_start = start
            self.config.grid_count = count

            print(f"  Sheet {sheet_num + 1}: generations {start} to {start + count - 1}")
            self._create_grid_layout(svg_dir, base_name)

            # Restore original config
            self.config.grid_start = original_start
            self.config.grid_count = original_count

    def _create_grid_layout(self, svg_dir: Path, base_name: str):
        """Create grid layout from generated SVGs.

        Args:
            svg_dir: Directory containing SVG files
            base_name: Base name for output file
        """
        start = self.config.grid_start
        count = self.config.grid_count
        end = start + count
        
        print(f"\nCreating {self.config.grid_rows}×{self.config.grid_cols} grid layout...")
        print(f"  Using patterns {start} to {end-1}")

        # Get paper size
        try:
            paper_width_mm, paper_height_mm = StandardPaperSizes.get_size(self.config.paper_size)
        except ValueError:
            print(f"Unknown paper size: {self.config.paper_size}, using 11×14 inches")
            paper_width_mm, paper_height_mm = StandardPaperSizes.CUSTOM_11X14

        # Create grid layout with fixed spacing
        grid = GridLayout(
            rows=self.config.grid_rows,
            cols=self.config.grid_cols,
            paper_width_mm=paper_width_mm,
            paper_height_mm=paper_height_mm,
            min_spacing_mm=self.config.spacing_mm
        )

        # Get SVG files
        all_svg_files = sorted(svg_dir.glob(f"{base_name}_gen*.svg"))

        if not all_svg_files:
            print("  No SVG files found to create grid")
            return

        # Select subset of files based on start and count
        svg_files = all_svg_files[start:end]
        
        if not svg_files:
            print(f"  No SVG files found in range {start} to {end-1}")
            return

        # Output file - include range in filename if not using defaults
        if start == 0 and count == self.config.grid_rows * self.config.grid_cols:
            output_file = self.config.output_dir / base_name / f"{base_name}_grid_{self.config.grid_rows}x{self.config.grid_cols}.svg"
        else:
            output_file = self.config.output_dir / base_name / f"{base_name}_grid_{self.config.grid_rows}x{self.config.grid_cols}_{start}-{end-1}.svg"

        # Generate grid
        grid.generate(svg_files, output_file)

    def _evolve_n_iterations(self, initial_cells: set[tuple[int, int]], n: int) -> list[set[tuple[int, int]]]:
        """Evolve pattern for exactly N iterations.

        Args:
            initial_cells: Initial set of live cell coordinates
            n: Number of iterations to generate

        Returns:
            List of cell sets for each generation (including initial)
        """
        generations = [initial_cells]
        current_cells = initial_cells

        for _ in range(n):
            # If pattern died, stop generating
            if not current_cells:
                break
            current_cells = PatternEvolver._step(current_cells, self.config.rule_table)
            generations.append(current_cells)

        return generations

    def _calculate_cell_size_from_generations(self, generations: list[set[tuple[int, int]]]) -> float:
        """Calculate cell size based on maximum bounds across all generations."""
        if not generations:
            return 10.0

        # Find maximum bounds across all generations
        all_cells = set()
        for gen_cells in generations:
            all_cells.update(gen_cells)

        if not all_cells:
            return 10.0

        # If custom dimensions are specified, subtract 5mm margin on each side
        if self.config.custom_dimensions is not None:
            margin_mm = 5.0  # Same as grid cut line margin
            pattern_width_mm = self.config.custom_dimensions[0] - 2 * margin_mm
            pattern_height_mm = self.config.custom_dimensions[1] - 2 * margin_mm
            print(f"  SVG size: {self.config.custom_dimensions[0]:.2f}mm × {self.config.custom_dimensions[1]:.2f}mm")
            print(f"  Pattern area (with 5mm margin): {pattern_width_mm:.2f}mm × {pattern_height_mm:.2f}mm")
        else:
            # Get Letter paper size
            paper_width_mm, paper_height_mm = StandardPaperSizes.get_size(self.config.paper_size)

            # Always calculate based on 3×3 grid as baseline
            baseline_grid = GridLayout(
                rows=3,
                cols=3,
                paper_width_mm=paper_width_mm,
                paper_height_mm=paper_height_mm,
                min_spacing_mm=self.config.spacing_mm
            )

            pattern_width_mm, pattern_height_mm = baseline_grid.calculate_pattern_size()

            # Apply scale factor for large mode (25% larger)
            pattern_width_mm *= self.config.scale_factor
            pattern_height_mm *= self.config.scale_factor

            print(f"  Pattern size: {pattern_width_mm / 25.4:.2f}\" × {pattern_height_mm / 25.4:.2f}\" (scale: {self.config.scale_factor}x)")

        # Calculate pattern dimensions based on maximum bounds
        min_x = min(x for x, y in all_cells)
        max_x = max(x for x, y in all_cells)
        min_y = min(y for x, y in all_cells)
        max_y = max(y for x, y in all_cells)

        pattern_width = max_x - min_x + 1
        pattern_height = max_y - min_y + 1

        print(f"  Maximum pattern bounds: {pattern_width} × {pattern_height} cells")

        return SVGGenerator.calculate_cell_size(
            pattern_width, pattern_height,
            pattern_width_mm, pattern_height_mm,
            padding=1, margin=0.0
        )

    def _create_artwork_panels(self, generations: list[set[tuple[int, int]]], base_name: str,
                                period: int = 0):
        """Create artwork panels with unified grid across all generations.

        Each panel is a single-page SVG with the same grid dimensions, allowing
        the viewer to see how the pattern travels over time.

        Args:
            generations: List of cell sets for each generation
            base_name: Base name for output files
            period: Period of the pattern (to include final displaced generation)
        """
        if not generations:
            print("  No generations to create panels from")
            return

        # For periodic patterns, include the final generation to show displacement
        # The evolver stops before adding the repeated state, but we want to show
        # both start and end positions for artwork panels
        if period > 0 and len(generations) > 0:
            final_gen = PatternEvolver._step(generations[-1], self.config.rule_table)
            generations = list(generations) + [final_gen]

        # Calculate unified bounds across ALL generations
        all_cells = set()
        for gen_cells in generations:
            all_cells.update(gen_cells)

        if not all_cells:
            print("  No live cells across all generations")
            return

        min_x = min(x for x, y in all_cells)
        max_x = max(x for x, y in all_cells)
        min_y = min(y for x, y in all_cells)
        max_y = max(y for x, y in all_cells)

        unified_bounds = (min_x, min_y, max_x, max_y)
        pattern_width = max_x - min_x + 1
        pattern_height = max_y - min_y + 1

        # Grid dimensions with padding
        padding = 1
        grid_width = pattern_width + 2 * padding
        grid_height = pattern_height + 2 * padding

        print(f"\n  Artwork panels:")

        num_panels = len(generations)
        num_rows = self.config.artwork_rows
        num_cols = -(-num_panels // num_rows)

        # Check if explicit preview dimensions are specified - if so, derive panel size from them
        # (--standard computes its own dimensions after default cell size, so skip this path)
        if (self.config.artwork_preview_width is not None and
            self.config.artwork_preview_height is not None and
            not self.config.standard_preview):
            # Frame dimensions (cut line dimensions)
            frame_width_in = self.config.artwork_preview_width
            frame_height_in = self.config.artwork_preview_height

            # Gap on all edges and between panels
            gap_in = self.config.gap

            # Available space after all gaps (edge + inter-panel)
            available_width_in = frame_width_in - (num_cols + 1) * gap_in
            available_height_in = frame_height_in - (num_rows + 1) * gap_in

            panel_width_in = available_width_in / num_cols
            panel_height_in = available_height_in / num_rows

            # The pattern border (6mm solid border around grid)
            border_mm = 6.0

            # Grid area inside border — constrain cell size by both dimensions
            grid_area_width_mm = panel_width_in * 25.4 - 2 * border_mm
            grid_area_height_mm = panel_height_in * 25.4 - 2 * border_mm
            cell_size = min(
                SVGGenerator._mm_to_px(grid_area_width_mm) / grid_width,
                SVGGenerator._mm_to_px(grid_area_height_mm) / grid_height,
            )

            # Actual pattern dimensions based on cell size
            actual_pattern_width_mm = SVGGenerator._px_to_mm(grid_width * cell_size)

            # Cut line dimensions
            gap_mm = gap_in * 25.4
            cut_line_width_mm = actual_pattern_width_mm + 2 * border_mm + 2 * gap_mm
            cut_line_height_mm = frame_height_in * 25.4
            frame_width_mm = frame_width_in * 25.4

            print(f"    Frame: {frame_width_in}\" × {frame_height_in}\"")
            print(f"    Gap: {gap_in}\"")

            # Use Letter paper size for SVG background
            svg_width_mm, svg_height_mm = StandardPaperSizes.get_size(self.config.paper_size)
        elif self.config.artwork_size is not None:
            # User specified size for longest dimension - scale pattern to fit
            target_size_mm = self.config.artwork_size
            aspect_ratio = grid_width / grid_height
            if grid_width >= grid_height:
                target_pattern_width_mm = target_size_mm
                target_pattern_height_mm = target_size_mm / aspect_ratio
            else:
                target_pattern_height_mm = target_size_mm
                target_pattern_width_mm = target_size_mm * aspect_ratio

            # Calculate cell size to fit grid in target pattern area
            cell_size_from_width = SVGGenerator._mm_to_px(target_pattern_width_mm) / grid_width
            cell_size_from_height = SVGGenerator._mm_to_px(target_pattern_height_mm) / grid_height
            cell_size = min(cell_size_from_width, cell_size_from_height)

            # Use Letter paper size for SVG
            svg_width_mm, svg_height_mm = StandardPaperSizes.get_size(self.config.paper_size)

            # No custom cut line dimensions
            cut_line_width_mm = None
            cut_line_height_mm = None
            frame_width_mm = None
        else:
            # Default: same as single pattern in 3×3 grid
            paper_width_mm, paper_height_mm = StandardPaperSizes.get_size(self.config.paper_size)
            baseline_grid = GridLayout(
                rows=3, cols=3,
                paper_width_mm=paper_width_mm,
                paper_height_mm=paper_height_mm,
                min_spacing_mm=self.config.spacing_mm
            )
            target_pattern_width_mm, target_pattern_height_mm = baseline_grid.calculate_pattern_size()

            # Calculate cell size to fit grid in target pattern area
            cell_size_from_width = SVGGenerator._mm_to_px(target_pattern_width_mm) / grid_width
            cell_size_from_height = SVGGenerator._mm_to_px(target_pattern_height_mm) / grid_height
            cell_size = min(cell_size_from_width, cell_size_from_height)

            # Use Letter paper size for SVG
            svg_width_mm, svg_height_mm = paper_width_mm, paper_height_mm

            # No custom cut line dimensions
            cut_line_width_mm = None
            cut_line_height_mm = None
            frame_width_mm = None

        # For --standard: derive frame dimensions from the default cell size, snap to ¼"
        if self.config.standard_preview:
            border_mm = 6.0
            gap_in = self.config.gap

            # Panel dimensions from cell size
            panel_width_mm = SVGGenerator._px_to_mm(grid_width * cell_size) + 2 * border_mm
            panel_height_mm = SVGGenerator._px_to_mm(grid_height * cell_size) + 2 * border_mm
            panel_width_in = panel_width_mm / 25.4
            panel_height_in = panel_height_mm / 25.4

            # Natural frame from panels + requested gap
            natural_width = (num_cols + 1) * gap_in + num_cols * panel_width_in
            natural_height = (num_rows + 1) * gap_in + num_rows * panel_height_in

            # Snap frame to nearest quarter inch (ceiling)
            frame_width_in = math.ceil(natural_width * 4) / 4
            frame_height_in = math.ceil(natural_height * 4) / 4

            # Effective gap absorbs the rounding
            effective_gap_w = (frame_width_in - num_cols * panel_width_in) / (num_cols + 1)
            effective_gap_h = (frame_height_in - num_rows * panel_height_in) / (num_rows + 1)

            # Cut line dimensions
            gap_mm = gap_in * 25.4
            cut_line_width_mm = panel_width_mm + 2 * gap_mm
            cut_line_height_mm = frame_height_in * 25.4
            frame_width_mm = frame_width_in * 25.4

            self.config.artwork_preview_width = frame_width_in
            self.config.artwork_preview_height = frame_height_in

            print(f"    Panel: {panel_width_in:.2f}\" × {panel_height_in:.2f}\"")
            print(f"    Frame: {frame_width_in}\" × {frame_height_in}\"")
            print(f"    Gap: {effective_gap_w:.3f}\" (h) / {effective_gap_h:.3f}\" (v)")

        # Create output directory
        panels_dir = self.config.output_dir / base_name / "panels"
        panels_dir.mkdir(parents=True, exist_ok=True)

        # Create hatch generator
        hatch_gen = HatchGenerator(
            spacing=self.config.hatch_spacing,
            angle=self.config.hatch_angle,
            crosshatch=True,
            inset=0.5
        )

        # Generate each panel with its own SVG generator (for panel-specific cut lines)
        for gen_num, cells in enumerate(generations):
            # Create SVG generator with panel-specific parameters
            # panel_index matches gen_num: 0 = rightmost (gen 0), increases leftward
            svg_gen = SVGGenerator(
                cell_size=cell_size,
                padding=padding,
                margin=0.0,
                show_grid=True,
                border_width_mm=svg_width_mm,
                border_height_mm=svg_height_mm,
                unified_bounds=unified_bounds,
                show_artwork_borders=True,
                cut_line_width_mm=cut_line_width_mm,
                cut_line_height_mm=cut_line_height_mm,
                gap_in=self.config.gap,
                num_panels=num_panels,
                panel_index=gen_num,
                frame_width_mm=frame_width_mm
            )

            panel_file = panels_dir / f"{base_name}_panel_gen{gen_num:04d}.svg"
            with open(panel_file, 'w') as f:
                f.write(svg_gen.generate(cells, hatch_gen))

        print(f"    Generated {len(generations)} panels in: {panels_dir}")

        # Generate preview PNG if requested
        if self.config.artwork_preview:
            self._generate_artwork_preview(panels_dir, base_name, len(generations),
                                           generations, unified_bounds, padding)

    def _generate_artwork_preview(self, panels_dir: Path, base_name: str, num_panels: int,
                                    generations: list[set[tuple[int, int]]],
                                    unified_bounds: tuple[int, int, int, int], padding: int):
        """Generate a PNG preview showing all panels arranged in a grid.

        Uses Pillow to render solid black cells on grey background with grid.
        Panels are arranged last-to-first, left-to-right, top-to-bottom.

        Args:
            panels_dir: Directory containing panel SVG files
            base_name: Base name for output file
            num_panels: Number of panels to include
            generations: List of cell sets for each generation
            unified_bounds: (min_x, min_y, max_x, max_y) for the unified grid
            padding: Number of padding cells around pattern
        """
        try:
            from PIL import Image, ImageDraw
        except ImportError:
            print("      Pillow not installed - preview PNG not generated")
            print("      Install with: pip install Pillow")
            return

        print(f"\n    Generating preview PNG...")

        min_x, min_y, max_x, max_y = unified_bounds
        grid_width = (max_x - min_x + 1) + 2 * padding
        grid_height = (max_y - min_y + 1) + 2 * padding

        preview_dpi = 150  # DPI for calculating dimensions

        # Calculate grid layout (rows × cols)
        num_rows = self.config.artwork_rows
        num_cols = (num_panels + num_rows - 1) // num_rows  # Ceiling division

        print(f"      Layout: {num_rows} rows × {num_cols} columns")

        # Check if explicit dimensions provided (--standard sets these in _create_artwork_panels)

        if (self.config.artwork_preview_width is not None and
            self.config.artwork_preview_height is not None):
            # Frame dimensions (total dimensions)
            total_width = int(self.config.artwork_preview_width * preview_dpi)
            total_height = int(self.config.artwork_preview_height * preview_dpi)

            # Gap on all edges and between rows
            gap_in = self.config.gap
            gap_px = gap_in * preview_dpi

            # Available dimensions after all gaps (edge + inter-panel)
            available_width = total_width - (num_cols + 1) * gap_px
            available_height = total_height - (num_rows + 1) * gap_px

            # Panel dimensions: divide available space
            panel_width = available_width / num_cols
            panel_height = available_height / num_rows

            # Use 6mm border to match SVG
            border_mm = 6.0
            border_px = border_mm * preview_dpi / 25.4

            # Calculate cell size based on the smaller constraint
            cell_size_from_width = (panel_width - 2 * border_px) / grid_width
            cell_size_from_height = (panel_height - 2 * border_px) / grid_height
            cell_size_px = min(cell_size_from_width, cell_size_from_height)

            # No outer margin for this mode
            outer_margin = 0
            spacing_px = None  # Use gap_px instead

        else:
            # Use legacy scaling based on height only
            base_cell_size = 8   # Pixels per cell in preview
            base_spacing = 72    # ~1 inch between panels
            base_margin = 36     # Margin around all panels
            border_px = 2        # Simple visual border for legacy mode

            # Calculate base dimensions to determine scale factor
            base_panel_height = grid_height * base_cell_size + 2 * border_px
            base_total_height = base_panel_height * num_rows + base_spacing * (num_rows - 1) + 2 * base_margin

            # Scale everything if target height specified
            if self.config.artwork_preview_height is not None:
                target_height_px = self.config.artwork_preview_height * preview_dpi
                scale = target_height_px / base_total_height
            else:
                scale = 1.0

            # Apply scale to all dimensions
            cell_size_px = base_cell_size * scale
            spacing_px = base_spacing * scale
            outer_margin = base_margin * scale

            panel_width = grid_width * cell_size_px + 2 * border_px
            panel_height = grid_height * cell_size_px + 2 * border_px

            # Calculate content area (panels + spacing)
            content_width = panel_width * num_cols + spacing_px * (num_cols - 1)
            content_height = panel_height * num_rows + spacing_px * (num_rows - 1)

            # Total image size with margins
            total_width = int(content_width + 2 * outer_margin)
            total_height = int(content_height + 2 * outer_margin)
            gap_px = None  # Use spacing_px instead

        # Create charcoal background image
        bg_color = (54, 69, 79)  # Charcoal grey
        img = Image.new('RGB', (total_width, total_height), bg_color)
        draw = ImageDraw.Draw(img)

        # Content area starts after margin
        content_x = outer_margin
        content_y = outer_margin

        # Calculate actual grid size in pixels (may be smaller than panel due to aspect ratio)
        actual_grid_width_px = grid_width * cell_size_px + 2 * border_px
        actual_grid_height_px = grid_height * cell_size_px + 2 * border_px

        # Draw each panel (in reverse order: last generation first)
        # Layout: top-left is highest gen, reading left-to-right, top-to-bottom
        for panel_idx, gen_idx in enumerate(range(num_panels - 1, -1, -1)):
            if gen_idx >= len(generations):
                continue

            cells = generations[gen_idx]

            # Calculate row and column for this panel
            row = panel_idx // num_cols
            col = panel_idx % num_cols

            # Calculate slot position (the allocated space for this panel)
            if spacing_px is not None:
                # Legacy mode with spacing
                slot_x = content_x + col * (panel_width + spacing_px)
                slot_y = content_y + row * (panel_height + spacing_px)
                slot_width = panel_width
                slot_height = panel_height
            else:
                # New mode: gaps at frame edges and between rows
                slot_x = content_x + gap_px + col * (panel_width + gap_px)
                slot_y = content_y + gap_px + row * (panel_height + gap_px)
                slot_width = panel_width
                slot_height = panel_height

            # Center the actual grid within the slot
            x_offset = slot_x + (slot_width - actual_grid_width_px) / 2
            y_offset = slot_y + (slot_height - actual_grid_height_px) / 2

            # Draw white background only for actual grid area
            draw.rectangle(
                [x_offset, y_offset, x_offset + actual_grid_width_px - 1, y_offset + actual_grid_height_px - 1],
                fill='white', outline='white', width=max(1, int(border_px))
            )

            # Draw grid lines (black)
            grid_color = (0, 0, 0)
            grid_x_start = x_offset + border_px
            grid_y_start = y_offset + border_px

            # Vertical grid lines
            for gx in range(grid_width + 1):
                line_x = grid_x_start + gx * cell_size_px
                draw.line(
                    [(line_x, grid_y_start), (line_x, grid_y_start + grid_height * cell_size_px)],
                    fill=grid_color, width=1
                )

            # Horizontal grid lines
            for gy in range(grid_height + 1):
                line_y = grid_y_start + gy * cell_size_px
                draw.line(
                    [(grid_x_start, line_y), (grid_x_start + grid_width * cell_size_px, line_y)],
                    fill=grid_color, width=1
                )

            # Draw filled cells
            for cx, cy in cells:
                # Convert cell coordinates to pixel coordinates within panel
                grid_x = cx - min_x + padding
                grid_y = cy - min_y + padding

                px_x = x_offset + border_px + grid_x * cell_size_px
                px_y = y_offset + border_px + grid_y * cell_size_px

                draw.rectangle(
                    [px_x, px_y, px_x + cell_size_px - 1, px_y + cell_size_px - 1],
                    fill='black'
                )

        # Save PNG
        preview_png_path = panels_dir.parent / f"{base_name}_preview.png"
        img.save(preview_png_path)
        print(f"      Preview saved: {preview_png_path}")


def print_usage():
    """Print usage information."""
    print("Usage: python3 plot_life.py <input_file.rle> [output_directory] [options]")
    print("\nOptions:")
    print("  --large                2×2 grid (4 patterns per sheet, 25% larger patterns)")
    print("  --dimensions WxH       Custom dimensions in mm (e.g., 100x150)")
    print("                         Disables grid layout generation")
    print("  --iterations N         Generate exactly N iterations instead of evolving")
    print("                         until repetition or death")
    print("  --artwork [SIZE]       Generate artwork panels with unified grid")
    print("                         SIZE is optional longest dimension in mm")
    print("                         Default size matches 3×3 grid pattern size")
    print("                         Each panel shows one generation within a fixed grid")
    print("                         that encompasses all generations (shows travel)")
    print("  --standard             Auto-calculate preview dimensions from pattern geometry")
    print("                         Implies --preview. Uses 8\" frame height, derives width")
    print("                         from aspect ratio, panel count, rows, and gap")
    print("  --preview              Generate PNG preview of artwork panels")
    print("                         Shows all panels arranged last-to-first (left to right)")
    print("  --preview-height N     Set preview frame height to N inches")
    print("  --preview-width N      Set preview frame width to N inches")
    print("                         Both must be specified together for frame-based layout")
    print("                         Otherwise, only --preview-height scales proportionally")
    print("  --gap N                Set gap on all edges in inches (default: 0.5)")
    print("  --artwork-rows N       Arrange artwork panels in N rows (default: 1)")
    print("  --table HEX|FILE       512-entry transition table as 128 hex chars (or a")
    print("                         file containing them) for isotropic non-totalistic")
    print("                         rules; generated by the automons repo. Default: B3/S23")
    print("                         E.g., 8 panels with --artwork-rows 2 gives 2×4 grid")
    print("\nDescription:")
    print("  Processes RLE pattern files and generates grid layouts on Letter paper.")
    print("  Automatically creates multiple sheets to cover all generations until the")
    print("  pattern repeats or dies out.")
    print("  ")
    print("  Default: 3×3 grid (9 patterns per sheet)")
    print("  --large: 2×2 grid (4 patterns per sheet, 25% larger patterns)")
    print("  --artwork: Individual panels with unified coordinate system")
    print("  ")
    print("  Hatch spacing is fixed at 1 pixel, angle at 45 degrees.")
    print("  Cut lines are drawn 5mm from each pattern's border.")
    print("  Pattern size is auto-calculated to fit the grid with 4mm spacing.")
    print("\nExamples:")
    print("  python3 plot_life.py glider.rle")
    print("  python3 plot_life.py glider.rle output")
    print("  python3 plot_life.py glider.rle output --large")
    print("  python3 plot_life.py glider.rle output --dimensions 100x150")
    print("  python3 plot_life.py glider.rle output --iterations 50")
    print("  python3 plot_life.py glider.rle output --artwork")
    print("  python3 plot_life.py glider.rle output --artwork 150")
    print("  python3 plot_life.py glider.rle output --artwork --iterations 20")
    print("  python3 plot_life.py glider.rle output --artwork --preview")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    # Parse command-line arguments
    args = sys.argv[1:]

    if not args:
        print("Error: No input file specified")
        sys.exit(1)

    # Check for flags
    large_scale = False
    custom_dimensions = None
    max_iterations = None
    artwork_mode = False
    artwork_size = None
    artwork_preview = False
    artwork_preview_height = None
    artwork_preview_width = None
    gap = 0.5
    artwork_rows = 1
    standard_preview = False
    rule_table = None

    # Process flags
    i = 0
    while i < len(args):
        if args[i] == "--large":
            large_scale = True
            args.pop(i)
        elif args[i] == "--dimensions":
            if i + 1 >= len(args):
                print("Error: --dimensions requires a value (e.g., 100x150)")
                sys.exit(1)
            dim_str = args[i + 1]
            try:
                width_str, height_str = dim_str.lower().split('x')
                width = float(width_str)
                height = float(height_str)
                custom_dimensions = (width, height)
                args.pop(i)  # Remove --dimensions
                args.pop(i)  # Remove the value
            except (ValueError, AttributeError):
                print(f"Error: Invalid dimensions format '{dim_str}'. Use WIDTHxHEIGHT (e.g., 100x150)")
                sys.exit(1)
        elif args[i] == "--iterations":
            if i + 1 >= len(args):
                print("Error: --iterations requires a value (e.g., 50)")
                sys.exit(1)
            try:
                max_iterations = int(args[i + 1])
                if max_iterations < 0:
                    print("Error: --iterations must be a non-negative integer")
                    sys.exit(1)
                args.pop(i)  # Remove --iterations
                args.pop(i)  # Remove the value
            except ValueError:
                print(f"Error: Invalid iterations value '{args[i + 1]}'. Must be an integer")
                sys.exit(1)
        elif args[i] == "--artwork":
            artwork_mode = True
            args.pop(i)  # Remove --artwork
            # Check if next argument is a size (number, not another flag or file)
            if i < len(args) and not args[i].startswith('--') and not args[i].endswith('.rle'):
                try:
                    artwork_size = float(args[i])
                    if artwork_size <= 0:
                        print("Error: --artwork size must be a positive number")
                        sys.exit(1)
                    args.pop(i)  # Remove the size value
                except ValueError:
                    pass  # Not a number, leave it as a file path
        elif args[i] == "--preview":
            artwork_preview = True
            args.pop(i)
        elif args[i] == "--preview-height":
            if i + 1 >= len(args):
                print("Error: --preview-height requires a value")
                sys.exit(1)
            try:
                artwork_preview_height = float(args[i + 1])
                if artwork_preview_height <= 0:
                    print("Error: --preview-height must be a positive number")
                    sys.exit(1)
                args.pop(i)  # Remove --preview-height
                args.pop(i)  # Remove the value
            except ValueError:
                print(f"Error: Invalid preview-height value '{args[i + 1]}'. Must be a number")
                sys.exit(1)
        elif args[i] == "--preview-width":
            if i + 1 >= len(args):
                print("Error: --preview-width requires a value")
                sys.exit(1)
            try:
                artwork_preview_width = float(args[i + 1])
                if artwork_preview_width <= 0:
                    print("Error: --preview-width must be a positive number")
                    sys.exit(1)
                args.pop(i)  # Remove --preview-width
                args.pop(i)  # Remove the value
            except ValueError:
                print(f"Error: Invalid preview-width value '{args[i + 1]}'. Must be a number")
                sys.exit(1)
        elif args[i] == "--gap":
            if i + 1 >= len(args):
                print("Error: --gap requires a value")
                sys.exit(1)
            try:
                gap = float(args[i + 1])
                if gap < 0:
                    print("Error: --gap must be non-negative")
                    sys.exit(1)
                args.pop(i)  # Remove --gap
                args.pop(i)  # Remove the value
            except ValueError:
                print(f"Error: Invalid gap value '{args[i + 1]}'. Must be a number")
                sys.exit(1)
        elif args[i] == "--artwork-rows":
            if i + 1 >= len(args):
                print("Error: --artwork-rows requires a value")
                sys.exit(1)
            try:
                artwork_rows = int(args[i + 1])
                if artwork_rows < 1:
                    print("Error: --artwork-rows must be at least 1")
                    sys.exit(1)
                args.pop(i)  # Remove --artwork-rows
                args.pop(i)  # Remove the value
            except ValueError:
                print(f"Error: Invalid artwork-rows value '{args[i + 1]}'. Must be an integer")
                sys.exit(1)
        elif args[i] == "--standard":
            standard_preview = True
            artwork_preview = True
            args.pop(i)
        elif args[i] == "--table":
            if i + 1 >= len(args):
                print("Error: --table requires a value (128 hex chars, or a file containing them)")
                sys.exit(1)
            table_arg = args[i + 1]
            if Path(table_arg).exists():
                table_arg = Path(table_arg).read_text()
            try:
                rule_table = table_from_hex(table_arg)
            except ValueError as e:
                print(f"Error: Invalid --table value: {e}")
                sys.exit(1)
            args.pop(i)  # Remove --table
            args.pop(i)  # Remove the value
        else:
            i += 1

    config = Config(large_scale=large_scale, custom_dimensions=custom_dimensions,
                    max_iterations=max_iterations, artwork_mode=artwork_mode, artwork_size=artwork_size,
                    artwork_preview=artwork_preview, artwork_preview_height=artwork_preview_height,
                    artwork_preview_width=artwork_preview_width, gap=gap, artwork_rows=artwork_rows,
                    standard_preview=standard_preview, rule_table=rule_table)

    input_file = Path(args[0])
    if len(args) > 1:
        config.output_dir = Path(args[1])

    if not input_file.exists():
        print(f"Error: File '{input_file}' does not exist")
        sys.exit(1)

    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Print configuration
    if artwork_mode:
        print(f"Artwork Panel Configuration:")
        if artwork_size:
            print(f"  Panel size: {artwork_size}mm (longest dimension)")
        else:
            print(f"  Panel size: Default (same as 3×3 grid pattern)")
        print(f"  Output: Individual panels with unified grid")
        if artwork_preview:
            print(f"  Preview: PNG will be generated")
    elif custom_dimensions:
        print(f"Custom Dimensions Configuration:")
        print(f"  Pattern size: {custom_dimensions[0]}mm × {custom_dimensions[1]}mm")
    else:
        grid_desc = "2×2 (Large Scale, 25% bigger)" if large_scale else "3×3"
        print(f"{grid_desc} Grid Layout Configuration:")
        print(f"  Paper: Letter (8.5×11\")")
        print(f"  Grid spacing: {config.spacing_mm} mm")
        print(f"  Patterns per sheet: {config.grid_rows}×{config.grid_cols} = {config.grid_rows * config.grid_cols}")

    print(f"  Hatch spacing: {config.hatch_spacing} pixels")
    print(f"  Hatch angle: {config.hatch_angle} degrees")

    if max_iterations is not None:
        print(f"  Iterations: {max_iterations} (fixed)")
    else:
        print(f"  Iterations: Until repetition or death")

    # Process file
    processor = PatternProcessor(config)
    processor.process_file(input_file)

    print(f"\nProcessing complete. Output saved in: {config.output_dir}")


if __name__ == "__main__":
    main()
