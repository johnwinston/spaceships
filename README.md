# automons

Isotropic cellular-automaton spaceships: searched, curated, pen-plotted as
physical cards, playable in a browser, mintable as Solana NFTs.

**Start here: [docs/ROADMAP.md](docs/ROADMAP.md)** — what exists, what's
planned, and the architecture. Solana plan: [chain/README.md](chain/README.md).

## Search pipeline (existing)

```
./src/auto_ntzfind.py
    -- generates random isotropic (Hensel) rules, runs ntzfind,
       creates Life 1.05 files in the golly folder

./src/automons.py
    -- run in golly to create rles of Life 1.05 files

./src/rle2apgcode.py
    -- reads rles from golly, gets the apgcode via lifelib,
       creates the QR code (points at the web player), saves patterns.json

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
    -- static player page the QR codes open: fly the ship, edit cells,
       mint button (scaffold). Works from any static host.
```

## Tests

```
pip install pillow qrcode pytest
python -m pytest tests/
```

The JS engine mirrors `src/engine.py`/`src/ruletable.py`; if you touch
either side, keep them in sync (table layout is documented in
`src/ruletable.py`).
