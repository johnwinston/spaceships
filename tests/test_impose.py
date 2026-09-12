import re

import pytest

from src import config, impose, plot_svg, rle, ruletable

GLIDER = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!"


def glider_card(url="https://example.com/#a=xq4_153"):
    cells, _ = rle.parse(GLIDER)
    return {
        "cells": cells,
        "table": ruletable.totalistic_table("b3s23"),
        "url": url,
    }


def test_grid_fits_both_papers_with_margin():
    for paper in ("a3", "11x17"):
        ox, oy, pw, ph = impose.sheet_geometry(paper)
        assert ox > 10, paper  # room for clone-grade registration
        assert oy > 10, paper
        assert ox * 2 + 4 * config.CARD_WIDTH_MM == pytest.approx(pw)
        assert oy * 2 + 4 * config.CARD_HEIGHT_MM == pytest.approx(ph)


def test_unknown_paper_is_rejected():
    with pytest.raises(ValueError):
        impose.sheet_geometry("tabloid")


def test_block_exceeding_stock_is_rejected():
    with pytest.raises(ValueError):
        impose.sheet_geometry("letter")  # default 4x4 doesn't fit Letter


def test_letter_3x3_fits_the_axidraw_v3():
    """3x3 on Letter is the block the machine can actually plot: the
    sheet lands landscape, so its 279.4 mm side must fit the 300 mm
    x-travel and its 215.9 mm side the 218 mm y-travel."""
    ox, oy, pw, ph = impose.sheet_geometry("letter", grid=(3, 3))
    assert (pw, ph) == (215.9, 279.4)
    assert ox * 2 + 3 * config.CARD_WIDTH_MM == pytest.approx(pw)
    assert oy * 2 + 3 * config.CARD_HEIGHT_MM == pytest.approx(ph)
    assert ph <= 300 and pw <= 218  # landscape on the V3


def test_mirrored_slots_swap_columns_on_3x3():
    for slot, mirror_slot in ((0, 2), (3, 5), (4, 4), (6, 8)):
        assert impose.slot_origin(slot, "letter", mirrored=True, grid=(3, 3)) ==             impose.slot_origin(mirror_slot, "letter", grid=(3, 3))


def test_slots_butt_edge_to_edge():
    x0, y0 = impose.slot_origin(0, "a3")
    x1, _ = impose.slot_origin(1, "a3")
    _, y4 = impose.slot_origin(4, "a3")
    assert x1 - x0 == pytest.approx(config.CARD_WIDTH_MM)
    assert y4 - y0 == pytest.approx(config.CARD_HEIGHT_MM)


def test_mirrored_slots_swap_columns_not_rows():
    """Backs are plotted after flipping the stock about its long edge:
    column 0 must land where column 3 was, same row."""
    for slot, mirror_slot in ((0, 3), (4, 7), (13, 14)):
        assert impose.slot_origin(slot, "a3", mirrored=True) == \
            impose.slot_origin(mirror_slot, "a3")


def test_front_sheet_merges_layers_across_cards():
    """The point of imposing: 16 cards in ONE layer per pen, so a sheet
    is one pen swap per layer instead of per card."""
    svg = impose.front_sheet_svg([glider_card() for _ in range(16)])
    for name in ("grid", "hatch"):
        assert svg.count('inkscape:label="%s"' % name) == 1
    # grid + hatch, each holding all 16 cards (no card frame: the only
    # edge the pen draws is the optional red cut line)
    assert svg.count("<g transform") == 2 * 16
    assert 'inkscape:label="frame"' not in svg


def test_default_style_is_the_original_plotted_look():
    """Hatched cells + graph-paper grid, no trail outlines -- matching
    the johnwinston/plotter cards the deck grew out of."""
    svg = impose.front_sheet_svg([glider_card()])
    assert 'label="grid"' in svg
    assert 'label="hatch"' in svg
    assert "trail-gen" not in svg
    assert 'label="ship"' not in svg


def test_hatch_covers_every_live_cell():
    """Each of the glider's 5 cells must receive hatch strokes: at least
    one path point inside each cell's rectangle."""
    card = glider_card()
    cells, grid_w, grid_h, ox, oy, cell_mm = impose._hatched_card_layout(
        card["cells"]
    )
    d = re.search(
        r'label="hatch"[^>]*><g[^>]*><path d="([^"]*)"',
        impose.front_sheet_svg([card])
    ).group(1)
    # the path sits inside the slot's translate group, so its coordinates
    # are already card-local; walk M/L/H so points along horizontal
    # sweeps are seen too (a merged run crosses mid-run cells with H)
    points = []
    cur = None
    for m in re.finditer(r"([MLH])([\d.eE+-]+)(?: ([\d.eE+-]+))?", d):
        cmd, a, b = m.group(1), float(m.group(2)), m.group(3)
        cur = (a, cur[1]) if cmd == "H" else (a, float(b))
        points.append(cur)
        if cmd == "H":
            points.append(((points[-2][0] + a) / 2, cur[1]))  # midpoint of sweep
    for cx, cy in cells:
        x0 = ox + (cx + 1) * cell_mm
        y0 = oy + (cy + 1) * cell_mm
        assert any(
            x0 <= px <= x0 + cell_mm and y0 <= py <= y0 + cell_mm
            for px, py in points
        ), "no hatch inside cell (%d,%d)" % (cx, cy)


