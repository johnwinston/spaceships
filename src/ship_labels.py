"""Public QR stickers for the back of each plotted card, on Avery 5160 stock.

Same links as ship_sheet.py (the ship's page, no claim code), laid out on
Avery 5160 / 8160 / 18160 address labels: 1" x 2-5/8", 30 per US Letter
sheet.  Each label has the QR on the left; beside it the ship's art (turned
lengthwise), centred on the QR's middle, with its id centred beneath, kept 0.06" inside the label edge for printer
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
ART_H = 0.5     # max ship art height; the art is centred on the QR's middle
GAP = 0.08      # between the QR and the art column
ART_W = LABEL_W - 2 * INSET - QR_SIZE - GAP  # width of the art column
ID_GAP = 0.04   # between the art and the id beneath it


def label_origin(index):
    """Top-left corner (x, y) in inches of label `index` (0..29) on its sheet."""
    row, col = divmod(index, COLS)
    return LEFT + col * PITCH_X, TOP + row * PITCH_Y


def _ship_svg_wide(rle_text):
    """(svg, height in inches): the ship's cells, turned 90 degrees if it's
    taller than wide, sized to fit ART_W x ART_H."""
    cells, _ = rle_codec.parse(rle_text)
    w = max(x for x, _ in cells) + 1
    h = max(y for _, y in cells) + 1
    if h > w:  # rotate clockwise: (x, y) -> (h - 1 - y, x)
        cells = [(h - 1 - y, x) for x, y in cells]
        w, h = h, w
    d = "".join("M%d %dh1v1h-1z" % (x, y) for x, y in cells)
    height = min(ART_H, ART_W * h / w)
    return ('<svg class="ship" viewBox="0 0 %d %d" style="height:%.4fin">'
            '<path d="%s"/></svg>' % (w, h, height, d)), height


def _label(ship_id, edition, url, entry, outline):
    art, height = _ship_svg_wide(entry["rle"])
    top = (QR_SIZE - height) / 2  # the ship's middle on the QR's middle
    return (
        '<div class="label%s">'
        '<div class="qr-box">%s</div>'
        '<div class="text">'
        '<div class="art" style="top:%.4fin">%s</div>'
        '<span style="top:%.4fin">%s</span></div>'
        '</div>' % (" outline" if outline else "", _qr_svg(url),
                    top, art, top + height + ID_GAP, html.escape(ship_id))
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
        "w": LABEL_W, "h": LABEL_H, "inset": INSET, "qr": QR_SIZE, "artw": ART_W, "gap": GAP,
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
           display: flex; gap: %(gap)sin; align-items: flex-start; }
  .outline { border: 0.5pt solid #bbb; border-radius: 0.08in; }
  .qr-box { flex: none; width: %(qr)sin; height: %(qr)sin; }
  .qr-box svg { width: 100%%; height: 100%%; display: block; }
  .qr path { fill: #000; }
  .text { position: relative; flex: none; width: %(artw)sin; height: %(qr)sin; }
  .art, .text span { position: absolute; left: 0; right: 0; }
  .art svg { display: block; margin: 0 auto; max-width: 100%%; }
  .text span { font: 8pt/1 ui-monospace, monospace; color: #444; text-align: center; }
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
