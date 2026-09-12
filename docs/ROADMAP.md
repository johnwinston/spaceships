# Spaceships — pen-plotted spaceship cards, claimable by their holders

The vision: ~100 isotropic cellular-automaton spaceships, pen-plotted as
physical cards (like the g4g run), each with a QR code on the back that
opens a web player where the holder can fly their ship and mint it as a
Solana NFT.

## What the repo already covered vs. what was missing

| Capability | Status before this branch |
|---|---|
| Isotropic rule search | **Already there.** `auto_ntzfind.py` generates random Hensel INT rules (`b2ce3aiy…/s…`) and drives `ntzfind` — the searches were always isotropic non-totalistic. |
| Canonical ship identity (apgcode) | **Already there** via lifelib in `rle2apgcode.py`. |
| QR generation | **Partially.** QRs existed but pointed to Catagolue, not an interactive page. |
| Card artwork + print sheets | **Raster only** (`combine.py`, PNG sheets for printing) — not plotter-compatible. |
| Curation UI | Already there (`cleanup.py` tkinter keep/delete). |
| Pen-plotter output (SVG) | **Missing** → added `src/plot_svg.py`. |
| Interactive web player | **Missing** → added `web/` (static, table-driven engine). |
| URL scheme linking card → player | **Missing** → added `src/shipurl.py` + `web/js/shipurl.js`. |
| NFT metadata | **Missing** → added `src/nft_metadata.py` (Metaplex standard). |
| Card claims | **Missing** → added `src/claimcode.py` (codes on the backs) + `worker/` (claim service) + claim UI in `web/`. |
| Solana mint | **Missing** → plan in `chain/README.md`; would build on the claim record. |
| Portability | Paths were hard-coded to one machine → centralised in `src/config.py`. |

## Architecture

```
 search (existing)                 new foundation
┌──────────────────┐   patterns.json   ┌────────────────────────────┐
│ auto_ntzfind     │──────────────────▶│ build_catalog ─▶ web/catalog.json
│  └─ ntzfind      │                   │ nft_metadata  ─▶ metadata/*.json
│ lif2rle headless │                   │ plot_svg      ─▶ plots/*_{front,back}.svg
│ rle2apgcode      │                   └────────────────────────────┘
│  └─ lifelib ─────┼── transition-table oracle ──┐
└──────────────────┘                             ▼
                                   web player (static hosting)
                                   scan QR ─▶ fly ship ─▶ claim (worker/ + KV)
```

**The key design decision — transition tables, not a JS rule parser.**
Hensel INT notation is easy to implement subtly wrong. Instead of parsing
rules in JavaScript, the pipeline brute-forces all 512 local
configurations through **lifelib** (already the pipeline's source of
truth) into a 128-hex-char table (`src/ruletable.py`), which ships inside
`web/catalog.json` or the URL itself. The JS engine (`web/js/engine.js`)
is a dumb table lookup — identical behaviour to lifelib by construction.
Totalistic rules (the golden glider) work with no table at all.

**URL scheme** (`src/shipurl.py` ⇄ `web/js/shipurl.js`), all in the
fragment so static hosting works:

- Production card: `https://<site>/#v=1&a=<apgcode>&r=<rule>&c=<claim>`
  (short → small QR → clean plot; player fetches catalog.json)
- Self-contained: `…#v=1&r=<rule>&p=<b64url-rle>&t=<128-hex-table>`
  (no catalog needed; survives even if the catalog moves)

## Phases

**Phase 0 — foundation (this branch).** Core modules, web player, plotter
SVG output, metadata generator, docs, tests. Done.

**Phase 1 — content.** Run the search for the ~100 ships (existing
pipeline), curate, then: `build_catalog --periods …`, `nft_metadata`,
`plot_svg --periods … --trail 3`. Pick names. Test-plot a few cards.

**Phase 2 — hosting.** Put `web/` on GitHub Pages (or any static host)
under the real domain; set `AUTOMONS_SITE_URL`; regenerate QR codes/backs.
Nice-to-haves: soup search mode, rule editing (needs a JS Hensel parser —
validate any implementation against `ruletable.verify_oracle`).

**Phase 3 — claims.** Done in code (2026-09-08): `worker/` verifies the
code plotted under each QR and records who holds the card; the
collection page shows it. Deploy per `worker/README.md`. A Solana mint,
if ever wanted, hangs off the same claim record (`chain/README.md`).

**Phase 4 — production run.** Set `AUTOMONS_CLAIM_SECRET`, rebuild the
deck (stickers) or sheets (plotted backs) so every back carries its
code, plot, and print the private code sheet for the booth.

## Open decisions

1. Real domain for the player (affects every QR — decide before plotting).
2. Free claim vs. paid mint (see chain/README.md).
3. Trail aesthetics on the plotted fronts (`--trail N`, layer per pen).
4. Whether the gif or a rendered SVG frame becomes the NFT `image`.

## Related work in other repos

None any more. The old `plotter` repo (the G4G Game of Life plotting
tool plus the AxiDraw operating notes) was folded into this one on
2026-09-12 as `plotter/` and `docs/OPERATING.md`, and archived on
GitHub. The original g4g ship data is gone; content comes from a fresh
search.
