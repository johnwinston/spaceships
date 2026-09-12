"""Parallel driver for rle2apgcode.

The serial pipeline spent minutes per ship: a GIF render nobody needs
now (the player animates ships live; the NFT artwork is a card scan),
plus a per-pattern cache purge that recompiled every rule from cold.
This driver splits each period's RLEs across worker processes, skips
GIFs, cleans the lifelib cache once at the very end, and merges the
workers' part files into the usual data/<period>/patterns.json.

Workers are separate processes (not threads: lifelib compiles and loads
per-rule shared objects, which is safe concurrently as long as nothing
deletes them mid-run -- which is exactly what cleanup_each did).

Usage:
    python -m src.apgcode_parallel --periods 4 5 6 7 --workers 8
    python -m src.apgcode_parallel --periods 4 --workers 4 --gifs
"""
import argparse
import json
import os
import subprocess
import sys

from . import config

PART_DIR = os.path.join("data", "_apgcode_parts")


def chunk(items, n):
    """Split items into at most n runs of near-equal length, in order."""
    n = max(1, min(n, len(items)))
    size, extra = divmod(len(items), n)
    out, start = [], 0
    for i in range(n):
        end = start + size + (1 if i < extra else 0)
        out.append(items[start:end])
        start = end
    return [c for c in out if c]


def merge_parts(part_paths):
    """Combine worker part files; later files win on (impossible) clashes."""
    merged = {}
    for path in part_paths:
        with open(path) as f:
            merged.update(json.load(f))
    return merged


def worker_argv(period, files, part_path, gifs):
    code = (
        "from submodules import lifelib\n"
        "from src.rle2apgcode import RLE2APGCODE\n"
        "import json,sys\n"
        "period,part,gifs=sys.argv[1],sys.argv[2],sys.argv[3]=='1'\n"
        "files=sys.argv[4:]\n"
        "RLE2APGCODE(lifelib,period).run(files=files,make_gifs=gifs,"
        "out_path=part,cleanup_each=False)\n"
    )
    return [sys.executable, "-c", code, str(period), part_path,
            "1" if gifs else "0"] + files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--periods", nargs="+", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--gifs", action="store_true",
                        help="also render GIFs (slow; only needed when "
                             "gifs are the token artwork)")
    args = parser.parse_args()

    os.makedirs(PART_DIR, exist_ok=True)
    jobs = []  # (period, part_path, Popen)
    for period in args.periods:
        rle_dir = os.path.join(config.PIPELINE_BASE, "rles", str(period))
        files = sorted(f for f in os.listdir(rle_dir) if f.endswith(".rle"))
        for i, part_files in enumerate(chunk(files, args.workers)):
            part = os.path.join(PART_DIR, "p%s_part%d.json" % (period, i))
            jobs.append((period, part, subprocess.Popen(
                worker_argv(period, part_files, part, args.gifs),
                stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
            )))

    failed = 0
    for period, part, proc in jobs:
        if proc.wait() != 0:
            failed += 1
            print("worker failed: period %s -> %s" % (period, part))
    if failed:
        print("%d workers failed; parts kept in %s" % (failed, PART_DIR))

    for period in args.periods:
        parts = [p for per, p, _ in jobs if per == period and os.path.exists(p)]
        merged = merge_parts(parts)
        out_dir = os.path.join("data", str(period))
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "patterns.json")
        with open(out, "w") as f:
            json.dump(merged, f, indent=4)
        done = sum(1 for v in merged.values() if v.get("apgcode"))
        print("period %s: %d/%d ships -> %s" % (period, done, len(merged), out))
        for p in parts:
            os.remove(p)

    # one cache purge for the whole run, in place of one per pattern
    pythlib = os.path.join("submodules", "lifelib", "pythlib")
    if os.path.isdir(pythlib):
        for name in os.listdir(pythlib):
            if name.endswith(".so"):
                os.remove(os.path.join(pythlib, name))


if __name__ == "__main__":
    main()
