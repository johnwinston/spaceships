# HANDOFF — Spaceships (pen-plot edition)

Read this first when picking the project back up. Written 2026-08-01 at
the end of the foundation session; updated 2026-08-06 after porting the
whole pipeline to the Apple Silicon Mac (Golly removed, lifelib under
Rosetta, QR backs made plottable). Everything described here is on branch
`claude/isotropic-automata-nft-a9szhi` (not merged to master yet).

## The project in one paragraph

~100 isotropic cellular-automaton spaceships, found by the existing
search pipeline, pen-plotted as physical trading cards (like the g4g
print run, but plotted instead of printed). Each card back has a QR code
that opens a web player where the holder can fly that exact ship and
claim it with the code plotted under the QR; the collection page
(`web/index.html`) lists every ship and who holds it.

## State right now

| Piece | Status |
|---|---|
| Isotropic search (ntzfind + Hensel rules) | ✅ runs on the Mac — ntzfind built at `submodules/ntzfind/ntzfind`, Golly no longer needed (`src/lif2rle.py` replaced it) |
| apgcode / gif / QR pipeline (lifelib) | ✅ runs on the Mac under Rosetta (`.venv-x86`); searched rules are canonicalised via lifelib (`ruletable.canonical_rule`) |
| Web player (`web/`) | ✅ built, works — table-driven engine, URL scheme, demo glider |
| Plotter SVG cards (`src/plot_svg.py`) | ✅ works; QR backs are now stroke-hatched (pen-plottable), no fills anywhere |
| Catalog + NFT metadata generators | ✅ built and exercised on a real searched INT ship |
| Tests | ✅ 41 passing (bare `pytest` works — root `conftest.py` + `pytest.ini`) |
| Real ~100 ships | ❌ not searched/curated yet — but the full pipeline was proven end-to-end on 2026-08-06 with one freshly searched p4 ship (`xq4_1vl0o88o0lv1z0aa7y07aazy07w7`) |
| Curation UI (`src/cleanup.py`) | ✅ tkinter installed (`python-tk@3.14`), imports clean in the arm venv |
| Hosting + real domain | ✅ live at https://john-winston.com/automons/ (GitHub Pages, deploys via `.github/workflows/pages.yml`) |
| Card claims (`src/claimcode.py`, `worker/`, claim UI in `web/`) | ✅ built + tested 2026-09-08; **not deployed** — follow `worker/README.md`, then set `CLAIM_ENDPOINT` in `web/js/config.js` |
| Solana mint | ❌ plan only (`chain/README.md`); would build on the claim record |
| Plotter hardware/software | ❌ AxiDraw is the target; no axicli/saxi/Inkscape installed yet, no device seen on USB |
| Other repos (g4g site, plotter tooling) | ❓ never inspected — original g4g data is gone; content will come from a fresh search |

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
3. **Claims are a code, not a token in the QR.** Each back carries a
   short code (`XXXX-XXXX`, HMAC of the ship id under
   `AUTOMONS_CLAIM_SECRET`) plotted under the QR; the QR itself only
   opens the player. The holder types the code on `play.html` and
   `worker/` records the claim in KV; `index.html` lists every ship with
   its claim. The QR *can* carry the code (`c=`) for one-tap claiming,
   but then a photo of the back is enough to claim — leave it off unless
   the code is under a scratch-off.

## How to run everything

```bash
./scripts/setup_mac.sh   # one shot: submodules, cpads patch, ntzfind,
                         # .venv (arm64) + .venv-x86 (Rosetta), smoke tests
```

Two venvs, one rule: **anything that imports lifelib runs in
`.venv-x86`** (lifelib's avxlife is x86 assembly; Rosetta 2 runs it,
SSE4.2). Everything else — tests, search, totalistic demo — uses the
arm64 `.venv`.

```bash
.venv/bin/pytest                                 # 41 passed

# search -> lif -> rle (arm64, headless — no Golly):
.venv/bin/python main.py                         # interactive driver, or:
.venv/bin/python -c "from src.auto_ntzfind import AUTO_NTZFIND; AUTO_NTZFIND(25, 4).run()"
.venv/bin/python -m src.lif2rle --periods 4

# apgcode/gif/qr + catalog + metadata + plots (x86, lifelib):
.venv-x86/bin/python -c "from submodules import lifelib; from src.rle2apgcode import RLE2APGCODE; RLE2APGCODE(lifelib, 4).run()"
.venv-x86/bin/python -m src.build_catalog --periods 4 5 6 7
.venv-x86/bin/python -m src.nft_metadata --periods 4 5 6 7
.venv-x86/bin/python -m src.plot_svg --periods 4 5 6 7 --trail 3
```

