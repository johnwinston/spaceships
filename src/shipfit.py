"""Card-fit geometry for the spaceship search.

ntzfind is told how wide to search; it decides how long the ship gets.
Left alone it will happily return something 12 cells wide and 40 long,
which lands on the card as a sliver.  This module turns the card's
printable box into the search bounds that produce card-shaped ships, and
grades what comes back.

Two ntzfind behaviours drive everything here.  Both are read off
``submodules/ntzfind/ntzfind.cpp`` rather than its help text, which is
ambiguous about which argument is measured in what:

* ``buffPattern`` prints the searched rows and then mirrors them about the
  centre column, so a ship's full width is a function of the ``w``
  argument *and* the symmetry flag -- ``2w`` for even, ``2w-1`` for odd,
  ``2w+1`` for gutter, plain ``w`` for asymmetric.
* ``buffPattern`` emits one line per ``period`` search rows and reports
  ``Length`` in search rows, so a ship's height in cells is
  ``(Length - 1) // period + 1``.  The ``m`` argument caps ``Length``
  (ntzfind.cpp backs up when ``currRow > m + 2*period - 1``), which makes
  ``m = height * period`` the knob for the long axis.

The printable box mirrors ``plot_svg.ship_layout``; the two are pinned
together by a test so they cannot drift apart.
"""
import math
import re
from collections import namedtuple

from . import config

# buffPattern() mirrors the searched rows about the centre column; how
# much it adds back depends on the symmetry flag.
_FULL_WIDTH = {
    "a": lambda w: w,
    "u": lambda w: 2 * w - 1,
    "v": lambda w: 2 * w,
    "g": lambda w: 2 * w + 1,
}

# A printed pattern row is dead/alive cells and nothing else.
_ROW_RE = re.compile(r"^[.o]+$")
_LENGTH_RE = re.compile(r"^Length:\s*(\d+)\s*$")

# plot_svg refuses to scale a cell past this, so a tiny ship floats in the
# middle of the card rather than becoming a poster.
MAX_CELL_MM = 8.0

ShipFit = namedtuple(
    "ShipFit", "rows width height cell_mm fill pop accepted"
)


def full_width(search_width, symmetry):
    """Ship width in cells for an ntzfind `w` argument and symmetry flag."""
    try:
        return _FULL_WIDTH[symmetry.lower()](search_width)
    except KeyError:
        raise ValueError(
            "unknown ntzfind symmetry flag %r (expected one of %s)"
            % (symmetry, ", ".join(sorted(_FULL_WIDTH)))
        )


def printable_box_mm():
    """The card area a ship may occupy, in mm -- matches plot_svg."""
    return (
        config.CARD_WIDTH_MM - 2 * config.CARD_MARGIN_MM,
        config.CARD_HEIGHT_MM - 2 * config.CARD_MARGIN_MM,
    )


def card_aspect():
    """Width:height of the printable box.  A ship matching this fills it."""
    box_w, box_h = printable_box_mm()
    return box_w / box_h


def height_band(ship_width, tolerance=None):
    """Heights whose aspect sits within `tolerance` of the card's.

    Returns an inclusive (min, max) in cells.  Widening the tolerance
    trades card coverage for how often a random rule yields a keeper.
    """
    if tolerance is None:
        tolerance = config.SEARCH_ASPECT_TOLERANCE
    aspect = card_aspect()
    low = ship_width / (aspect * (1.0 + tolerance))
    high = ship_width / (aspect * (1.0 - tolerance))
    return math.ceil(low), math.floor(high)


def max_length_arg(ship_width, period, tolerance=None):
    """The ntzfind `m` argument that stops the search overshooting.

    `m` caps the reported Length, and height is Length//period, so the
    tightest cap admitting the whole band is `max_height * period`.
    Passing this prunes over-long ships mid-walk instead of finding them
    and discarding them afterwards.
    """
    _, high = height_band(ship_width, tolerance)
    return max(1, high) * period


def cell_size_mm(grid_w, grid_h):
    """The cell size plot_svg will pick for a ship of this bounding box."""
    box_w, box_h = printable_box_mm()
    return min(box_w / grid_w, box_h / grid_h, MAX_CELL_MM)


def fill_fraction(grid_w, grid_h):
    """Share of the printable box the ship's bounding box will cover."""
    box_w, box_h = printable_box_mm()
    cell = cell_size_mm(grid_w, grid_h)
    return (grid_w * cell) * (grid_h * cell) / (box_w * box_h)


def bounding_box(rows):
    """Trim blank margins off a printed pattern.

    Returns (rows, width, height).  Only leading and trailing blank rows
    go -- an interior gap is part of the ship (two components flying in
    formation) and removing it would corrupt the pattern.
    """
    live = [i for i, row in enumerate(rows) if "o" in row]
    if not live:
        return [], 0, 0
    kept = rows[live[0]:live[-1] + 1]
    left = min(row.index("o") for row in kept if "o" in row)
    right = max(row.rindex("o") for row in kept if "o" in row)
    return [row[left:right + 1] for row in kept], right - left + 1, len(kept)


def iter_ships(stdout):
    """Yield (rows, length) for every confirmed ship in ntzfind's stdout.

    ntzfind prints the same block shape for a progress dump as for a real
    find -- the LWSS-hunting run that shaped this parser printed a pattern
    and a Length immediately before "0 spaceships found".  A block only
    counts once "Spaceship found." follows it.
    """
    pending = None
    rows = []
    for line in stdout.splitlines():
        line = line.strip()
        if _ROW_RE.match(line):
            rows.append(line)
            continue
        length = _LENGTH_RE.match(line)
        if length:
            pending = (rows, int(length.group(1)))
            rows = []
            continue
        if not line:
            continue
        if pending and line.startswith("Spaceship found."):
            yield pending
        pending = None
        rows = []


def evaluate(rows, tolerance=None, min_pop=None):
    """Grade a printed pattern against the card's printable box.

    Judged on the ship's real bounding box, not the nominal search width:
    a search `w` is an upper bound and ships routinely come back narrower.

    Acceptance needs both the right shape and enough live cells to read as
    solid.  The two are independent -- a sparse ship can sit dead on the
    card's aspect and still plot as scattered marks -- so neither check
    substitutes for the other.
    """
    if min_pop is None:
        min_pop = config.SEARCH_MIN_POPULATION
    trimmed, width, height = bounding_box(rows)
    if not trimmed:
        return ShipFit([], 0, 0, 0.0, 0.0, 0, False)
    low, high = height_band(width, tolerance)
    pop = sum(row.count("o") for row in trimmed)
    return ShipFit(
        trimmed,
        width,
        height,
        cell_size_mm(width, height),
        fill_fraction(width, height),
        pop,
        low <= height <= high and pop >= min_pop,
    )
