"""Common card grid, label band, and misfit rejection (impose.py hatched style)."""
import re

import pytest

from src import config, impose, rle, stroke_font

GLIDER = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!"
BLOCK = "x = 2, y = 2, rule = B3/S23\n2o$2o!"
# A 1x30 column: too tall for any sensible card box.
COLUMN = "x = 1, y = 30, rule = B3/S23\n" + "o$" * 29 + "o!"


def cells_of(text):
    return rle.parse(text)[0]


def coords(d):
    return [
        (float(m.group(1)), float(m.group(2)))
        for m in re.finditer(r"[ML]([\d.eE+-]+) ([\d.eE+-]+)", d)
    ]


def test_every_card_shares_cell_size_and_grid():
    """Two ships of different sizes land on identical graph paper."""
    a = impose._hatched_card_layout(cells_of(GLIDER))
    b = impose._hatched_card_layout(cells_of(BLOCK))
    assert a[1:] == pytest.approx(b[1:])  # grid_w, grid_h, ox, oy, cell_mm
    bw, bh = config.CARD_GRID_BOX
    assert (a[1], a[2]) == (bw + 2 * impose.GRID_PADDING, bh + 2 * impose.GRID_PADDING)


def test_box_override_changes_the_grid():
    _, grid_w, grid_h, _, _, cell_small = impose._hatched_card_layout(cells_of(GLIDER), box=(10, 10))
    assert (grid_w, grid_h) == (12, 12)
    _, _, _, _, _, cell_default = impose._hatched_card_layout(cells_of(GLIDER))
    assert cell_small > cell_default


def test_ship_is_centred_in_box_on_whole_cells():
    cells, _, _, _, _, _ = impose._hatched_card_layout(cells_of(BLOCK))
    bw, bh = config.CARD_GRID_BOX
    assert min(x for x, _ in cells) == (bw - 2) // 2
    assert min(y for _, y in cells) == (bh - 2) // 2
    assert all(isinstance(x, int) and isinstance(y, int) for x, y in cells)


def test_grid_and_label_band_stay_inside_the_margin():
    _, grid_w, grid_h, ox, oy, cell = impose._hatched_card_layout(cells_of(GLIDER))
    m = config.CARD_MARGIN_MM
    assert ox >= m - 1e-6
    assert ox + grid_w * cell <= config.CARD_WIDTH_MM - m + 1e-6
    assert oy >= m - 1e-6
    bottom = oy + grid_h * cell + config.CARD_LABEL_BAND_MM
    assert bottom <= config.CARD_HEIGHT_MM - m + 1e-6


def test_oversize_ship_is_rejected():
    assert not impose.fits_box(cells_of(COLUMN))
    with pytest.raises(impose.ShipTooBig):
        impose._hatched_card_layout(cells_of(COLUMN))
    assert impose.fits_box(cells_of(COLUMN), box=(1, 30))


def test_split_by_fit_keeps_edition_order():
    deck = [
        {"id": "a", "cells": cells_of(GLIDER)},
        {"id": "b", "cells": cells_of(COLUMN)},
        {"id": "c", "cells": cells_of(BLOCK)},
    ]
    fits, misfits = impose.split_by_fit(deck)
    assert [c["id"] for c in fits] == ["a", "c"]
    assert [c["id"] for c in misfits] == ["b"]


def test_parse_box():
    assert impose.parse_box("16x25") == (16, 25)
    assert impose.parse_box("16X25") == (16, 25)
    for bad in ("16", "16x", "0x5", "axb"):
        with pytest.raises(ValueError):
            impose.parse_box(bad)


def test_labels_are_plotted_under_the_grid_flush_with_its_edges():
    card = {"cells": cells_of(GLIDER), "labels": ("Period 4", "1 of 45")}
    svg = impose.front_sheet_svg([card])
    assert svg.count('inkscape:label="label"') == 1

    layers = impose._card_front_layers_hatched(card["cells"], card["labels"])
    pts = coords(re.search(r'd="([^"]*)"', layers["label"]).group(1))
    _, grid_w, grid_h, ox, oy, cell = impose._hatched_card_layout(card["cells"])
    grid_bottom = oy + grid_h * cell
    grid_right = ox + grid_w * cell
    assert min(y for _, y in pts) > grid_bottom            # all text below the grid
    assert max(y for _, y in pts) <= grid_bottom + config.CARD_LABEL_BAND_MM + 1e-6
    # path data is written to 3 decimals, hence the tolerance
    assert min(x for x, _ in pts) == pytest.approx(ox, abs=1e-3)          # left label flush left
    assert max(x for x, _ in pts) == pytest.approx(grid_right, abs=1e-3)  # right label flush right


def test_cards_without_labels_get_no_label_layer():
    svg = impose.front_sheet_svg([{"cells": cells_of(GLIDER)}])
    assert 'inkscape:label="label"' not in svg


def test_card_labels_text():
    assert impose.card_labels("4", 1, 45) == ("Period 4", "1 of 45")
    assert impose.card_labels("7", 6, 6) == ("Period 7", "6 of 6")


def test_stroke_font_alignment_and_width():
    cap = 2.3
    w = stroke_font.text_width("1 of 45", cap)
    assert w > 0
    left = stroke_font.text_path_d("1 of 45", 10, 5, cap)
    right = stroke_font.text_path_d("1 of 45", 10 + w, 5, cap, align="right")
    assert coords(left) == pytest.approx(coords(right), abs=1e-3)
    # "Pod": caps and ascenders only (an "i" dot rides above cap height)
    ys = [y for _, y in coords(stroke_font.text_path_d("Pod", 0, 5, cap))]
    assert max(ys) == pytest.approx(5)            # baseline sits at y=5 ...
    assert min(ys) == pytest.approx(5 - cap)      # ... caps rise cap_mm above it
    with pytest.raises(ValueError):
        stroke_font.text_path_d("x", 0, 0, 1, align="top")


def test_stroke_font_unknown_char_advances_like_a_space():
    # "é" is outside Hershey Simplex's ASCII range
    assert stroke_font.text_width("aéb", 1) == pytest.approx(stroke_font.text_width("a b", 1))


def test_stroke_font_covers_printable_ascii():
    for code in range(33, 127):
        assert stroke_font.text_path_d(chr(code), 0, 0, 1), chr(code)
