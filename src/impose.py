"""Gang card faces onto plotter sheets.

plot_svg draws one card per SVG; a booth's worth of cards is plotted in
sheets.  This module places a grid of cards butted edge to edge on the
stock (3x3 on Letter by default -- the largest block the AxiDraw V3's
300x218 mm travel takes; 4x4 needs A3-class stock and machine) and --
the part that actually saves time at the machine -- merges
layers *across* cards rather than concatenating cards: one sheet-level
"ship" layer holds all sixteen ships, so a 4-pen front sheet costs 4 pen
swaps instead of 64.

Backs are the same grid mirrored left-right (position only, content
upright): plot the fronts, flip the stock about its long edge, plot the
backs, and each QR lands behind its own ship.

Butted cards share cut lines, so a "cuts" layer marks the grid's 3+3
interior lines plus the outer rectangle -- straight trimmer passes.  It
is a layer like any other so the plotting step can skip it or draw it in
pencil.

Usage:
    python -m src.impose --periods 4 5 6 7 --trail 3
    python -m src.impose --periods 4 5 6 7 --paper 11x17 --out plots/sheets

Reads data/<p>/patterns.json (rle2apgcode output) and web/catalog.json
(build_catalog output; supplies each rule's transition table so trails
need no lifelib here).  Writes sheet_NN_front.svg / sheet_NN_back.svg.
"""
import argparse
import json
import os

from . import config
from . import plot_svg
from .hatching import HatchGenerator
from . import rle as rle_codec
from . import ruletable
from . import shipurl
from . import stroke_font
from . import claimcode

PAPERS_MM = {
    "a3": (297.0, 420.0),
    "11x17": (279.4, 431.8),
    "a4": (210.0, 297.0),
    "letter": (215.9, 279.4),
}

# Imposition grid (columns x rows of cards).  A 4x4 block needs A3-class
# stock and an A3-class machine; the AxiDraw V3 on the desk has 300 x 218
# mm of pen travel, which takes Letter/A4 *landscape* -- so 3x3 on Letter
# (block 190.5 x 266.7 mm) is the layout that actually plots there, and
# main() defaults to it.  Library callers get 4x4 unless they say
# otherwise.
DEFAULT_GRID = (4, 4)

# Layer stacks, bottom to top -- one pen each.
#
# "hatched" is the original plotted look (johnwinston/plotter): graph-paper
# grid over the pattern's bounding box, live cells crosshatched, all cells
# identical.  "trails" is plot_svg's outline style with motion-trail pens.
STYLE_LAYERS = {
    # No card frame on the hatched cards: the only edge the pen sees is the
    # (optional) red cut line, so a trimmed card shows grid, hatch, labels
    # and nothing else.
    "hatched": ("grid", "hatch", "label"),
    "trails": ("frame", "trail-gen3", "trail-gen2", "trail-gen1", "ship"),
}

# The original cards were hatched at spacing 1.0 / inset 0.5 with a cell
# of ~3.6 units; carrying the look over means preserving those ratios,
# not the absolute numbers.

# Every hatched card shares one grid: config.CARD_GRID_BOX cells for the
# ship, GRID_PADDING empty cells all round, and a label band underneath.
# Same cell size and same box on every card -- the ship is centred in the
# box, and a ship that doesn't fit the box doesn't fit the deck.
GRID_PADDING = 1
# The G4G cards' hatch settings (plotter/plot_life.py): spacing was a
# FIXED 1.0 px (25.4/96 mm) with a 0.5 px inset, independent of cell
# size.  At a 0.35 mm pen that spacing is below the pen width, so cells
# read as solid black with a crosshatch sheen.
HATCH_SPACING_MM = 25.4 / 96
HATCH_INSET_MM = 25.4 / 192
HATCH_ANGLE_DEG = 45.0


class ShipTooBig(ValueError):
    """The ship's bounding box exceeds the common card box."""


