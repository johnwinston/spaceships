"""RLE (Run Length Encoded) pattern parser for Game of Life.

This module handles parsing and serialization of RLE format files,
which are commonly used to represent Game of Life patterns.
"""

import re
from typing import Set, Tuple


class RLEParser:
    """Parser for RLE (Run Length Encoded) Game of Life patterns.

    RLE format is a compact way to represent Game of Life patterns.
    Format: x = width, y = height, rule = B3/S23
            pattern using: b (dead), o (alive), $ (newline), ! (end)
    """

    @staticmethod
    def parse(rle_content: str) -> Tuple[int, int, Set[Tuple[int, int]]]:
        """Parse RLE format and return dimensions and live cells.

        Args:
            rle_content: String containing RLE format pattern

        Returns:
            Tuple of (width, height, set of (x, y) coordinates for live cells)

        Raises:
            ValueError: If RLE format is invalid
        """
        lines = rle_content.strip().split('\n')

        # Find the header line with dimensions
        header = None
        for line in lines:
            if line.startswith('x') and '=' in line:
                header = line
                break

        if not header:
            raise ValueError("Could not find RLE header with dimensions")

        match = re.match(r'x\s*=\s*(\d+)\s*,\s*y\s*=\s*(\d+)', header)
        if not match:
            raise ValueError(f"Invalid RLE header: {header}")

        width = int(match.group(1))
        height = int(match.group(2))

        # Get pattern lines (skip comments and header)
        pattern_lines = []
        header_found = False
        for line in lines:
            if line.startswith('x') and '=' in line:
                header_found = True
                continue
            if header_found and line and not line.startswith('#'):
                pattern_lines.append(line.strip())

        pattern_str = ''.join(pattern_lines)

        live_cells = set()
        x, y = 0, 0
        i = 0

        while i < len(pattern_str):
            count_str = ''
            while i < len(pattern_str) and pattern_str[i].isdigit():
                count_str += pattern_str[i]
                i += 1

            count = int(count_str) if count_str else 1

            if i >= len(pattern_str):
                break

            tag = pattern_str[i]
            i += 1

            if tag == 'b':
                x += count
            elif tag == 'o':
                for _ in range(count):
                    live_cells.add((x, y))
                    x += 1
            elif tag == '$':
                x = 0
                y += count
            elif tag == '!':
                break

        return width, height, live_cells

    @staticmethod
    def to_rle(live_cells: Set[Tuple[int, int]],
               width: int = None,
               height: int = None) -> str:
        """Convert live cells back to RLE format.

        Args:
            live_cells: Set of (x, y) coordinates for live cells
            width: Optional width (auto-calculated if None)
            height: Optional height (auto-calculated if None)

        Returns:
            String in RLE format
        """
        if not live_cells:
            if width is None:
                width = 0
            if height is None:
                height = 0
            return f"x = {width}, y = {height}, rule = B3/S23\n!"

        min_x = min(x for x, y in live_cells)
        max_x = max(x for x, y in live_cells)
        min_y = min(y for x, y in live_cells)
        max_y = max(y for x, y in live_cells)

        # Normalize to origin
        normalized = {(x - min_x, y - min_y) for x, y in live_cells}
        actual_width = max_x - min_x + 1
        actual_height = max_y - min_y + 1

        header = f"x = {actual_width}, y = {actual_height}, rule = B3/S23"
        rle_lines = [header]
        rle_pattern = []

        for y in range(actual_height):
            x = 0
            line_content = []

            while x < actual_width:
                dead_count = 0
                while x < actual_width and (x, y) not in normalized:
                    dead_count += 1
                    x += 1

                if dead_count > 0:
                    if dead_count == 1:
                        line_content.append('b')
                    else:
                        line_content.append(f'{dead_count}b')

                live_count = 0
                while x < actual_width and (x, y) in normalized:
                    live_count += 1
                    x += 1

                if live_count > 0:
                    if live_count == 1:
                        line_content.append('o')
                    else:
                        line_content.append(f'{live_count}o')

            line_str = ''.join(line_content)
            rle_pattern.append(line_str)

            if y < actual_height - 1:
                rle_pattern.append('$')

        rle_pattern.append('!')

        # Format pattern string with line breaks at ~70 characters
        pattern_str = ''.join(rle_pattern)
        formatted_pattern = []
        line = ''
        for char in pattern_str:
            line += char
            if len(line) >= 70:
                formatted_pattern.append(line)
                line = ''
        if line:
            formatted_pattern.append(line)

        rle_lines.extend(formatted_pattern)
        return '\n'.join(rle_lines)
