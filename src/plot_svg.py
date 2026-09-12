"""Plotter-ready SVG card faces.

Replaces the raster card pipeline (combine.py) for the pen-plotted
edition: everything is stroke-only vector geometry in real millimetres,
sized for a standard poker card (see config.py).

Front: the spaceship's live cells as outlined squares, optionally with
"motion trail" outlines of past generations on separate layers (separate
layers = separate pens on an AxiDraw-style plotter).

Back: the QR code drawn as horizontal pen strokes — consecutive dark
modules merge into one line, and each module row is hatched with enough
passes (at the configured pen width) to read as solid.  A pen cannot
"fill", so everything is stroke geometry a plotter can actually draw.

Usage:
    python -m src.plot_svg --demo                 # golden glider front+back
    python -m src.plot_svg --periods 4 5 6 7      # from data/<p>/patterns.json

Output: plots/<period>/<apgcode>_front.svg and _back.svg
"""
import argparse
import json
import math
import os

import qrcode

from . import config
from . import engine
from . import rle as rle_codec
from . import ruletable
from . import shipurl
from . import stroke_font

STROKE_MM = config.PEN_WIDTH_MM


def _svg_header(width_mm, height_mm):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
        'width="%gmm" height="%gmm" viewBox="0 0 %g %g">'
        % (width_mm, height_mm, width_mm, height_mm)
    )


def _layer(name, content, stroke="black"):
    return (
        '<g inkscape:groupmode="layer" inkscape:label="%s" '
        'fill="none" stroke="%s" stroke-width="%g" '
        'stroke-linejoin="round" stroke-linecap="round">%s</g>'
        % (name, stroke, STROKE_MM, content)
    )


def _cells_path(cells, origin_x, origin_y, cell_mm, inset_mm=0.0):
    """One path drawing every live cell as a square outline."""
    parts = []
    s = cell_mm - 2 * inset_mm
    for x, y in sorted(cells):
        px = origin_x + x * cell_mm + inset_mm
        py = origin_y + y * cell_mm + inset_mm
        parts.append("M%g %gh%gv%gh%gz" % (px, py, s, s, -s))
    return '<path d="%s"/>' % "".join(parts)


def card_frame_path():
    """Rounded-rectangle cut/registration line for the card edge."""
    w, h, r = config.CARD_WIDTH_MM, config.CARD_HEIGHT_MM, 3.0
    return (
        '<rect x="0.5" y="0.5" width="%g" height="%g" rx="%g"/>'
        % (w - 1, h - 1, r)
    )


def ship_layout(cells, trail_generations, table):
    """Compute generations and the cell size that fits them on the card."""
    generations = list(engine.run(cells, table, trail_generations))
    all_cells = set().union(*generations)
    min_x = min(c[0] for c in all_cells)
    min_y = min(c[1] for c in all_cells)
    generations = [
        {(x - min_x, y - min_y) for x, y in gen} for gen in generations
    ]
    all_cells = set().union(*generations)
    grid_w = max(c[0] for c in all_cells) + 1
    grid_h = max(c[1] for c in all_cells) + 1

    avail_w = config.CARD_WIDTH_MM - 2 * config.CARD_MARGIN_MM
    avail_h = config.CARD_HEIGHT_MM - 2 * config.CARD_MARGIN_MM
    cell_mm = min(avail_w / grid_w, avail_h / grid_h, 8.0)
    origin_x = (config.CARD_WIDTH_MM - grid_w * cell_mm) / 2
    origin_y = (config.CARD_HEIGHT_MM - grid_h * cell_mm) / 2
    return generations, origin_x, origin_y, cell_mm


def card_front_svg(cells, table=None, trail_generations=0):
    """Front face: the ship, plus optional trail layers showing where the
    next few generations fly (one layer per generation = one pen each)."""
    if trail_generations and table is None:
        raise ValueError("trail generations require a transition table")
    generations, ox, oy, cell_mm = ship_layout(
        cells, trail_generations if table else 0, table or [0] * 512
    )
    svg = [_svg_header(config.CARD_WIDTH_MM, config.CARD_HEIGHT_MM)]
    svg.append(_layer("frame", card_frame_path()))
    # trails first (plotted in a lighter pen), current generation last
    for g, gen_cells in enumerate(generations[1:], start=1):
        inset = 0.25 * g * cell_mm / max(len(generations), 1)
        svg.append(_layer(
            "trail-gen%d" % g,
            _cells_path(gen_cells, ox, oy, cell_mm, inset_mm=inset),
            stroke="silver",
        ))
    svg.append(_layer("ship", _cells_path(generations[0], ox, oy, cell_mm)))
    svg.append("</svg>")
    return "".join(svg)


