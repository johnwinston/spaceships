"""NFT metadata + artwork for every card in the deck.

Reads web/catalog.json (build_deck output) and writes, under web/nft/ so
GitHub Pages serves it next to the player:

    web/nft/<id>.json        Metaplex token metadata for one ship
    web/nft/<id>.gif         the ship flying through one period, looped
    web/nft/collection.json  metadata for the collection itself
    web/nft/collection.gif   cover image: the first card's ship

chain/src/premint.mjs points each on-chain asset at <site>/nft/<id>.json.
The files are plain static assets, so they can move to permanent storage
(Arweave) later and the assets' URIs be updated -- the vault wallet stays
the update authority.

Usage:
    python -m src.nft_metadata
    python -m src.nft_metadata --catalog path/to/catalog.json --site https://example.com/
"""
import argparse
import json
import os

from PIL import Image, ImageDraw

from . import config
from . import engine
from . import rle as rle_codec
from . import ruletable
from . import shipurl

COLLECTION_NAME = "Spaceships"
OUT_DIR = os.path.join("web", "nft")

# Artwork: a card-shaped frame (the cards are 1:1.4), ink on paper, the
# ship centred and flying up like it does on the card and in the player.
IMAGE_W, IMAGE_H = 600, 840
PAPER = (246, 243, 236)
INK = (24, 24, 24)
FRAME_MS = 160
# Box the ship is scaled into, in cells -- the card's ship box (16 x 25)
# plus a margin so every ship in the deck draws at the same cell size.
BOX_CELLS = (22, 31)


def deck_entries(catalog):
    """[(id, entry)] for real cards (edition > 0), in edition order."""
    cards = [(sid, e) for sid, e in catalog.items() if int(e.get("edition") or 0)]
    return sorted(cards, key=lambda item: int(item[1]["edition"]))


def _table(entry):
    if entry.get("table"):
        return ruletable.table_from_hex(entry["table"])
    return ruletable.totalistic_table(entry["rule"])


def _bbox(cells):
    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    return min(xs), min(ys), max(xs), max(ys)


def _centre(cells):
    x0, y0, x1, y1 = _bbox(cells)
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0


def _orient_up(dx, dy):
    """Rotate/flip a whole run so the ship's travel points up the image."""
    if abs(dy) >= abs(dx):
        if dy <= 0:
            return lambda c: c
        return lambda c: (c[0], -c[1])
    if dx < 0:
        return lambda c: (c[1], c[0])
    return lambda c: (c[1], -c[0])


def flight_frames(entry):
    """One period of the ship as cell sets, camera following the ship.

    The camera moves at the ship's average speed, so frame `period` would
    equal frame 0 and the gif loops without a jump.
    """
    cells, _ = rle_codec.parse(entry["rle"])
    period = int(entry["period"])
    gens = list(engine.run(cells, _table(entry), period))
    cx0, cy0 = _centre(gens[0])
    cxp, cyp = _centre(gens[-1])
    dx, dy = cxp - cx0, cyp - cy0
    turn = _orient_up(dx, dy)
    frames = []
    for g, live in enumerate(gens[:period]):
        camx = cx0 + dx * g / period
        camy = cy0 + dy * g / period
        frames.append([turn((x - camx, y - camy)) for x, y in live])
    return frames


def render_gif(entry, path):
    """Write the ship's flight as a looping gif."""
    frames = flight_frames(entry)
    cell = min(IMAGE_W / BOX_CELLS[0], IMAGE_H / BOX_CELLS[1])
    images = []
    for live in frames:
        img = Image.new("RGB", (IMAGE_W, IMAGE_H), PAPER)
        draw = ImageDraw.Draw(img)
        gap = max(1.0, cell * 0.08)
        for x, y in live:
            px = IMAGE_W / 2 + (x - 0.5) * cell
            py = IMAGE_H / 2 + (y - 0.5) * cell
            draw.rectangle([px + gap, py + gap, px + cell - gap, py + cell - gap], fill=INK)
        images.append(img.convert("P", palette=Image.ADAPTIVE, colors=4))
    images[0].save(path, save_all=True, append_images=images[1:],
                   duration=FRAME_MS, loop=0, optimize=True)


def metadata_for(ship_id, entry, deck_size, site):
    """Metaplex token-metadata JSON for one card."""
    edition = int(entry["edition"])
    image = site + "nft/%s.gif" % ship_id
    play = shipurl.player_url(base=site, ship_id=ship_id)
    return {
        "name": "%s #%d" % (COLLECTION_NAME.rstrip("s"), edition),
        "symbol": config.NFT_SYMBOL,
        "description": config.NFT_DESCRIPTION,
        "image": image,
        "external_url": play,
        "attributes": [
            {"trait_type": "ship", "value": ship_id},
            {"trait_type": "edition", "value": "%d of %d" % (edition, deck_size)},
            {"trait_type": "period", "value": str(entry["period"])},
            {"trait_type": "rarity", "value": entry.get("rarity", "")},
            {"trait_type": "rule", "value": entry["rule"]},
        ],
        "properties": {
            "files": [{"uri": image, "type": "image/gif"}],
            "category": "image",
        },
    }


def collection_metadata(site):
    return {
        "name": COLLECTION_NAME,
        "symbol": config.NFT_SYMBOL,
        "description": (
            "Isotropic cellular-automaton spaceships, pen-plotted as cards. "
            "Each NFT belongs to whoever holds its card."
        ),
        "image": site + "nft/collection.gif",
        "external_url": site,
        "properties": {
            "files": [{"uri": site + "nft/collection.gif", "type": "image/gif"}],
            "category": "image",
        },
    }


def build(catalog, site, out_dir=OUT_DIR, images=True):
    """Write every file; returns the number of cards."""
    if not site.endswith("/"):
        site += "/"
    os.makedirs(out_dir, exist_ok=True)
    cards = deck_entries(catalog)
    for ship_id, entry in cards:
        meta = metadata_for(ship_id, entry, len(cards), site)
        with open(os.path.join(out_dir, ship_id + ".json"), "w") as f:
            json.dump(meta, f, indent=2)
            f.write("\n")
        if images:
            render_gif(entry, os.path.join(out_dir, ship_id + ".gif"))
    with open(os.path.join(out_dir, "collection.json"), "w") as f:
        json.dump(collection_metadata(site), f, indent=2)
        f.write("\n")
    if images and cards:
        render_gif(cards[0][1], os.path.join(out_dir, "collection.gif"))
    return len(cards)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=os.path.join("web", "catalog.json"))
    parser.add_argument("--site", default=config.SITE_BASE_URL,
                        help="public base URL the files will be served from")
    parser.add_argument("--out", default=OUT_DIR)
    parser.add_argument("--no-images", action="store_true")
    args = parser.parse_args(argv)
    with open(args.catalog) as f:
        catalog = json.load(f)
    n = build(catalog, args.site, args.out, images=not args.no_images)
    print("wrote metadata for %d cards to %s" % (n, args.out))


if __name__ == "__main__":
    main()
