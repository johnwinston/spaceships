"""Build web/catalog.json from the pipeline's patterns.json files.

The catalog is what the web player fetches when a QR link uses the short
``a=<apgcode>`` form.  Each entry carries everything the player needs to
run the ship: rule, RLE, and the precomputed 512-entry transition table.

Usage:
    python -m src.build_catalog --periods 4 5 6 7      # from data/<p>/patterns.json
    python -m src.build_catalog --demo                 # golden-glider demo entry

Building tables for INT rules requires lifelib (same dependency the rest
of the pipeline already uses); totalistic rules work without it.
"""
import argparse
import json
import os

from . import rle as rle_codec
from . import ruletable

RARITY_BY_PERIOD = {"4": "common", "5": "uncommon", "6": "rare", "7": "legendary"}

GLIDER_RLE = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!"


def load_lifelib():
    try:
        from submodules import lifelib
        return lifelib
    except Exception:
        return None


def demo_entries():
    """A catalog the player can use with zero pipeline runs."""
    return {
        "xq4_153": {
            "name": "golden glider",
            "rule": "b3s23",
            "rle": GLIDER_RLE,
            "period": "life",
            "rarity": "golden",
            "table": ruletable.table_to_hex(ruletable.totalistic_table("b3s23")),
        }
    }


def entries_from_patterns(period, lifelib):
    path = os.path.join("data", str(period), "patterns.json")
    with open(path) as f:
        patterns = json.load(f)

    entries = {}
    table_cache = {}
    skipped = []
    for filename, node in patterns.items():
        apgcode = node.get("apgcode")
        rule = node.get("rule")
        rle_text = node.get("rle")
        if not apgcode or not rule or not rle_text:
            skipped.append(filename)
            continue
        if rule not in table_cache:
            try:
                table_cache[rule] = ruletable.table_to_hex(
                    ruletable.table_for_rule(rule, lifelib)
                )
            except ValueError as e:
                print("!! %s: %s" % (filename, e))
                skipped.append(filename)
                continue
        cells, _ = rle_codec.parse(rle_text)
        entries[apgcode] = {
            "name": node.get("name", ""),
            "rule": rule,
            "rle": rle_codec.serialize(cells, rule),
            "period": str(period),
            "rarity": RARITY_BY_PERIOD.get(str(period), "legendary"),
            "table": table_cache[rule],
        }
    if skipped:
        print("skipped %d entries without full data: %s" % (len(skipped), skipped))
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periods", nargs="*", default=[],
                        help="periods to include, e.g. 4 5 6 7")
    parser.add_argument("--demo", action="store_true",
                        help="include the golden-glider demo entry")
    parser.add_argument("--out", default="web/catalog.json")
    args = parser.parse_args()

    catalog = {}
    if args.demo:
        catalog.update(demo_entries())

    lifelib = load_lifelib() if args.periods else None
    if args.periods and lifelib is None:
        print("note: lifelib not importable — only totalistic rules will build")
    for period in args.periods:
        catalog.update(entries_from_patterns(period, lifelib))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(catalog, f, indent=2)
    print("wrote %d ships to %s" % (len(catalog), args.out))


if __name__ == "__main__":
    main()
