"""Public QR stickers for the back of each plotted card, on Avery 5160 stock.

Same links as ship_sheet.py (the ship's page, no claim code), laid out on
Avery 5160 / 8160 / 18160 address labels: 1" x 2-5/8", 30 per US Letter
sheet.  Each label has the QR on the left; on the right, the ship's art (turned
lengthwise, top aligned with the QR's top) with its id centred beneath, kept 0.06" inside the label edge for printer
drift.  Labels run in edition order; 99 ships fill 4 sheets.

    python -m src.ship_labels            -> data/ship_labels_5160.html
    python -m src.ship_labels --test     -> data/ship_labels_test.html
                                            (one page, label outlines only:
                                             print on plain paper, hold it
                                             against a label sheet)

Print at 100% / "Actual size" -- any fit-to-page scaling breaks alignment.
"""
import argparse
import html
import json
import os

from . import rle as rle_codec
from . import plot_svg
from .claim_sheet import _qr_svg
from .ship_sheet import tiles

OUT_PATH = os.path.join("data", "ship_labels_5160.html")
TEST_PATH = os.path.join("data", "ship_labels_test.html")

# Avery 5160 geometry, inches (Avery's published template).
TOP = 0.5
LEFT = 0.1875
LABEL_W = 2.625
LABEL_H = 1.0
PITCH_X = 2.75   # 0.125" gutter between columns
PITCH_Y = 1.0    # rows touch
COLS, ROWS = 3, 10
PER_SHEET = COLS * ROWS
INSET = 0.06     # keep ink this far inside each label
QR_SIZE = LABEL_H - 2 * INSET  # 0.88": the QR svg already includes its quiet zone
ART_H = 0.5     # ship art height; its top lines up with the top of the QR
QUIET = 2       # quiet-zone modules on each side of claim_sheet._qr_svg


def label_origin(index):
    """Top-left corner (x, y) in inches of label `index` (0..29) on its sheet."""
    row, col = divmod(index, COLS)
    return LEFT + col * PITCH_X, TOP + row * PITCH_Y


def _ship_svg_wide(rle_text):
    """The ship's cells as an SVG, turned 90 degrees if it's taller than wide."""
    cells, _ = rle_codec.parse(rle_text)
    w = max(x for x, _ in cells) + 1
    h = max(y for _, y in cells) + 1
    if h > w:  # rotate clockwise: (x, y) -> (h - 1 - y, x)
        cells = [(h - 1 - y, x) for x, y in cells]
        w, h = h, w
    d = "".join("M%d %dh1v1h-1z" % (x, y) for x, y in cells)
    return ('<svg class="ship" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMin meet">'
            '<path d="%s"/></svg>' % (w, h, d))


def qr_top(url):
    """Inches from the top of the QR box to its first dark row (the quiet zone)."""
    n = len(plot_svg.qr_matrix(url))
    return QR_SIZE * QUIET / (n + 2 * QUIET)


def _label(ship_id, edition, url, entry, outline):
    return (
        '<div class="label%s">'
        '<div class="qr-box">%s</div>'
        '<div class="text" style="padding-top:%.4fin">'
        '<div class="art">%s</div><span>%s</span></div>'
        '</div>' % (" outline" if outline else "", _qr_svg(url), qr_top(url),
                    _ship_svg_wide(entry["rle"]), html.escape(ship_id))
    )


def render(rows, test=False):
    """HTML for all sheets; with `test`, one sheet of empty outlined labels."""
    sheets = []
    batches = [[None] * PER_SHEET] if test else [
        rows[i:i + PER_SHEET] for i in range(0, len(rows), PER_SHEET)]
    for batch in batches:
        cells = []
        for i, row in enumerate(batch):
            x, y = label_origin(i)
            inner = '<div class="label outline"></div>' if row is None else _label(*row, outline=False)
            cells.append('<div class="slot" style="left:%.4fin;top:%.4fin">%s</div>' % (x, y, inner))
        sheets.append('<section class="sheet">%s</section>' % "".join(cells))
    return PAGE_TEMPLATE % {
        "title": "Spaceships labels (alignment test)" if test else "Spaceships labels",
        "w": LABEL_W, "h": LABEL_H, "inset": INSET, "qr": QR_SIZE, "art": ART_H,
        "sheets": "".join(sheets),
    }


PAGE_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>%(title)s</title>
<style>
  @page { size: 8.5in 11in; margin: 0; }
  html, body { margin: 0; padding: 0; background: #fff; color: #111;
               font-family: -apple-system, system-ui, sans-serif; }
  .sheet { position: relative; width: 8.5in; height: 11in; overflow: hidden;
           page-break-after: always; break-after: page; }
  .sheet:last-child { page-break-after: auto; break-after: auto; }
  .slot { position: absolute; width: %(w)sin; height: %(h)sin; }
  .label { box-sizing: border-box; width: 100%%; height: 100%%; padding: %(inset)sin;
           display: flex; gap: 0.08in; align-items: flex-start; }
  .outline { border: 0.5pt solid #bbb; border-radius: 0.08in; }
  .qr-box { flex: none; width: %(qr)sin; height: %(qr)sin; }
  .qr-box svg { width: 100%%; height: 100%%; display: block; }
  .qr path { fill: #000; }
  .text { box-sizing: border-box; flex: 1; min-width: 0; height: 100%%; display: flex;
          flex-direction: column; align-items: center; gap: 0.05in; }
  .text span { font: 8pt/1 ui-monospace, monospace; color: #444; text-align: center; }
  .art { width: 100%%; height: %(art)sin; flex: none; }
  .art svg { width: 100%%; height: 100%%; display: block; }
  .ship path { fill: #111; }
</style></head><body>
%(sheets)s
</body></html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=os.path.join("web", "catalog.json"))
    parser.add_argument("--site", default=None, help="player base URL (default: config)")
    parser.add_argument("--test", action="store_true", help="one outline-only alignment page")
    parser.add_argument("-o", "--out", default=None)
    args = parser.parse_args(argv)
    out = args.out or (TEST_PATH if args.test else OUT_PATH)
    rows = []
    if not args.test:
        with open(args.catalog) as f:
            rows = tiles(json.load(f), args.site)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w") as f:
        f.write(render(rows, test=args.test))
    sheets = 1 if args.test else -(-len(rows) // PER_SHEET)
    print("wrote %s (%d sheet%s)" % (out, sheets, "" if sheets == 1 else "s"))


if __name__ == "__main__":
    main()
