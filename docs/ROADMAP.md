# Isotropic Automons — pen-plotted spaceship cards with mintable NFTs

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
| Solana mint | **Missing** → plan + scaffolding in `chain/README.md`, `web/js/mint.js`. |
| Portability | Paths were hard-coded to one machine → centralised in `src/config.py`. |

## Architecture

```
 search (existing)                 new foundation
┌──────────────────┐   patterns.json   ┌────────────────────────────┐
│ auto_ntzfind     │──────────────────▶│ build_catalog ─▶ web/catalog.json
│  └─ ntzfind      │                   │ nft_metadata  ─▶ metadata/*.json
│ golly (automons) │                   │ plot_svg      ─▶ plots/*_{front,back}.svg
│ rle2apgcode      │                   └────────────────────────────┘
│  └─ lifelib ─────┼── transition-table oracle ──┐
└──────────────────┘                             ▼
                                   web player (static hosting)
                                   scan QR ─▶ fly ship ─▶ mint (claim service)
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

**Phase 3 — chain.** Follow `chain/README.md`: devnet mint of Core
assets, claim service, wallet-adapter in `mint.js`, then mainnet.

**Phase 4 — production run.** Generate claim tokens, final QR SVGs, plot
fronts + backs, scratch-off stickers if desired.

## Open decisions

1. Real domain for the player (affects every QR — decide before plotting).
2. Free claim vs. paid mint (see chain/README.md).
3. Trail aesthetics on the plotted fronts (`--trail N`, layer per pen).
4. Whether the gif or a rendered SVG frame becomes the NFT `image`.

## Related work in other repos

This session only had access to `automons`. If the g4g site, plotter
tooling (e.g. AxiDraw scripts), or any wallet/mint experiments live in
other repos, add them to a session and reconcile — most useful would be
the g4g QR/print settings and any existing plotter workflow.
