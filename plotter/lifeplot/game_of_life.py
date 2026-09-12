"""Game of Life simulation engine.

This module implements Conway's Game of Life rules and pattern evolution.
Optionally, a 512-entry transition table drives any isotropic
(non-totalistic) rule instead — src/ruletable.py at the repo root
generates lifelib-verified tables and documents the layout mirrored
here.
"""

from typing import Set, Tuple, List, Optional

# Neighbour bit order for table-driven rules: N, NE, E, SE, S, SW, W, NW
# (bit i of the table index); index = centre * 256 + neighbour bits.
# Must match src/ruletable.py (repo root) exactly.
NEIGH_ORDER = [
    (0, -1), (1, -1), (1, 0), (1, 1),
    (0, 1), (-1, 1), (-1, 0), (-1, -1),
]


def table_from_hex(hex_str: str) -> List[int]:
    """Unpack 128 hex chars into a 512-entry 0/1 transition table.

    Bit j of the table lives in hex char j // 4 at position j % 4
    (little-endian nibbles) — the automons interchange format.
    """
    hex_str = hex_str.strip()
    if len(hex_str) != 128:
        raise ValueError(
            f"transition table must be 128 hex chars, got {len(hex_str)}"
        )
    table = [0] * 512
    for j, ch in enumerate(hex_str):
        nibble = int(ch, 16)
        for k in range(4):
            table[j * 4 + k] = (nibble >> k) & 1
    return table


class PatternEvolver:
    """Evolves Game of Life patterns through generations.

    Tracks pattern evolution and detects stable states (still lifes),
    oscillators, and other periodic patterns.
    """

    def __init__(self, max_generations: int = 10000,
                 rule_table: Optional[List[int]] = None):
        """Initialize the evolver.

        Args:
            max_generations: Maximum number of generations to simulate
            rule_table: Optional 512-entry transition table (see
                table_from_hex); None means Conway's B3/S23
        """
        self.max_generations = max_generations
        self.rule_table = rule_table
        self._seen_patterns = {}
        self._period = 0
        self._first_repeat = None

    def evolve(self, initial_cells: Set[Tuple[int, int]]) -> List[Set[Tuple[int, int]]]:
        """Evolve pattern until it repeats or dies.

        Args:
            initial_cells: Initial set of live cell coordinates

        Returns:
            List of cell sets for each generation (including initial)
        """
        generations = []
        current_cells = initial_cells
        self._seen_patterns = {}
        self._period = 0
        self._first_repeat = None

        for generation in range(self.max_generations + 1):
            # Normalize pattern for comparison
            normalized = self._normalize_pattern(current_cells)

            # Check if we've seen this pattern before
            if normalized in self._seen_patterns:
                self._period = generation - self._seen_patterns[normalized]
                self._first_repeat = self._seen_patterns[normalized]
                # Don't append the redundant final generation
                break

            # Record this pattern
            self._seen_patterns[normalized] = generation
            generations.append(current_cells)

            # Check if pattern died out
            if not current_cells:
                self._period = 0
                break

            # Advance to next generation
            current_cells = self._step(current_cells, self.rule_table)

        return generations

    def get_period(self) -> int:
        """Get the period of the last evolved pattern.

        Returns:
            Period (0 if died out, 1 if still life, N if oscillator with period N)
        """
        return self._period

    def get_first_repeat_generation(self) -> Optional[int]:
        """Get the generation number where the pattern first repeated.

        Returns:
            Generation number or None if pattern didn't repeat
        """
        return self._first_repeat

    @staticmethod
    def _step(live_cells: Set[Tuple[int, int]],
              rule_table: Optional[List[int]] = None) -> Set[Tuple[int, int]]:
        """Advance the pattern by one generation.

        Args:
            live_cells: Current set of live cells
            rule_table: Optional 512-entry transition table; None means
                Conway's B3/S23

        Returns:
            Next generation of live cells
        """
        cells_to_check = set()
        for x, y in live_cells:
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    cells_to_check.add((x + dx, y + dy))

        if rule_table is not None:
            # Table-driven isotropic rule (mirrors the automons engine)
            next_generation = set()
            for x, y in cells_to_check:
                idx = 256 if (x, y) in live_cells else 0
                for i, (dx, dy) in enumerate(NEIGH_ORDER):
                    if (x + dx, y + dy) in live_cells:
                        idx |= 1 << i
                if rule_table[idx]:
                    next_generation.add((x, y))
            return next_generation

        next_generation = set()

        for x, y in cells_to_check:
            neighbor_count = 0
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if dx == 0 and dy == 0:
                        continue
                    if (x + dx, y + dy) in live_cells:
                        neighbor_count += 1

            is_alive = (x, y) in live_cells

            # Conway's Game of Life rules:
            # - Live cell with 2-3 neighbors survives
            # - Dead cell with exactly 3 neighbors becomes alive
            if is_alive and neighbor_count in [2, 3]:
                next_generation.add((x, y))
            elif not is_alive and neighbor_count == 3:
                next_generation.add((x, y))

        return next_generation

    @staticmethod
    def _normalize_pattern(live_cells: Set[Tuple[int, int]]) -> frozenset:
        """Normalize pattern to origin for comparison.

        Args:
            live_cells: Set of live cell coordinates

        Returns:
            Frozenset of normalized coordinates
        """
        if not live_cells:
            return frozenset()

        min_x = min(x for x, y in live_cells)
        min_y = min(y for x, y in live_cells)

        return frozenset((x - min_x, y - min_y) for x, y in live_cells)
