# HANDOFF — Isotropic Automons (pen-plot + NFT edition)

Read this first when picking the project back up. Written 2026-08-01 at
the end of the foundation session. Everything described here is on branch
`claude/isotropic-automata-nft-a9szhi` (not merged to master yet).

## The project in one paragraph

~100 isotropic cellular-automaton spaceships, found by the existing
search pipeline, pen-plotted as physical trading cards (like the g4g
print run, but plotted instead of printed). Each card back has a QR code
that opens a web player where the holder can fly that exact ship and
mint it as a Solana NFT (one specific NFT per card, not a random drop).

## State right now

| Piece | Status |
|---|---|
| Isotropic search (ntzfind + Hensel rules) | ✅ existed before, untouched logic |
| apgcode / gif / QR pipeline (lifelib) | ✅ existed; QRs now point at the player, not Catagolue |
| Web player (`web/`) | ✅ built, works — table-driven engine, URL scheme, demo glider |
| Plotter SVG cards (`src/plot_svg.py`) | ✅ built, works — see `plots/demo/` for output |
| Catalog + NFT metadata generators | ✅ built (`src/build_catalog.py`, `src/nft_metadata.py`) |
| Tests | ✅ 26 passing (`python -m pytest tests/`) |
| Real ~100 ships | ❌ not searched/curated yet |
| Hosting + real domain | ✅ live at https://john-winston.com/automons/ (GitHub Pages, deploys via `.github/workflows/pages.yml`) |
| Solana mint (claim service, wallet connect) | ❌ scaffold + plan only (`chain/README.md`, `web/js/mint.js`) |
| Other repos (g4g site, plotter tooling) | ❓ never inspected — session was scoped to this repo only |

## The three design decisions that matter

1. **No Hensel parser in JavaScript.** The web player runs ships from a
   512-entry transition table (128 hex chars) precomputed in Python,
   using lifelib as the oracle (`src/ruletable.py`). If you ever write a
   JS rule parser, validate it against `ruletable.verify_oracle()`.
   Table bit layout is documented at the top of `src/ruletable.py`;
   `web/js/engine.js` must stay in sync with it.
2. **Everything in the URL fragment** (`#v=1&a=<apgcode>&r=<rule>...`),
   so the player is pure static hosting. Short "catalog" form for card
   QRs (small QR = clean plot); self-contained form (`p=` RLE, `t=`
   table) for permanence. Spec: `src/shipurl.py` ⇄ `web/js/shipurl.js`.
3. **Claim-token mint, not a candy machine.** Cards map to specific
   ships, so the QR carries a single-use HMAC token (`c=` param); a tiny
   serverless endpoint verifies it and mints a Metaplex Core asset to
   the scanner's wallet. Full plan + build order: `chain/README.md`.

## How to run everything

```bash
pip install -r requirements.txt        # lifelib comes from the submodule

python -m pytest tests/                # should be 26 passed

python -m src.build_catalog --demo     # -> web/catalog.json (glider demo)
python -m src.plot_svg --demo --trail 3  # -> plots/demo/*.svg
# open web/index.html in a browser -> glider flies

# once real ships exist (after search + curation):
python -m src.build_catalog --periods 4 5 6 7
python -m src.nft_metadata --periods 4 5 6 7
python -m src.plot_svg --periods 4 5 6 7 --trail 3
```

The original search flow is unchanged: `python main.py` (needs ntzfind
built and Golly for the rle step; run `src/automons.py` inside Golly).
Machine paths now come from `src/config.py` — override with `AUTOMONS_*`
env vars (`AUTOMONS_GOLLY_BASE`, `AUTOMONS_SITE_URL`, etc.).

## Next steps, in order

1. ~~Decide the player domain~~ **Done 2026-08-01**: GitHub Pages project
   site. The repo owner's custom domain applies to all project pages, so
   the canonical URL is `https://john-winston.com/automons/` (baked into
   `src/config.py` as the `SITE_BASE_URL` default).
2. ~~Host `web/`~~ **Done 2026-08-01**: `.github/workflows/pages.yml`
   deploys `web/` on push to `master` or this branch (the `github-pages`
   environment allows both). HTTPS enforced; verified live with
   `#v=1&a=xq4_153&r=b3s23`.
3. **Search + curate the real ~100 ships** with the existing pipeline
   (periods 4/5/6/7 map to common/uncommon/rare/legendary).
4. Run the three generators (catalog, metadata, plots) and test-plot a
   few cards; judge the `--trail` look on paper.
5. **Chain phase** (follow `chain/README.md` build order): upload assets
   to Irys/Arweave → devnet mint script (Metaplex Core + collection) →
   claim service (one POST endpoint, holds the only key) → wallet-adapter
   in `web/js/mint.js` (set `CLAIM_ENDPOINT`) → mainnet.
6. Generate claim tokens, regenerate QR backs with `c=` params, plot.

## Open decisions for the human

- ~~Player domain~~ decided: `https://john-winston.com/automons/`.
- Free claim vs. paid mint (trade-offs in `chain/README.md`).
- Trails on plotted fronts or clean single-generation fronts.
- NFT `image`: the pipeline gif, or a rendered frame of the SVG.
- Claim-token exposure: same QR (photo of card back = mintable) vs.
  scratch-off / second QR inside packaging.

## Gotchas

- `plots/`, `metadata/`, `data/` are gitignored (generated); the two
  demo SVGs were force-added as reference output.
- Building tables for INT rules **requires lifelib** (submodule not
  initialised in fresh clones: `git submodule update --init`). Totalistic
  rules (the demo) need nothing.
- `src/rle.py` ⇄ `web/js/rle.js` and `src/engine.py` ⇄ `web/js/engine.js`
  are mirrored pairs — change both or neither.
- `patterns.json` nodes now have both `url` (player) and `catagolue`
  (reference); old data files generated before this branch lack the
  `catagolue` field.
- The g4g-era raster card pipeline (`src/combine.py`, `template.pdf`)
  still works and was left alone — it's the printed edition, not this one.
- Other repos possibly containing g4g/plotter/QR settings were never
  checked; if they exist, reconcile before finalising card dimensions.