def _pen_down_length(d):
    """Total pen-down length of axis-aligned path data (M x y then h/v runs)."""
    total = 0.0
    for m in re.finditer(r"[hv]([-\d.eE+]+)", d):
        total += abs(float(m.group(1)))
    return total


def test_grid_lines_are_doubled_as_down_and_back_strokes():
    """Heavy tracing = each line drawn twice, but as ONE full-length
    down-and-back stroke: the pen never lifts or turns mid-line."""
    double = impose._card_front_layers_hatched(glider_card()["cells"])
    single = impose._card_front_layers_hatched(glider_card()["cells"], grid_traces=1)
    d2 = re.search(r'd="([^"]*)"', double["grid"]).group(1)
    d1 = re.search(r'd="([^"]*)"', single["grid"]).group(1)
    assert _pen_down_length(d2) == pytest.approx(2 * _pen_down_length(d1))
    # same stroke count as single-trace: the retrace shares the stroke
    assert d2.count("M") == d1.count("M")


def test_hatch_is_one_stroke_per_cell_with_perimeter():
    """Each live cell is one continuous stroke (fill a cell, then hop to
    the next) ending in a perimeter trace that inks edges and corners."""
    from src import config
    card = glider_card()
    layers = impose._card_front_layers_hatched(card["cells"])
    d = re.search(r'd="([^"]*)"', layers["hatch"]).group(1)
    assert d.count("M") == len(card["cells"])
    cells, _, _, ox, oy, cell = impose._hatched_card_layout(card["cells"])
    e = config.PEN_WIDTH_MM / 2
    x, y = sorted(cells)[0]
    corner = "%g %g" % (ox + (x + impose.GRID_PADDING) * cell + e,
                        oy + (y + impose.GRID_PADDING) * cell + e)
    assert d.count(corner) == 2  # perimeter ring opens and closes on it


def test_trails_style_still_available():
    svg = impose.front_sheet_svg(
        [glider_card() for _ in range(2)], trail=2, style="trails"
    )
    assert svg.count('inkscape:label="ship"') == 1
    assert svg.count('inkscape:label="trail-gen1"') == 1
    assert "hatch" not in svg


def test_unknown_style_is_rejected():
    with pytest.raises(ValueError):
        impose.front_sheet_svg([glider_card()], style="stipple")


def test_trails_sheet_geometry_matches_single_card():
    """A slot-0 card must be the single-card SVG translated, not resized:
    same path data plot_svg emits for that card alone."""
    card = glider_card()
    single = plot_svg.card_front_svg(card["cells"])
    single_path = re.search(
        r'label="ship"[^>]*>(<path d="[^"]*")', single
    ).group(1)
    sheet = impose.front_sheet_svg([card], style="trails")
    assert single_path.split(">")[-1] in sheet


def test_sheet_rejects_seventeen_cards():
    with pytest.raises(ValueError):
        impose.front_sheet_svg([glider_card()] * 17)


def test_cut_lines_cover_grid():
    path = impose.cut_lines_path("a3")
    # outer rect + 3 vertical + 3 horizontal interior lines
    assert path.count("M") == 7


def test_back_sheet_mirrors_position_not_content():
    """Slot 0's QR must appear at slot 3's x on the back; the hatch
    itself stays upright (same relative path data either side)."""
    cards = [glider_card("https://example.com/#a=ship%d" % i)
             for i in range(2)]
    svg = impose.back_sheet_svg(cards)
    x3, _ = impose.slot_origin(3, "a3")
    x2, _ = impose.slot_origin(2, "a3")
    assert ('transform="translate(%g' % x3) in svg
    assert ('transform="translate(%g' % x2) in svg
    assert svg.count('stroke-linecap="butt"') == 1  # one merged qr layer


def test_trailless_card_gets_no_trail_layers():
    svg = impose.front_sheet_svg(
        [{"cells": glider_card()["cells"], "table": None, "url": ""}],
        trail=3, style="trails",
    )
    assert "trail-gen" not in svg