Machine paths come from `src/config.py` — search intermediates default
to the repo-local `data/pipeline/` (override `AUTOMONS_PIPELINE_BASE`;
the old `AUTOMONS_GOLLY_BASE` env var still works). Pen width for the
plots is `AUTOMONS_PEN_MM` (default 0.35).

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
   (periods 4/5/6/7 map to common/uncommon/rare/legendary). The pipeline
   is proven end-to-end on this Mac, curation UI included. Install
   AxiDraw tooling (`saxi` via npm, or `pyaxidraw`) before the test
   plots.
4. Run the three generators (catalog, metadata, plots) and test-plot a
   few cards; judge the `--trail` look on paper.
5. **Claims** are built (`worker/`, `src/claimcode.py`, claim UI in
   `web/`). A Solana mint, if wanted later, follows `chain/README.md`
   on top of the claim record.
6. Deploy the claim service (`worker/README.md`), set `CLAIM_ENDPOINT`
   in `web/js/config.js`, export the same secret as
   `AUTOMONS_CLAIM_SECRET`, rebuild stickers/sheets so the backs carry
   codes, plot.

## Open decisions for the human

- ~~Player domain~~ decided: `https://john-winston.com/automons/`.
- Free claim vs. paid mint (trade-offs in `chain/README.md`).
- Trails on plotted fronts or clean single-generation fronts.
- NFT `image`: the pipeline gif, or a rendered frame of the SVG.
- Scratch-off over the plotted claim code, or trust the booth.
- Whether the GitHub repo/Pages path should also become `spaceships`
  (changes every printed URL — decide before plotting).

## Gotchas

- **lifelib only runs under Rosetta** on this Mac (x86 assembly, no
  arm64 port — confirmed against lifelib 2.5.7). Anything importing it
  must use `.venv-x86`. Importing the package on arm64 is fine; only
  `load_rules` (which compiles) fails.
- **The cpads patch is a local, uncommitted edit inside the lifelib
  submodule** (clang 21 rejects `\033` escapes in `static_assert`
  messages). `git submodule update` reverts it — re-run
  `./scripts/setup_mac.sh` (idempotent) after touching submodules.
- **Searched rules are non-canonical** (auto_ntzfind emits clauses in
  random order); lifelib refuses them. `ruletable.canonical_rule()`
  canonicalises via lifelib itself, and `rle2apgcode` rewrites RLE
  headers to the canonical form before anything is stored. The canonical
  rule is the identity everywhere (URLs, catalog, metadata).
- `plots/`, `metadata/`, `data/` are gitignored (generated); the demo
  SVGs were force-added as reference output.
- Building tables for INT rules **requires lifelib** (submodule not
  initialised in fresh clones: `git submodule update --init`). Totalistic
  rules (the demo) need nothing.
- `src/rle.py` ⇄ `web/js/rle.js` and `src/engine.py` ⇄ `web/js/engine.js`
  are mirrored pairs — change both or neither.
- QR backs are hatch-filled strokes sized by `AUTOMONS_PEN_MM`; a back is
  ~1,100–1,500 strokes / ~2.1 m of ink. The claim code is plotted as
  stroke text under the QR, so the URL (and the QR) stays short; putting
  the code in the QR (`c=`) would add modules.
- `web/index.html` is the collection; QR links (`/#v=1&a=p4-01`) are
  bounced to `play.html` by an inline script in its `<head>` — keep that
  shim or every printed card breaks.
- `src/automons.py` is the old in-Golly script, kept for reference only;
  `src/lif2rle.py` replaced it.
- The g4g-era raster card pipeline (`src/combine.py`, `template.pdf`)
  still works and was left alone — it's the printed edition, not this one.
- The g4g-era ship data is gone (nothing on this Mac or its backups);
  the ~100 ships will come from a fresh search.