def ship_extent(cells):
    """(width, height) of the ship's bounding box in cells."""
    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    return max(xs) - min(xs) + 1, max(ys) - min(ys) + 1


def fits_box(cells, box=None):
    bw, bh = box or config.CARD_GRID_BOX
    w, h = ship_extent(cells)
    return w <= bw and h <= bh


def parse_box(text):
    """'16x25' -> (16, 25)."""
    try:
        w, h = (int(v) for v in text.lower().split("x"))
    except ValueError:
        raise ValueError("box must look like WIDTHxHEIGHT, e.g. 16x25, not %r" % (text,))
    if w < 1 or h < 1:
        raise ValueError("box dimensions must be positive, not %r" % (text,))
    return w, h


def sheet_geometry(paper, grid=DEFAULT_GRID):
    """Origin and size of the butted card block, centred on the sheet."""
    try:
        paper_w, paper_h = PAPERS_MM[paper]
    except KeyError:
        raise ValueError(
            "unknown paper %r (expected one of %s)"
            % (paper, ", ".join(sorted(PAPERS_MM)))
        )
    cols, rows = grid
    block_w = cols * config.CARD_WIDTH_MM
    block_h = rows * config.CARD_HEIGHT_MM
    if block_w > paper_w or block_h > paper_h:
        raise ValueError("%dx%d card block exceeds %s stock" % (cols, rows, paper))
    return (paper_w - block_w) / 2, (paper_h - block_h) / 2, paper_w, paper_h


def slot_origin(slot, paper, mirrored=False, grid=DEFAULT_GRID):
    """Top-left mm of a card slot (row-major from 0).

    mirrored flips the column only: the sheet is turned over about its
    long edge for the backs, so columns reverse and rows stay.
    """
    cols, _ = grid
    row, col = divmod(slot, cols)
    if mirrored:
        col = cols - 1 - col
    ox, oy, _, _ = sheet_geometry(paper, grid)
    return (
        ox + col * config.CARD_WIDTH_MM,
        oy + row * config.CARD_HEIGHT_MM,
    )


def cut_lines_path(paper, grid=DEFAULT_GRID):
    """Shared cut lines: outer rectangle plus interior grid lines."""
    cols, rows = grid
    ox, oy, _, _ = sheet_geometry(paper, grid)
    block_w = cols * config.CARD_WIDTH_MM
    block_h = rows * config.CARD_HEIGHT_MM
    parts = ["M%g %gh%gv%gh%gz" % (ox, oy, block_w, block_h, -block_w)]
    for col in range(1, cols):
        x = ox + col * config.CARD_WIDTH_MM
        parts.append("M%g %gv%g" % (x, oy, block_h))
    for row in range(1, rows):
        y = oy + row * config.CARD_HEIGHT_MM
        parts.append("M%g %gh%g" % (ox, y, block_w))
    return '<path d="%s"/>' % "".join(parts)


def _hatched_card_layout(cells, box=None):
    """Common-grid placement.

    The grid is a fixed box of ``box`` cells (default config.CARD_GRID_BOX)
    plus GRID_PADDING empty cells all round, so every card has the same
    cell size and the same graph paper.  The ship is centred in the box on
    whole cells; the grid-plus-label-band block is centred in the card's
    printable area.  Returns (cells, grid_w, grid_h, ox, oy, cell_mm) with
    cells already shifted into grid coordinates (padding excluded).

    Raises ShipTooBig when the ship's bounding box exceeds the box.
    """
    bw, bh = box or config.CARD_GRID_BOX
    w, h = ship_extent(cells)
    if w > bw or h > bh:
        raise ShipTooBig("ship is %dx%d cells; card box is %dx%d" % (w, h, bw, bh))
    min_x = min(x for x, _ in cells)
    min_y = min(y for _, y in cells)
    dx = (bw - w) // 2
    dy = (bh - h) // 2
    cells = {(x - min_x + dx, y - min_y + dy) for x, y in cells}
    grid_w = bw + 2 * GRID_PADDING
    grid_h = bh + 2 * GRID_PADDING
    avail_w = config.CARD_WIDTH_MM - 2 * config.CARD_MARGIN_MM
    avail_h = (config.CARD_HEIGHT_MM - 2 * config.CARD_MARGIN_MM
               - config.CARD_LABEL_BAND_MM)
    cell_mm = min(avail_w / grid_w, avail_h / grid_h, 8.0)
    block_h = grid_h * cell_mm + config.CARD_LABEL_BAND_MM
    ox = (config.CARD_WIDTH_MM - grid_w * cell_mm) / 2
    oy = (config.CARD_HEIGHT_MM - block_h) / 2
    return cells, grid_w, grid_h, ox, oy, cell_mm


