#!/usr/bin/env python3
"""Bake a plot-ready flat SVG from an imposed sheet.

saxi's CLI flattens SVGs through svgdom, whose nested-transform
composition is broken: a parent group's rotation is dropped from its
children's transforms (probed 2026-08-23 — ``translate() rotate()`` in a
single attribute works, but wrapping already-transformed card groups in
a rotate group produces garbage).  Plot files therefore must carry NO
transforms at all.  This script parses an imposed sheet, applies each
card's translate — and, with --rotate, the portrait→landscape rotation —
numerically, and emits one flat SVG of bare <path> elements sized
exactly to the paper, so saxi's mapping is identity.

Usage:
    python3 scripts/bake_plot_svg.py plots/sheets/sheet_01_front.svg \
        --layers grid --rotate --out plots/sheets/plot/s01_pass1_grid.svg
    python3 scripts/bake_plot_svg.py plots/sheets/sheet_01_front.svg \
        --layers hatch,label --rotate --out plots/sheets/plot/s01_pass2_inks.svg

--rotate turns the portrait sheet (W x H) into landscape (H x W) via
(x, y) -> (H - y, x), which is how a portrait design lands on stock
placed landscape on the machine.

Output is in CSS px units (96/25.4 px per mm) and MUST be plotted with
saxi's --no-fit-page flag: saxi's default fit-page mode rescales and
re-centres the drawing to the content bbox, so two passes with
different bboxes (grid vs inks) land at different scales and positions
on the paper (probed 2026-08-23: the hatch pass plotted offset from
the grid pass).  With --no-fit-page saxi converts px -> mm at 25.4/96
exactly, giving the identity mapping these files are designed for.
"""
import argparse
import re
import sys

PX_PER_MM = 96 / 25.4

NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
TOKEN = re.compile(r"([MLHVCZmlhvcz])|(" + NUM + ")")


def parse_path(d):
    """Path data -> list of subpaths; each subpath is a list of absolute
    commands ("L", x, y) / ("C", x1, y1, x2, y2, x, y), starting with M."""
    items = [c if c else float(n) for c, n in TOKEN.findall(d)]
    i = 0
    cmd = None
    cur = (0.0, 0.0)
    start = (0.0, 0.0)
    subpaths = []
    sub = None

    def take(k):
        nonlocal i
        vals = items[i:i + k]
        if len(vals) != k or any(isinstance(v, str) for v in vals):
            raise ValueError("malformed path data near index %d" % i)
        i += k
        return vals

    while i < len(items):
        if isinstance(items[i], str):
            cmd = items[i]
            i += 1
            if cmd in "Zz":
                if sub is not None and cur != start:
                    sub.append(("L",) + start)
                cur = start
                cmd = None
                continue
        if cmd is None:
            raise ValueError("path data continues after Z without a command")
        if cmd in "Mm":
            x, y = take(2)
            if cmd == "m":
                x, y = cur[0] + x, cur[1] + y
            cur = start = (x, y)
            sub = [("M", x, y)]
            subpaths.append(sub)
            cmd = "L" if cmd == "M" else "l"
        elif cmd in "Ll":
            x, y = take(2)
            if cmd == "l":
                x, y = cur[0] + x, cur[1] + y
            sub.append(("L", x, y))
            cur = (x, y)
        elif cmd in "Hh":
            (x,) = take(1)
            if cmd == "h":
                x += cur[0]
            sub.append(("L", x, cur[1]))
            cur = (x, cur[1])
        elif cmd in "Vv":
            (y,) = take(1)
            if cmd == "v":
                y += cur[1]
            sub.append(("L", cur[0], y))
            cur = (cur[0], y)
        elif cmd in "Cc":
            v = take(6)
            if cmd == "c":
                v = [v[j] + (cur[0] if j % 2 == 0 else cur[1]) for j in range(6)]
            sub.append(("C",) + tuple(v))
            cur = (v[4], v[5])
        else:
            raise ValueError("unsupported path command %r" % cmd)
    return subpaths


def emit_path(subpaths, transform):
    parts = []
    for sub in subpaths:
        for seg in sub:
            pts = [transform(seg[j], seg[j + 1]) for j in range(1, len(seg), 2)]
            parts.append(seg[0] if seg[0] != "M" else "M")
            parts.append(" ".join("%.3f %.3f" % p for p in pts))
    return "".join(
        p if p in "MLC" else p for p in parts
    )


