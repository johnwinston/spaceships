"""Build the deck: own ship ids, catalog, and QR sticker assets.

This replaces the apgcode pipeline (rle2apgcode + build_catalog) as the
source of ship identity.  The deck is self-hosted: each ship gets an id
like ``p4-01`` -- period, then position in the curated order -- plus a
deck-wide edition number 1..N.  Nothing references Catagolue and no
apgcode is computed; lifelib appears only to canonicalize the rule
string for display (pure Python -- it never compiles anything here).

The 512-entry transition table the player runs on comes from ntzrule,
the port of ntzfind's own table generator, so a card animates under
exactly the semantics that found it.  It used to be brute-forced
through lifelib, which compiles a shared object per rule into one
shared directory: under ``--workers 8`` the workers clobbered each
other's generated source, and 82 of 98 cards shipped with another
rule's table and sat frozen in the player.  Deriving the table
arithmetically keeps the build parallel-safe and needs no compiler.

Outputs:
    web/catalog.json     id -> {name, rule, rle, period, rarity, edition,
                                table}  (player + collection read this)
    data/deck.json       id -> {source, period, rule, edition}  (manifest
                                tying ids back to pipeline files)
    qrs/deck/<id>.png    QR sticker art pointing at the player, with the
                         card's claim code underneath when
                         AUTOMONS_CLAIM_SECRET is set (see claimcode.py)

Usage:
    python -m src.build_deck --periods 4 5 6 7 --workers 8
"""
import argparse
import json
import os
import subprocess
import sys

import qrcode
from PIL import Image, ImageDraw, ImageFont

from . import config
from . import shipurl
from . import claimcode
from .apgcode_parallel import chunk, merge_parts

RARITY_BY_PERIOD = {"4": "common", "5": "uncommon", "6": "rare", "7": "legendary"}

PART_DIR = os.path.join("data", "_deck_parts")

# The golden-glider demo entry keeps working QRs/links alive with zero
# pipeline runs; carried over from build_catalog.
GOLDEN_ID = "xq4_153"


def curated_order(periods):
    """(period, filename) for every ship, in deck order.

    Deck order is period ascending, then pattern number ascending -- the
    order curation produced, and the order the plot sheets use.
    """
    out = []
    for period in periods:
        rle_dir = os.path.join(config.PIPELINE_BASE, "rles", str(period))
        files = sorted(
            (f for f in os.listdir(rle_dir) if f.endswith(".rle")),
            key=lambda f: int(f[7:-4]),
        )
        out.extend((str(period), f) for f in files)
    return out


def assign_ids(ordered):
    """id -> (period, filename, edition) for the whole deck."""
    per_period = {}
    deck = {}
    for edition, (period, filename) in enumerate(ordered, start=1):
        per_period[period] = per_period.get(period, 0) + 1
        ship_id = "p%s-%02d" % (period, per_period[period])
        deck[ship_id] = (period, filename, edition)
    return deck


def worker_argv(period, files, part_path):
    """A worker canonicalizes rules and computes tables for its chunk."""
    code = """
import json, sys, re, os
from submodules import lifelib
from src import config, ntzrule, ruletable
period, part = sys.argv[1], sys.argv[2]
out = {}
for name in sys.argv[3:]:
    path = os.path.join(config.PIPELINE_BASE, 'rles', period, name)
    rle = open(path, encoding='utf-8', errors='ignore').read()
    try:
        raw = re.search(r'rule = ([^ \\n]+)', rle).group(1)
        # The table comes from the raw rule, which still carries the
        # b.../s... slash ntzrule parses; the canonical form is for
        # display only.
        table = ntzrule.neigh_order_table(raw)
        rule = ruletable.canonical_rule(raw, lifelib)
        out[name] = {
            'rule': rule,
            'rle': re.sub(r'rule = [^ \\n]+', 'rule = ' + rule, rle),
            'table': ruletable.table_to_hex(table),
        }
    except Exception as exc:
        print('%s failed: %s' % (name, exc), file=sys.stderr)
json.dump(out, open(part, 'w'))
"""
    return [sys.executable, "-c", code, str(period), part_path] + files


QR_PX = 450
CODE_BAND_PX = 70
CODE_FONT_PX = 40