def _grid_lines_path(grid_w, grid_h, ox, oy, cell_mm, traces=2):
    """Graph-paper grid over the padded box.  traces=2 (the default)
    draws every line twice for a heavier weight, as the original cards
    did -- as ONE down-and-back stroke per line, so the pen always runs
    the full length of a line and only turns at its ends.  traces=1
    halves the grid's pen time at the cost of a lighter line."""
    w, h = grid_w * cell_mm, grid_h * cell_mm
    parts = []
    for i in range(grid_w + 1):
        x = ox + i * cell_mm
        parts.append("M%g %gv%gv%g" % (x, oy, h, -h) if traces == 2
                     else "M%g %gv%g" % (x, oy, h))
    for j in range(grid_h + 1):
        y = oy + j * cell_mm
        parts.append("M%g %gh%gh%g" % (ox, y, w, -w) if traces == 2
                     else "M%g %gh%g" % (ox, y, w))
    return '<path d="%s"/>' % "".join(parts)


def _label_path(labels, grid_w, grid_h, ox, oy, cell_mm):
    """Stroke-font text under the grid: left label flush with the grid's
    left edge, right label flush with its right edge, one baseline."""
    left, right = labels
    baseline = oy + grid_h * cell_mm + config.CARD_LABEL_BASELINE_MM
    cap = config.CARD_LABEL_CAP_MM
    d = ""
    if left:
        d += stroke_font.text_path_d(left, ox, baseline, cap)
    if right:
        d += stroke_font.text_path_d(
            right, ox + grid_w * cell_mm, baseline, cap, align="right"
        )
    return '<path d="%s"/>' % d if d else None


def paths_to_d(paths):
    """Serialize HatchGenerator command tuples into one SVG path d."""
    parts = []
    for path in paths:
        for cmd in path:
            if cmd[0] == "M":
                parts.append("M%g %g" % (cmd[1], cmd[2]))
            elif cmd[0] == "L":
                parts.append("L%g %g" % (cmd[1], cmd[2]))
            elif cmd[0] == "C":
                parts.append("C%g %g %g %g %g %g" % cmd[1:7])
    return "".join(parts)


def _cell_stroke_d(paths, rect, pen_mm):
    """One continuous stroke filling a cell: its crosshatch (chained
    pen-down) followed by a perimeter trace inset half a pen width, so
    edges and corners get solid ink instead of relying on the short
    corner slivers of the 45-degree hatch."""
    parts = []
    first = True
    for path in paths:
        for cmd in path:
            if cmd[0] == "M":
                parts.append(("M" if first else "L") + "%g %g" % (cmd[1], cmd[2]))
                first = False
            elif cmd[0] == "L":
                parts.append("L%g %g" % (cmd[1], cmd[2]))
            elif cmd[0] == "C":
                parts.append("C%g %g %g %g %g %g" % cmd[1:7])
    x, y, w, h = rect
    e = pen_mm / 2
    ring = [(x + e, y + e), (x + w - e, y + e), (x + w - e, y + h - e),
            (x + e, y + h - e), (x + e, y + e)]
    parts.append(("M" if first else "L") + "%g %g" % ring[0])
    for px, py in ring[1:]:
        parts.append("L%g %g" % (px, py))
    return "".join(parts)


