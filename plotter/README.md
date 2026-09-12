# plotter — Game of Life patterns for the pen plotter

The original tool behind the G4G plotted cards, folded in from the
`johnwinston/plotter` repo on 2026-09-12. It takes an RLE pattern,
evolves it until it repeats or dies, and writes plotter-ready SVGs
(crosshatch fills, grid lines traced twice) as single panels, 3×3 / 2×2
sheets with cut lines, or one "artwork" strip showing the pattern's
travel across generations.

Run it from this directory with the repo's arm64 venv:

```bash
cd plotter
../.venv/bin/python plot_life.py rle/doodah.rle output_patterns
../.venv/bin/python plot_life.py rle/doodah.rle output_patterns --large        # 2×2, 25% larger
../.venv/bin/python plot_life.py rle/doodah.rle output_patterns --iterations 50
../.venv/bin/python plot_life.py rle/robin.rle output_patterns --artwork --preview
../.venv/bin/python plot_life.py rle/automon_p4.rle output_patterns \
    --table rle/automon_p4.table --artwork --standard   # isotropic (non-B3/S23) rule
```

Output goes to `output_patterns/<name>/` (gitignored): `rle/` and `svg/`
per generation, `panels/` for artwork mode, and the grid sheets named by
generation range (`<name>_grid_3x3_0-8.svg`). `--help` lists every flag.

Fixed settings: hatch spacing 1 px at 45°, 5 mm cut margin, 4 mm grid
spacing, Letter paper, 96 DPI (1 in = 96 px = 25.4 mm; SVG dimensions
are always in mm).

## `--table`: rules other than Conway's

`--table HEX|FILE` takes a 512-entry transition table as 128 hex chars
(or a file holding them) and the evolver uses it instead of B3/S23.
Tables come from `src/ruletable.py` at the repo root (lifelib is the
oracle; `web/catalog.json` carries one per ship). The bit layout is
documented in `lifeplot/game_of_life.py` and must match `ruletable.py`.
`rle/automon_p4.{rle,table}` is the first plotted spaceship
(`xq4_1vl0o88o0lv1z0aa7y07aazy07w7`) and a regression test.

## Layout

```
plot_life.py            CLI + pipeline orchestration (PatternProcessor)
lifeplot/
  rle_parser.py         RLE <-> cell set
  game_of_life.py       evolution, period detection, optional rule table
  hatching.py           eggbot-style crosshatch with Bezier-joined segments
                        (src/hatching.py at the repo root is a unit-agnostic
                        fork of this for the card pipeline)
  svg_generator.py      plotter SVG in mm; crosshatch / solid / circles
  grid_layout.py        3×3 / 2×2 sheets on Letter with cut lines
  circle_layout.py, hershey_fonts.py, text_to_path.py   unused extras
tests/                  run with `pytest` from the repo root, or
                        `pytest plotter/tests`
rle/                    the pattern collection (Conway spaceships from
                        the G4G run, plus automon_p4)
```

Pipeline: parse RLE → evolve (max 10,000 generations; period 0 = died,
1 = still life, N = oscillator/spaceship) → SVG per generation → layout.
Pattern-type labels are heuristics on the period (period > 8 is called
a spaceship).

Plotting the output on the AxiDraw: [../docs/OPERATING.md](../docs/OPERATING.md).