def layer_spans(svg):
    """name -> (start, end) byte spans of top-level inkscape layer groups."""
    spans = {}
    for m in re.finditer(r'<g inkscape:groupmode="layer"[^>]*>', svg):
        name = re.search(r'inkscape:label="([^"]+)"', m.group(0)).group(1)
        depth = 0
        for g in re.finditer(r"<g\b|</g>", svg[m.start():]):
            depth += 1 if g.group(0) == "<g" else -1
            if depth == 0:
                spans[name] = (m.start(), m.start() + g.end())
                break
    return spans


def bake(sheet_svg, layers, rotate, card=None, slot=None):
    m = re.search(r'width="(%s)mm" height="(%s)mm"' % (NUM, NUM), sheet_svg)
    page_w, page_h = float(m.group(1)), float(m.group(2))
    if rotate:
        out_w, out_h = page_h, page_w

        def page_xform(x, y):
            return (page_h - y, x)
    else:
        out_w, out_h = page_w, page_h

        def page_xform(x, y):
            return (x, y)

    spans = layer_spans(sheet_svg)
    missing = [n for n in layers if n not in spans]
    if missing:
        raise SystemExit("layers not in sheet: %s (has %s)" % (missing, sorted(spans)))

    out_paths = []
    bbox = [1e9, 1e9, -1e9, -1e9]
    for name in layers:
        a, b = spans[name]
        body = sheet_svg[a:b]
        head = body[:body.index(">") + 1]
        stroke = re.search(r'stroke="([^"]+)"', head)
        width = re.search(r'stroke-width="([^"]+)"', head)
        stroke = stroke.group(1) if stroke else "black"
        width = width.group(1) if width else "0.35"
        # paths either sit inside a translate wrapper (one per card) or bare
        groups = list(re.finditer(
            r'(?:<g transform="translate\((%s)[ ,](%s)\)">\s*)?<path d="([^"]+)"' % (NUM, NUM),
            body,
        ))
        for idx, gm in enumerate(groups, start=1):
            if card is not None and idx != card:
                continue
            # --slot M plots this card's artwork at another card's position
            pos = groups[slot - 1] if slot is not None else gm
            tx = float(pos.group(1)) if pos.group(1) else 0.0
            ty = float(pos.group(2)) if pos.group(2) else 0.0

            def xform(x, y, tx=tx, ty=ty):
                p = page_xform(x + tx, y + ty)
                bbox[0] = min(bbox[0], p[0]); bbox[1] = min(bbox[1], p[1])
                bbox[2] = max(bbox[2], p[0]); bbox[3] = max(bbox[3], p[1])
                return (p[0] * PX_PER_MM, p[1] * PX_PER_MM)

            d = emit_path(parse_path(gm.group(3)), xform)
            out_paths.append(
                '<path d="%s" fill="none" stroke="%s" stroke-width="%s" '
                'stroke-linejoin="round" stroke-linecap="round"/>' % (d, stroke, width)
            )
    if not (0 <= bbox[0] and 0 <= bbox[1] and bbox[2] <= out_w and bbox[3] <= out_h):
        raise SystemExit("BAKE SANITY FAILED: content bbox %s exceeds page %gx%g"
                         % (["%.1f" % v for v in bbox], out_w, out_h))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%g" height="%g" '
        'viewBox="0 0 %g %g">%s</svg>'
        % (out_w * PX_PER_MM, out_h * PX_PER_MM,
           out_w * PX_PER_MM, out_h * PX_PER_MM, "".join(out_paths))
    )
    return svg, bbox, (out_w, out_h)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("sheet")
    ap.add_argument("--layers", required=True,
                    help="comma-separated layer names, e.g. grid or hatch,label")
    ap.add_argument("--rotate", action="store_true",
                    help="rotate portrait sheet onto landscape stock")
    ap.add_argument("--card", type=int, default=None,
                    help="bake only the Nth card (1-based, document order) "
                         "of each layer, for one-card-at-a-time plotting")
    ap.add_argument("--slot", type=int, default=None,
                    help="with --card: plot that card's artwork at this "
                         "slot's position instead of its own (1-based)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    sheet = open(args.sheet).read()
    layers = [n.strip() for n in args.layers.split(",") if n.strip()]
    svg, bbox, (w, h) = bake(sheet, layers, args.rotate, card=args.card,
                             slot=args.slot)
    with open(args.out, "w") as f:
        f.write(svg)
    print("%s: %s -> %gx%g mm page, content x %.1f-%.1f y %.1f-%.1f, %d paths"
          % (args.out, "+".join(layers), w, h, bbox[0], bbox[2], bbox[1], bbox[3],
             svg.count("<path")))


if __name__ == "__main__":
    main()