def _card_front_layers_hatched(cells, labels=None, box=None, grid_traces=2):
    cells, grid_w, grid_h, ox, oy, cell_mm = _hatched_card_layout(cells, box)
    # G4G density (fixed 1 px spacing), but ONE stroke per cell: the
    # plotter's sorter reorders whole strokes, so per-cell strokes make
    # the pen finish each cell before hopping to the nearest next one
    # instead of wandering along cross-card chains.
    spacing = HATCH_SPACING_MM
    hatcher = HatchGenerator(
        spacing=spacing,
        angle=HATCH_ANGLE_DEG,
        crosshatch=True,
        inset=HATCH_INSET_MM,
    )
    pen = config.PEN_WIDTH_MM
    cell_ds = []
    for x, y in sorted(cells):
        rect = (ox + (x + GRID_PADDING) * cell_mm,
                oy + (y + GRID_PADDING) * cell_mm, cell_mm, cell_mm)
        paths = hatcher.generate_for_rectangles(
            [rect], connect_segments=True, connection_radius=3.0 * spacing
        )
        cell_ds.append(_cell_stroke_d(paths, rect, pen))
    layers = {
        "grid": _grid_lines_path(grid_w, grid_h, ox, oy, cell_mm, traces=grid_traces),
        "hatch": '<path d="%s"/>' % "".join(cell_ds),
    }
    label = _label_path(labels, grid_w, grid_h, ox, oy, cell_mm) if labels else None
    if label:
        layers["label"] = label
    return layers


def _card_front_layers_trails(cells, table, trail):
    """plot_svg.card_front_svg geometry, unwrapped for cross-card merge."""
    generations, ox, oy, cell_mm = plot_svg.ship_layout(
        cells, trail if table else 0, table or [0] * 512
    )
    layers = {"frame": plot_svg.card_frame_path()}
    for g, gen_cells in enumerate(generations[1:], start=1):
        inset = 0.25 * g * cell_mm / max(len(generations), 1)
        layers["trail-gen%d" % g] = plot_svg._cells_path(
            gen_cells, ox, oy, cell_mm, inset_mm=inset
        )
    layers["ship"] = plot_svg._cells_path(generations[0], ox, oy, cell_mm)
    return layers


def _placed(content, x, y):
    return '<g transform="translate(%g %g)">%s</g>' % (x, y, content)


def front_sheet_svg(cards, paper="a3", trail=0, style="hatched", box=None,
                    grid=DEFAULT_GRID, grid_traces=2):
    """One front sheet.  cards: list of dicts with cells/table (at most
    cols*rows); an optional "labels" pair is plotted under the grid."""
    per_sheet = grid[0] * grid[1]
    if len(cards) > per_sheet:
        raise ValueError("a sheet holds %d cards, got %d" % (per_sheet, len(cards)))
    try:
        layer_order = STYLE_LAYERS[style]
    except KeyError:
        raise ValueError(
            "unknown style %r (expected one of %s)"
            % (style, ", ".join(sorted(STYLE_LAYERS)))
        )
    _, _, paper_w, paper_h = sheet_geometry(paper, grid)
    per_layer = {name: [] for name in layer_order}
    for slot, card in enumerate(cards):
        x, y = slot_origin(slot, paper, grid=grid)
        if style == "hatched":
            layers = _card_front_layers_hatched(
                card["cells"], card.get("labels"), box, grid_traces
            )
        else:
            layers = _card_front_layers_trails(
                card["cells"], card.get("table"), trail
            )
        for name, content in layers.items():
            per_layer[name].append(_placed(content, x, y))
    svg = [plot_svg._svg_header(paper_w, paper_h)]
    for name in layer_order:
        if not per_layer[name]:
            continue
        stroke = "silver" if name.startswith("trail") else "black"
        svg.append(plot_svg._layer(name, "".join(per_layer[name]), stroke=stroke))
    svg.append(plot_svg._layer("cuts", cut_lines_path(paper, grid), stroke="red"))
    svg.append("</svg>")
    return "".join(svg)


