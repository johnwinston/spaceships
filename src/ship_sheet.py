"""The public QR sheet: one tile per card, each opening that ship's page.

The companion to claim_sheet.py.  These QRs carry no claim code -- they
just open the player on the ship -- so the sheet is safe to leave on the
table or stick next to the cards.  Same layout as the booklet, so the two
print and cut alike.

    python -m src.ship_sheet
    -> data/ship_sheet.html   open in a browser, print (A4, 12 per page)
"""
import argparse
import html
import json
import os

from . import shipurl
from .claim_sheet import PER_PAGE, _qr_svg, _ship_svg
from .nft_metadata import deck_entries

OUT_PATH = os.path.join("data", "ship_sheet.html")


def ship_url(ship_id, site=None):
    """The player URL for one ship, with no claim code."""
    return shipurl.player_url(base=site, ship_id=ship_id)


def tiles(catalog, site=None):
    """[(ship_id, edition, url, entry)] in edition order."""
    return [(ship_id, int(entry["edition"]), ship_url(ship_id, site), entry)
            for ship_id, entry in deck_entries(catalog)]


def _details(entry):
    bits = []
    if entry.get("period"):
        bits.append("period %s" % entry["period"])
    if entry.get("rarity"):
        bits.append(str(entry["rarity"]))
    return " · ".join(html.escape(b) for b in bits)


def render(rows, deck_size):
    pages = []
    for start in range(0, len(rows), PER_PAGE):
        cells = []
        for ship_id, edition, url, entry in rows[start:start + PER_PAGE]:
            cells.append(
                '<div class="tile">'
                '<div class="head"><b>Spaceship #%d</b> <span>%s</span></div>'
                '<div class="art">%s%s</div>'
                '<div class="info">%s</div>'
                '</div>' % (edition, html.escape(ship_id), _ship_svg(entry["rle"]),
                            _qr_svg(url), _details(entry))
            )
        pages.append('<section class="page">%s</section>' % "".join(cells))
    return PAGE_TEMPLATE % {"deck": deck_size, "pages": "".join(pages)}


PAGE_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Spaceships QR sheet</title>
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
  .info { font-size: 11px; color: #555; text-align: center; }
  @media print { .note { display: none; } }
</style></head><body>
<p class="note">Public: each QR opens its ship's page (no claim code). %(deck)d cards. Print on A4, cut along the dashes.</p>
%(pages)s
</body></html>
"""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=os.path.join("web", "catalog.json"))
    parser.add_argument("--site", default=None, help="player base URL (default: config)")
    parser.add_argument("-o", "--out", default=OUT_PATH)
    args = parser.parse_args(argv)
    with open(args.catalog) as f:
        catalog = json.load(f)
    rows = tiles(catalog, args.site)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write(render(rows, len(rows)))
    print("wrote %d ship tiles to %s" % (len(rows), args.out))


if __name__ == "__main__":
    main()
