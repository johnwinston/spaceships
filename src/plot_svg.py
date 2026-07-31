"""Plotter-ready SVG card faces.

Replaces the raster card pipeline (combine.py) for the pen-plotted
edition: everything is stroke-only vector geometry in real millimetres,
sized for a standard poker card (see config.py).

Front: the spaceship's live cells as outlined squares, optionally with
"motion trail" outlines of past generations on separate layers (separate
layers = separate pens on an AxiDraw-style plotter).

Back: the QR code as a single SVG path (from the qrcode library's SVG
factory), plus an optional caption in stroke-only geometry left to the
plotting software's Hershey-text tooling.

Usage:
    python -m src.plot_svg --demo                 # golden glider front+back
    python -m src.plot_svg --periods 4 5 6 7      # from data/<p>/patterns.json

Output: plots/<period>/<apgcode>_front.svg and _back.svg
"""
import argparse
import json
import os
import xml.etree.ElementTree as ET

import qrcode
import qrcode.image.svg

from . import config
from . import engine
from . import rle as rle_codec
from . import ruletable
from . import shipurl

STROKE_MM = 0.35  # typical fineliner width


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


def qr_path_d(url):
    """Render the QR for ``url`` and return (path_d, coordinate_span).

    coordinate_span is the width of the QR in the path's own units, read
    from the generated viewBox (the qrcode SVG factory uses 0.1 units per
    module, so don't assume 1 unit = 1 module).
    """
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=1,
        border=0,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    root = ET.fromstring(img.to_string())
    path = root.find(".//{http://www.w3.org/2000/svg}path")
    span = float(root.get("viewBox").split()[2])
    return path.get("d"), span


def card_back_svg(url):
    """Back face: centred QR code as filled path (plot with fill routines
    or a thick pen; modules are square regions)."""
    d, span = qr_path_d(url)
    scale = config.QR_TARGET_MM / span
    qx = (config.CARD_WIDTH_MM - config.QR_TARGET_MM) / 2
    qy = (config.CARD_HEIGHT_MM - config.QR_TARGET_MM) / 2
    svg = [_svg_header(config.CARD_WIDTH_MM, config.CARD_HEIGHT_MM)]
    svg.append(_layer("frame", card_frame_path()))
    svg.append(
        '<g inkscape:groupmode="layer" inkscape:label="qr" '
        'transform="translate(%g %g) scale(%g)">'
        '<path d="%s" fill="black" stroke="none"/></g>'
        % (qx, qy, scale, d)
    )
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