def back_sheet_svg(cards, paper="a3", grid=DEFAULT_GRID):
    """Matching back sheet: QR hatching, columns mirrored for the flip,
    and each card's claim code under its QR when the deck carries one."""
    per_sheet = grid[0] * grid[1]
    if len(cards) > per_sheet:
        raise ValueError("a sheet holds %d cards, got %d" % (per_sheet, len(cards)))
    _, _, paper_w, paper_h = sheet_geometry(paper, grid)
    frames, qrs, codes = [], [], []
    for slot, card in enumerate(cards):
        x, y = slot_origin(slot, paper, mirrored=True, grid=grid)
        frames.append(_placed(plot_svg.card_frame_path(), x, y))
        matrix, module_mm, qx, qy, quiet_mm = plot_svg.back_geometry(card["url"])
        qrs.append(_placed(
            plot_svg.qr_hatch_path(
                matrix, qx, qy, module_mm, config.PEN_WIDTH_MM
            ),
            x, y,
        ))
        if card.get("code"):
            codes.append(_placed(
                '<path d="%s"/>' % plot_svg.claim_code_path_d(card["code"], qy, quiet_mm),
                x, y,
            ))
    svg = [plot_svg._svg_header(paper_w, paper_h)]
    svg.append(plot_svg._layer("frame", "".join(frames)))
    svg.append(
        '<g inkscape:groupmode="layer" inkscape:label="qr" '
        'fill="none" stroke="black" stroke-width="%g" '
        'stroke-linecap="butt">%s</g>'
        % (config.PEN_WIDTH_MM, "".join(qrs))
    )
    if codes:
        svg.append(plot_svg._layer("claim", "".join(codes)))
    svg.append(plot_svg._layer("cuts", cut_lines_path(paper, grid), stroke="red"))
    svg.append("</svg>")
    return "".join(svg)


def load_deck(periods):
    """Card dicts for every ship in the given periods, in edition order.

    Reads web/catalog.json (build_deck output).  Edition order is the
    curated order ids were assigned in, so sheet numbering is stable and
    final as long as the deck doesn't change.
    """
    with open(os.path.join("web", "catalog.json")) as f:
        catalog = json.load(f)
    wanted = {str(p) for p in periods}
    entries = sorted(
        (entry["edition"], ship_id, entry)
        for ship_id, entry in catalog.items()
        if entry.get("edition") and entry.get("period") in wanted
    )
    # Cards are numbered within their period ("1 of 45"): position in
    # edition order among ships of the same period, out of that period's
    # total in the deck.
    per_period = {}
    for _, _, entry in entries:
        per_period[entry["period"]] = per_period.get(entry["period"], 0) + 1
    secret = claimcode.claim_secret(required=False)
    deck = []
    seen = {}
    for edition, ship_id, entry in entries:
        period = entry["period"]
        seen[period] = seen.get(period, 0) + 1
        cells, _ = rle_codec.parse(entry["rle"])
        deck.append({
            "id": ship_id,
            "edition": edition,
            "period": period,
            "cells": cells,
            "table": ruletable.table_from_hex(entry["table"])
                     if entry.get("table") else None,
            "url": shipurl.player_url(ship_id=ship_id),
            "code": claimcode.claim_code(ship_id, secret) if secret else None,
            "labels": card_labels(period, seen[period], per_period[period]),
        })
    return deck


def card_labels(period, index, count):
    """(bottom-left, bottom-right) text for a card: its period, and its
    number among the deck's ships of that period."""
    return ("Period %s" % period, "%d of %d" % (index, count))


