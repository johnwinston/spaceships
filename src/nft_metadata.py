"""Generate Metaplex-standard NFT metadata JSON from patterns.json.

One JSON file per ship, ready to upload (Irys/Arweave or similar) before
minting on Solana.  See chain/README.md for the full mint plan.

Usage:
    python -m src.nft_metadata --periods 4 5 6 7
    python -m src.nft_metadata --periods 4 --image-base https://arweave.net/<dir>/

Output: metadata/<period>/<apgcode>.json

The ``image`` field defaults to the gif filename the existing pipeline
already produces (gifs/<period>/<apgcode>.gif); pass --image-base once the
gifs are uploaded and re-run to bake in the permanent URIs.
"""
import argparse
import json
import os

from . import config
from . import shipurl

RARITY_BY_PERIOD = {"4": "common", "5": "uncommon", "6": "rare", "7": "legendary"}


def metadata_for(node, period, name, image_uri):
    apgcode = node["apgcode"]
    rule = node["rule"]
    play_url = shipurl.player_url(apgcode=apgcode, rule=rule)
    rarity = RARITY_BY_PERIOD.get(str(period), "legendary")
    return {
        "name": name or apgcode,
        "symbol": config.NFT_SYMBOL,
        "description": config.NFT_DESCRIPTION,
        "seller_fee_basis_points": config.NFT_SELLER_FEE_BASIS_POINTS,
        "image": image_uri,
        "animation_url": play_url,
        "external_url": play_url,
        "attributes": [
            {"trait_type": "rule", "value": rule},
            {"trait_type": "period", "value": str(period)},
            {"trait_type": "apgcode", "value": apgcode},
            {"trait_type": "rarity", "value": rarity},
            {"trait_type": "catagolue", "value": shipurl.catagolue_url(apgcode, rule)},
        ],
        "properties": {
            "files": [{"uri": image_uri, "type": "image/gif"}],
            "category": "image",
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periods", nargs="+", required=True)
    parser.add_argument("--image-base", default="",
                        help="URI prefix for uploaded gifs; default = local filename")
    parser.add_argument("--names", default="",
                        help="optional JSON file mapping apgcode -> display name")
    args = parser.parse_args()

    names = {}
    if args.names:
        with open(args.names) as f:
            names = json.load(f)

    total = 0
    for period in args.periods:
        with open(os.path.join("data", str(period), "patterns.json")) as f:
            patterns = json.load(f)
        out_dir = os.path.join("metadata", str(period))
        os.makedirs(out_dir, exist_ok=True)
        for filename, node in patterns.items():
            apgcode = node.get("apgcode")
            if not apgcode:
                print("skipping %s (no apgcode)" % filename)
                continue
            image_uri = (args.image_base + apgcode + ".gif") if args.image_base \
                else (apgcode + ".gif")
            meta = metadata_for(node, period, names.get(apgcode), image_uri)
            with open(os.path.join(out_dir, apgcode + ".json"), "w") as f:
                json.dump(meta, f, indent=2)
            total += 1
    print("wrote %d metadata files" % total)


if __name__ == "__main__":
    main()
