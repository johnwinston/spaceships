# AxiDraw operating notes

Consolidated 2026-09-12 from the old plotter repo's OPERATING.md
(hard-won on the 2026-08-06 and 2026-08-23 plots) and the sheet scripts
in `scripts/`, which are the current source of truth for machine
settings. Where the two disagreed the scripts win, and the withdrawn
advice is called out so nobody reinstates it.

## One-time setup (done on the M1 MacBook)

- Driver: `saxi` (`npm install -g saxi`). The CLI in saxi 0.x is broken
  out of the box and is **locally patched** in
  `/opt/homebrew/lib/node_modules/saxi/dist/server/cli.js`:
  1. `new Window()` → `createSVGWindow()` (svgdom API change)
  2. added `penHome: {x: 0, y: 0}` to `planOptions` (CLI never sets it)
  Reinstalling/upgrading saxi wipes both patches — reapply or re-derive.
- Device shows up as `/dev/cu.usbmodem2101` (EiBotBoard); the scripts
  find it with `ls /dev/cu.usbmodem*`. If plots ever say "Couldn't
  connect", check `ioreg -p IOUSB | grep EiBot`.

## Physical setup

1. Letter stock **landscape relative to the machine** (long side along
   the wide x-travel). Designs are portrait; the bake step rotates them
   (below). saxi's `--landscape` only swaps the paper dimensions and
   never rotates the drawing.
2. Carriage at **home** = top-left corner of the drawing area. The
   machine has no sensors: wherever the carriage sits when a plot starts
   *is* (0,0). `scripts/plotter_home.sh` sends it there.
3. Tape the sheet down. Registration matters for multi-pass sheets and
   for an aligned overdraw (below).

## Pen calibration (repeat when swapping pens)

1. `saxi pen 62 --device /dev/cu.usbmodem2101` — arm to the resting
   (clamping) height.
2. Loosen the clamp, let the nib rest on the paper under the pen's own
   weight, and tighten right there.
3. Plot with **down = 68** (5% below the clamping height = flex that
   keeps ink flowing; 2026-08-23: down at the clamp height itself
   plotted mostly dry).
4. Pen up: the scripts use **20** with explicit lift/drop timing
   (`--pen-lift-duration 0.35 --pen-drop-duration 0.25`). saxi's
   default 50 was not enough clearance (the pen dragged during travel);
   the August plots used 40.

## Homing and aborting

`scripts/plotter_home.sh` raises the pen (`SP,1`) and returns the
carriage with the board's `HM` command. saxi zeroes the board's step
counter at true home at the start of every run, so HM is always safe:
a kill mid-run leaves the motors on and the counter valid; a completed
run is already home; a fresh power-up at home is a no-op.

**Never send `EM` (motor enable/disable) to the board.** EM resets the
step counter, so the board then believes wherever it stands is home,
and the next plot is offset (and can drive the carriage past the edge).
The earlier procedure — `EM,0,0`, then slide the carriage home by
hand — is withdrawn for exactly that reason.

After an abort: `scripts/plotter_home.sh`, then restart the pass. On a
fresh sheet if the double-drawn strokes matter, otherwise on the same
one; `plot_sheet_cards.sh <sheet> <start_card>` resumes from a given
card.

## Running a plot

Sheets (the card pipeline) go through the scripts:

```bash
scripts/plot_sheet_cards.sh s01 [start_card] [end_card]
    # per card: grid pass (fast), then cells + label pass (slow);
    # then the shared cut lines. Homes first. Resume with start_card.
scripts/plot_cuts.sh
    # just the cut lines on the sheet currently taped down
```

Both call `plotter_home.sh` first, which also lifts the pen. The saxi
CLI does NOT lift the pen before the initial travel move, so a manual
run must start with `saxi pen 20 --device ...` or it drags a line from
home to the first stroke.

The settings the scripts use, for a manual run:

```bash
saxi plot --device /dev/cu.usbmodem2101 \
  --no-fit-page --paper-size 279.4x215.9mm --margin 0 \
  --pen-up-height 20 --pen-down-height 68 \
  --pen-up-max-velocity 100 --pen-up-acceleration 200 \
  --pen-lift-duration 0.35 --pen-drop-duration 0.25 \
  --pen-down-max-velocity 25 --pen-down-acceleration 100 \
  <file>.svg
```

- **`--no-fit-page` is mandatory.** The default fit-page mode rescales
  and re-centres the drawing to its content bbox, so passes with
  different bboxes land at different scales/positions (2026-08-23: the
  ink pass plotted offset from the grid pass). With --no-fit-page saxi
  reads coordinates as CSS px (× 25.4/96 mm), so plot files must be in
  px units sized to the paper, with no transforms — which is what
  `scripts/bake_plot_svg.py` produces.
- Pen-down **25 mm/s, 100 mm/s²** for hatch fills. At the default
  50/200, belt backlash + arm flex shorten the hatch turnarounds and
  leave unfilled slivers on one side of cells, worst near the bottom of
  the sheet (max arm extension). Grid and cut passes (no fills) run at
  50/200. A full panel ≈ 11–12 min.

## Aligned overdraw (repair trick)

If the sheet hasn't moved and the last plot finished cleanly, replotting
the same file redraws the identical geometry exactly on top — use it to
re-ink thin fills after a settings change without wasting the sheet. A
run that was killed and then homed with `plotter_home.sh` keeps its
registration too (the step counter survives a kill).

## Generating plottable files

Spaceship card sheets (the production pipeline):

```bash
python -m src.impose --periods 4 5 6 7 --trail 3
    # -> plots/sheets/sheet_NN_{front,back}.svg (layered, mm, portrait)
python3 scripts/bake_plot_svg.py plots/sheets/sheet_01_front.svg \
    --layers grid --rotate --out plots/sheets/plot/s01_pass1_grid.svg
python3 scripts/bake_plot_svg.py plots/sheets/sheet_01_front.svg \
    --layers hatch,label --rotate --out plots/sheets/plot/s01_pass2_inks.svg
```

`bake_plot_svg.py` exists because saxi flattens SVGs through svgdom,
whose nested-transform handling is broken (a parent group's rotation is
dropped from its children). It applies every transform numerically and
emits bare paths in px, sized to the paper. `--card N` bakes a single
card; `plot_sheet_cards.sh` expects those under
`plots/sheets/plot/cards/` as `sNN_cN_{grid,inks}.svg`, plus
`plots/sheets/plot/cuts_baked.svg`.

Single patterns and Conway panels (the original tool, `plotter/`):

```bash
cd plotter
python3 plot_life.py rle/<pattern>.rle output_patterns --artwork --standard
python3 plot_life.py rle/automon_p4.rle output_patterns \
    --table rle/automon_p4.table --artwork --standard     # isotropic rule
```

Panels land in `plotter/output_patterns/<name>/panels/*.svg`, one per
generation, in mm and portrait. Tables come from `src/ruletable.py`
(`web/catalog.json` → `table` field, 128 hex chars, lifelib-verified).
These panels were plotted on 2026-08-06, before the no-fit-page/bake
lessons; `bake_plot_svg.py` only understands imposed sheets, so plotting
panels with today's settings means adapting the bake step first. See
`plotter/README.md`.