def qr_matrix(url):
    """Module matrix (list of rows of bools) for ``url``, no border."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=0,
    )
    qr.add_data(url)
    qr.make(fit=True)
    return qr.get_matrix()


def _hatch_offsets(band_mm, pen_mm):
    """Pen-centre offsets that ink a band of ``band_mm`` solid.

    Centres are inset half a pen width from both edges (no bleed into
    neighbouring light modules) and spaced at most 0.8 pen widths so
    successive passes overlap.
    """
    inner = band_mm - pen_mm
    if inner <= 0:
        return [band_mm / 2]
    n = int(math.ceil(inner / (pen_mm * 0.8))) + 1
    step = inner / (n - 1)
    return [pen_mm / 2 + k * step for k in range(n)]


def qr_hatch_path(matrix, origin_x, origin_y, module_mm, pen_mm):
    """Horizontal hatch strokes covering every dark module.

    Consecutive dark modules in a row merge into single lines; endpoints
    are inset half a pen width so the ink stays inside the run.
    """
    parts = []
    offsets = _hatch_offsets(module_mm, pen_mm)
    for row_idx, row in enumerate(matrix):
        y0 = origin_y + row_idx * module_mm
        runs = []
        col = 0
        while col < len(row):
            if row[col]:
                start = col
                while col < len(row) and row[col]:
                    col += 1
                runs.append((start, col))
            else:
                col += 1
        for start, end in runs:
            x1 = origin_x + start * module_mm + pen_mm / 2
            x2 = origin_x + end * module_mm - pen_mm / 2
            for dy in offsets:
                parts.append("M%g %gH%g" % (x1, y0 + dy, x2))
    return '<path d="%s"/>' % "".join(parts)


def back_geometry(url):
    """(matrix, module_mm, qx, qy, quiet_mm) for the QR on a card back.

    Shared with impose.py so a single card and a sheet of cards place
    the QR -- and the claim code under it -- identically.
    """
    matrix = qr_matrix(url)
    modules = len(matrix)
    module_mm = config.QR_TARGET_MM / modules
    qx = (config.CARD_WIDTH_MM - config.QR_TARGET_MM) / 2
    qy = (config.CARD_HEIGHT_MM - config.QR_TARGET_MM) / 2
    # QR spec: at least a 4-module quiet zone on every side.
    quiet_mm = 4 * module_mm
    if min(qx, qy) - 1.0 < quiet_mm:  # 1mm allowance for the frame line
        raise ValueError(
            "QR of %d modules at %gmm leaves no quiet zone on the card"
            % (modules, config.QR_TARGET_MM)
        )
    return matrix, module_mm, qx, qy, quiet_mm


def claim_code_path_d(code, qy, quiet_mm):
    """The claim code in stroke font, centred under the QR's quiet zone.

    The code is uppercase letters and digits (no descenders), so its cap
    height is its full height; it must clear the card's bottom margin.
    """
    cap = config.CARD_CLAIM_CAP_MM
    baseline = qy + config.QR_TARGET_MM + quiet_mm + config.CARD_CLAIM_GAP_MM + cap
    if baseline > config.CARD_HEIGHT_MM - config.CARD_MARGIN_MM:
        raise ValueError(
            "claim code at %gmm caps does not fit under the QR" % cap
        )
    return stroke_font.text_path_d(
        code, config.CARD_WIDTH_MM / 2, baseline, cap, align="center"
    )


def card_back_svg(url, code=None):
    """Back face: centred QR code as horizontal pen strokes, plus the
    claim code under it when one is given.

    Every dark module is hatched at the configured pen width; the blank
    card stock provides the light modules and the quiet zone.
    """
    matrix, module_mm, qx, qy, quiet_mm = back_geometry(url)
    pen_mm = config.PEN_WIDTH_MM
    svg = [_svg_header(config.CARD_WIDTH_MM, config.CARD_HEIGHT_MM)]
    svg.append(_layer("frame", card_frame_path()))
    svg.append(
        '<g inkscape:groupmode="layer" inkscape:label="qr" '
        'fill="none" stroke="black" stroke-width="%g" '
        'stroke-linecap="butt">%s</g>'
        % (pen_mm, qr_hatch_path(matrix, qx, qy, module_mm, pen_mm))
    )
    if code:
        svg.append(_layer(
            "claim", '<path d="%s"/>' % claim_code_path_d(code, qy, quiet_mm)
        ))
    svg.append("</svg>")
    return "".join(svg)


def write_card(out_dir, key, front_svg, back_svg):
    os.makedirs(out_dir, exist_ok=True)
    front_path = os.path.join(out_dir, key + "_front.svg")
    back_path = os.path.join(out_dir, key + "_back.svg")
    with open(front_path, "w") as f:
        f.write(front_svg)
    with open(back_path, "w") as f:
        f.write(back_svg)
    return front_path, back_path


def run_demo(trail):
    cells, rule = rle_codec.parse("x=3,y=3,rule=B3/S23\nbob$2bo$3o!")
    table = ruletable.totalistic_table("b3s23")
    url = shipurl.player_url(apgcode="xq4_153", rule="b3s23")
    front = card_front_svg(cells, table=table, trail_generations=trail)
    back = card_back_svg(url)
    paths = write_card(os.path.join("plots", "demo"), "xq4_153", front, back)
    print("wrote %s and %s" % paths)


def run_periods(periods, trail):
    try:
        from submodules import lifelib
    except Exception:
        lifelib = None
        if trail:
            print("note: lifelib unavailable — trails only for totalistic rules")
    for period in periods:
        with open(os.path.join("data", str(period), "patterns.json")) as f:
            patterns = json.load(f)
        out_dir = os.path.join("plots", str(period))
        count = 0
        for filename, node in patterns.items():
            apgcode, rule = node.get("apgcode"), node.get("rule")
            if not apgcode or not rule:
                continue
            cells, _ = rle_codec.parse(node["rle"])
            table = None
            if trail:
                try:
                    table = ruletable.table_for_rule(rule, lifelib)
                except ValueError:
                    pass
            front = card_front_svg(
                cells, table=table, trail_generations=trail if table else 0
            )
            back = card_back_svg(shipurl.player_url(apgcode=apgcode, rule=rule))
            write_card(out_dir, apgcode, front, back)
            count += 1
        print("wrote %d cards to %s" % (count, out_dir))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--periods", nargs="*", default=[])
    parser.add_argument("--trail", type=int, default=0,
                        help="number of past generations to plot as trails")
    args = parser.parse_args()
    if args.demo:
        run_demo(args.trail)
    if args.periods:
        run_periods(args.periods, args.trail)
    if not args.demo and not args.periods:
        parser.print_help()


if __name__ == "__main__":
    main()
