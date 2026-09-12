# spaceships

Isotropic cellular-automaton spaceships: searched, curated, pen-plotted as
physical cards, playable in a browser, claimable by whoever buys the card.
(The repo keeps its old name, `automons`; the ships, site and cards are
"spaceships".)

**Start here: [docs/ROADMAP.md](docs/ROADMAP.md)** — what exists, what's
planned, and the architecture. Solana plan: [chain/README.md](chain/README.md).

## Search pipeline (existing)

```
./src/auto_ntzfind.py
    -- generates random isotropic (Hensel) rules, runs ntzfind,
       creates Life 1.05 files under data/pipeline/

./src/lif2rle.py
    -- headless Life 1.05 -> RLE conversion (replaced the old
       run-inside-Golly step, src/automons.py)

./src/rle2apgcode.py
    -- reads the rles, canonicalises the rule + gets the apgcode via
       lifelib (x86 venv -- see docs/HANDOFF.md), creates the QR code
       (points at the web player), saves patterns.json

./src/cleanup.py
    -- tkinter keep/delete curation of generated ships

./src/combine.py
    -- legacy raster card sheets (the printed g4g edition)
```

Machine-specific paths now live in `src/config.py` (override with
`AUTOMONS_*` environment variables). Set `AUTOMONS_SITE_URL` to the real
player domain before generating production QR codes.

## New foundation (pen-plot + web + NFT edition)

```
python -m src.build_catalog --demo --periods 4 5 6 7
    -- patterns.json -> web/catalog.json with per-rule transition
       tables (lifelib is the oracle for INT rules)

python -m src.nft_metadata --periods 4 5 6 7
    -- patterns.json -> metadata/<p>/<apgcode>.json (Metaplex standard)

python -m src.plot_svg --demo --trail 3
python -m src.plot_svg --periods 4 5 6 7 --trail 3
    -- plotter-ready SVG card faces in real mm: front = ship (+ motion
       trail layers, one pen each), back = QR code as a single path

web/
    -- static site, any host: index.html lists every ship in the deck
       with its claim; play.html (what the QR codes open) flies one
       ship and takes the claim code printed on the card back.

worker/
    -- the claim service (Cloudflare Worker + KV) behind the claim
       form.  Deploy + booth-day notes: worker/README.md.

AUTOMONS_CLAIM_SECRET=... python -m src.claimcode --deck data/deck.json
    -- every card's claim code (HMAC of its id; the same secret goes
       into the worker).  build_deck and impose plot the code under
       the QR when the secret is set.
```

## Plotting on the AxiDraw

[docs/OPERATING.md](docs/OPERATING.md) is the machine procedure: saxi
setup and its local patches, pen calibration, homing, the flags every
pass uses and why. The sheet scripts in `scripts/` encode the same
settings:

```
python3 scripts/bake_plot_svg.py ...   # imposed sheet -> flat px SVG per pass
scripts/plot_sheet_cards.sh s01        # plot one sheet, card by card
scripts/plot_cuts.sh                   # cut lines only
```

`plotter/` is the original Game of Life plotting tool (the G4G cards),
folded in from the old `plotter` repo on 2026-09-12: single-pattern
panels and grids from an RLE, with `--table` for isotropic rules. See
[plotter/README.md](plotter/README.md).

## Setup + tests

```
./scripts/setup_mac.sh    # venvs (arm64 + Rosetta/x86 for lifelib),
                          # ntzfind build, submodule patch, smoke tests
pytest                    # 139 passed (tests/ + plotter/tests/)
```

The JS engine mirrors `src/engine.py`/`src/ruletable.py`; if you touch
either side, keep them in sync (table layout is documented in
`src/ruletable.py`).