def split_by_fit(deck, box=None):
    """(fits, misfits): cards whose ship fits the common box, and those
    that don't and so can't go on the sheets."""
    fits = [card for card in deck if fits_box(card["cells"], box)]
    misfits = [card for card in deck if not fits_box(card["cells"], box)]
    return fits, misfits


def sheets_of(deck, grid=DEFAULT_GRID):
    per_sheet = grid[0] * grid[1]
    return [deck[i:i + per_sheet] for i in range(0, len(deck), per_sheet)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periods", nargs="+", required=True)
    parser.add_argument("--paper", default="letter", choices=sorted(PAPERS_MM))
    parser.add_argument(
        "--grid-traces", type=int, default=2, choices=(1, 2),
        help="times each grid line is drawn (2 = heavier line, the "
             "original look; 1 saves ~20 min of pen time per 3x3 sheet)",
    )
    parser.add_argument(
        "--grid", default="3x3",
        help="cards per sheet as COLSxROWS (default 3x3: the largest block "
             "that fits Letter/A4 stock and the AxiDraw V3's 300x218 mm "
             "travel; 4x4 needs A3-class stock and machine)",
    )
    parser.add_argument("--style", default="hatched", choices=sorted(STYLE_LAYERS))
    parser.add_argument("--trail", type=int, default=0)
    parser.add_argument("--out", default=os.path.join("plots", "sheets"))
    parser.add_argument(
        "--box", default=None,
        help="common card box in cells, WIDTHxHEIGHT (default %dx%d from "
             "config.CARD_GRID_BOX); ships that don't fit are left off"
             % config.CARD_GRID_BOX,
    )
    args = parser.parse_args()

    box = parse_box(args.box) if args.box else config.CARD_GRID_BOX
    grid = parse_box(args.grid)
    sheet_geometry(args.paper, grid)  # fail fast if the block exceeds the stock
    full_deck = load_deck(args.periods)
    if full_deck and not full_deck[0].get("code"):
        print("note: %s not set -- backs will carry no claim code"
              % config.CLAIM_SECRET_ENV)
    if args.style == "hatched":
        deck, misfits = split_by_fit(full_deck, box)
        if deck:
            _, grid_w, grid_h, _, _, cell_mm = _hatched_card_layout(deck[0]["cells"], box)
            print("card grid: %dx%d box + %d padding = %dx%d cells at %.2f mm"
                  % (box[0], box[1], GRID_PADDING, grid_w, grid_h, cell_mm))
        if misfits:
            print("%d of %d ships exceed the %dx%d box and are NOT on the sheets "
                  "(find replacements that fit):"
                  % (len(misfits), len(deck) + len(misfits), box[0], box[1]))
            for card in misfits:
                w, h = ship_extent(card["cells"])
                print("  %-8s %2dx%-2d" % (card["id"], w, h))
    else:
        deck = full_deck  # trails style sizes each card on its own
    os.makedirs(args.out, exist_ok=True)
    print("imposing %dx%d on %s" % (grid[0], grid[1], args.paper))
    for num, cards in enumerate(sheets_of(deck, grid), start=1):
        front = front_sheet_svg(
            cards, paper=args.paper, trail=args.trail, style=args.style, box=box,
            grid=grid, grid_traces=args.grid_traces,
        )
        back = back_sheet_svg(cards, paper=args.paper, grid=grid)
        fp = os.path.join(args.out, "sheet_%02d_front.svg" % num)
        bp = os.path.join(args.out, "sheet_%02d_back.svg" % num)
        with open(fp, "w") as f:
            f.write(front)
        with open(bp, "w") as f:
            f.write(back)
        missing = sum(1 for c in cards if c["table"] is None)
        note = " (%d cards without tables: no trails)" % missing if missing else ""
        print("sheet %02d: %d cards -> %s, %s%s" % (num, len(cards), fp, bp, note))


if __name__ == "__main__":
    main()