def sticker_image(qr_img, code=None):
    """The QR alone, or the QR with the claim code set underneath it."""
    qr_img = qr_img.convert("RGB").resize((QR_PX, QR_PX))
    if not code:
        return qr_img
    img = Image.new("RGB", (QR_PX, QR_PX + CODE_BAND_PX), "white")
    img.paste(qr_img, (0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=CODE_FONT_PX)
    left, top, right, bottom = draw.textbbox((0, 0), code, font=font)
    x = (QR_PX - (right - left)) / 2 - left
    y = QR_PX + (CODE_BAND_PX - (bottom - top)) / 2 - top - 8
    draw.text((x, y), code, fill="black", font=font)
    return img


def write_qr(ship_id, url, out_dir, code=None):
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = sticker_image(qr.make_image(), code)
    img.save(os.path.join(out_dir, ship_id + ".png"))


def golden_entry():
    from . import ruletable
    return {
        "name": "golden glider",
        "rule": "b3s23",
        "rle": "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!",
        "period": "life",
        "rarity": "golden",
        "edition": 0,
        "table": ruletable.table_to_hex(ruletable.totalistic_table("b3s23")),
    }


def verify_catalog(catalog):
    """Ids whose stored table does not fly their own ship.

    The catalog is the only thing the player reads, so this checks the
    shipped artefact rather than the inputs: decode the table, evolve
    the RLE for `period` generations, and require the pattern to come
    back to its own shape somewhere else on the plane.  A build that
    hands a card the wrong rule leaves it sitting still, which is
    exactly the failure this catches.
    """
    from . import engine, rle, ruletable

    broken = []
    for ship_id, entry in catalog.items():
        if entry["period"] == "life":
            continue
        cells = set(rle.parse(entry["rle"])[0])
        table = ruletable.table_from_hex(entry["table"])
        moved = cells
        for _ in range(int(entry["period"])):
            moved = engine.step(moved, table)
        if not moved or len(moved) != len(cells):
            broken.append(ship_id)
            continue
        origin = (min(x for x, _ in cells), min(y for _, y in cells))
        shifted = (min(x for x, _ in moved), min(y for _, y in moved))
        same_shape = (
            sorted((x - origin[0], y - origin[1]) for x, y in cells)
            == sorted((x - shifted[0], y - shifted[1]) for x, y in moved)
        )
        if not same_shape or origin == shifted:
            broken.append(ship_id)
    return broken


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periods", nargs="+", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    ordered = curated_order(args.periods)
    deck = assign_ids(ordered)
    print("deck: %d ships across periods %s" % (
        len(deck), ", ".join(args.periods)))

    # fan the per-period file lists out to workers
    os.makedirs(PART_DIR, exist_ok=True)
    jobs = []
    for period in args.periods:
        files = [f for p, f in ordered if p == str(period)]
        for i, part_files in enumerate(chunk(files, args.workers)):
            part = os.path.join(PART_DIR, "p%s_part%d.json" % (period, i))
            jobs.append((str(period), part, subprocess.Popen(
                worker_argv(period, part_files, part),
                stdout=subprocess.DEVNULL,
            )))
    for _, _, proc in jobs:
        proc.wait()

    computed = {}  # (period, filename) -> worker entry
    for period in args.periods:
        parts = [p for per, p, _ in jobs if per == str(period) and os.path.exists(p)]
        for filename, entry in merge_parts(parts).items():
            computed[(str(period), filename)] = entry

    qr_dir = os.path.join("qrs", "deck")
    os.makedirs(qr_dir, exist_ok=True)
    secret = claimcode.claim_secret(required=False)
    if not secret:
        print("note: %s not set -- QR stickers will carry no claim code"
              % config.CLAIM_SECRET_ENV)
    catalog = {GOLDEN_ID: golden_entry()}
    manifest = {}
    missing = []
    for ship_id, (period, filename, edition) in deck.items():
        entry = computed.get((period, filename))
        if entry is None:
            missing.append(ship_id)
            continue
        catalog[ship_id] = {
            "name": ship_id,
            "rule": entry["rule"],
            "rle": entry["rle"],
            "period": period,
            "rarity": RARITY_BY_PERIOD.get(period, "legendary"),
            "edition": edition,
            "table": entry["table"],
        }
        manifest[ship_id] = {
            "source": "ntzfind_patterns/%s/%s" % (period, filename[:-4] + ".lif"),
            "period": period,
            "rule": entry["rule"],
            "edition": edition,
        }
        write_qr(ship_id, shipurl.player_url(ship_id=ship_id), qr_dir,
                 code=claimcode.claim_code(ship_id, secret) if secret else None)

    broken = verify_catalog(catalog)
    if broken:
        raise SystemExit(
            "refusing to write catalog: %d of %d cards do not fly under "
            "their own stored table (%s)"
            % (len(broken), len(catalog) - 1, ", ".join(broken[:8]))
        )

    with open(os.path.join("web", "catalog.json"), "w") as f:
        json.dump(catalog, f, indent=2)
    os.makedirs("data", exist_ok=True)
    with open(os.path.join("data", "deck.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    for _, part, _ in jobs:
        if os.path.exists(part):
            os.remove(part)

    print("catalog: %d entries -> web/catalog.json" % len(catalog))
    print("qr stickers: %d -> %s/" % (len(manifest), qr_dir))
    if missing:
        print("MISSING (worker failures): %s" % ", ".join(missing))


if __name__ == "__main__":
    main()
