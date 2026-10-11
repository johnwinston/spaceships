"""The booth's claim booklet: one QR per card, kept off the cards.

The cards on the table carry no working secret.  When someone buys one,
John finds that card's tile in this booklet and the buyer scans it: the
QR opens the player on their ship with the claim code already filled in,
so all that's left is pasting a wallet address.

Every tile is a secret -- whoever scans it can claim that ship -- so the
output goes under data/ (gitignored), never into the repo or web/.

    AUTOMONS_CLAIM_SECRET=... python -m src.claim_sheet
    -> data/claim_sheet.html   open in a browser, print (A4, 12 per page)
"""
import argparse
import html
import json
import os

from . import claimcode
from . import plot_svg
from . import rle as rle_codec
from . import shipurl
from .nft_metadata import deck_entries

OUT_PATH = os.path.join("data", "claim_sheet.html")
PER_PAGE = 12


def claim_url(ship_id, code, site=None):
    """The player URL with the claim code prefilled (`c=`)."""
    return shipurl.player_url(base=site, ship_id=ship_id, claim=code.replace("-", ""))


def _qr_svg(url):
    matrix = plot_svg.qr_matrix(url)
    n = len(matrix)
    d = "".join(
        "M%d %dh1v1h-1z" % (x, y)
        for y, row in enumerate(matrix) for x, on in enumerate(row) if on
    )
    return ('<svg class="qr" viewBox="-2 -2 %d %d" shape-rendering="crispEdges">'
            '<path d="%s"/></svg>' % (n + 4, n + 4, d))


def _ship_svg(rle_text):
    cells, _ = rle_codec.parse(rle_text)
    w = max(x for x, _ in cells) + 1
    h = max(y for _, y in cells) + 1
    d = "".join("M%d %dh1v1h-1z" % (x, y) for x, y in cells)
    return ('<svg class="ship" viewBox="-1 -1 %d %d"><path d="%s"/></svg>'
            % (w + 2, h + 2, d))


def tiles(catalog, secret, site=None):
    """[(ship_id, edition, code, url, entry)] in edition order."""
    out = []
    for ship_id, entry in deck_entries(catalog):
        code = claimcode.claim_code(ship_id, secret)
        out.append((ship_id, int(entry["edition"]), code,
                    claim_url(ship_id, code, site), entry))
    return out


def render(rows, deck_size):
    pages = []
    for start in range(0, len(rows), PER_PAGE):
        cells = []
        for ship_id, edition, code, url, entry in rows[start:start + PER_PAGE]:
            cells.append(
                '<div class="tile">'
                '<div class="head"><b>#%d</b> <span>%s</span></div>'
                '<div class="art">%s%s</div>'
                '<div class="code">%s</div>'
                '</div>' % (edition, html.escape(ship_id), _ship_svg(entry["rle"]),
                            _qr_svg(url), html.escape(code))
            )
        pages.append('<section class="page">%s</section>' % "".join(cells))
    return PAGE_TEMPLATE % {"deck": deck_size, "pages": "".join(pages)}


PAGE_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Spaceships claim booklet (private)</title>
<style>
  @page { size: A4; margin: 10mm; }
  body { font: 11px/1.3 -apple-system, system-ui, sans-serif; margin: 0; color: #111; background: #fff; }
  .note { padding: 8mm 10mm 0; }
  .page { display: grid; grid-template-columns: repeat(3, 1fr); grid-auto-rows: 66mm;
          gap: 0; width: 190mm; margin: 0 auto; page-break-after: always; }
  .tile { border: 0.2mm dashed #aaa; padding: 3mm; display: flex; flex-direction: column; gap: 2mm; }
  .head { display: flex; justify-content: space-between; font-size: 12px; }
  .head span { font-family: ui-monospace, monospace; color: #555; }
  .art { flex: 1; display: grid; grid-template-columns: 1fr 2fr; gap: 3mm; align-items: center; min-height: 0; }
  .art svg { width: 100%%; max-height: 46mm; display: block; }
  .ship path { fill: #111; }
  .qr path { fill: #000; }
  .code { font-family: ui-monospace, monospace; font-size: 13px; letter-spacing: 0.1em; text-align: center; }
  @media print { .note { display: none; } }
</style></head><body>
<p class="note">Private: every tile claims its ship. %(deck)d cards. Print on A4, cut along the dashes.</p>
%(pages)s
</body></html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=os.path.join("web", "catalog.json"))
    parser.add_argument("--site", default=None, help="player base URL (default: config)")
    parser.add_argument("-o", "--out", default=OUT_PATH)
    args = parser.parse_args(argv)
    secret = claimcode.claim_secret()
    with open(args.catalog) as f:
        catalog = json.load(f)
    rows = tiles(catalog, secret, args.site)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write(render(rows, len(rows)))
    print("wrote %d claim tiles to %s -- keep it private" % (len(rows), args.out))


if __name__ == "__main__":
    main()
