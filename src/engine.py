"""Pure-Python CA stepping driven by a 512-entry transition table.

Mirror of web/js/engine.js — used for tests and for drawing generation
trails in plot_svg.py.  Operates on sparse cell sets on an infinite plane.
"""
from .ruletable import NEIGH_ORDER


def step(cells, table):
    """Advance one generation.  cells: set of (x, y).  Returns a new set."""
    cells = set(cells)
    candidates = set(cells)
    for x, y in cells:
        for dx, dy in NEIGH_ORDER:
            candidates.add((x + dx, y + dy))
    nxt = set()
    for x, y in candidates:
        idx = 256 if (x, y) in cells else 0
        for i, (dx, dy) in enumerate(NEIGH_ORDER):
            if (x + dx, y + dy) in cells:
                idx |= 1 << i
        if table[idx]:
            nxt.add((x, y))
    return nxt


def run(cells, table, generations):
    """Yield the cell set at each generation, starting with generation 0."""
    current = set(cells)
    yield current
    for _ in range(generations):
        current = step(current, table)
        yield current
