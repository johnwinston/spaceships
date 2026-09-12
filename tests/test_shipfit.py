import pytest

from src import config, plot_svg, rle, shipfit

GLIDER = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!"

# A real ntzfind run: it printed a pattern and a Length immediately before
# concluding it had found nothing.  Only the block trailed by "Spaceship
# found." is a ship.
NTZFIND_DUMP = """\
Starting search
..o..
.ooo.
Length: 6
Search complete: 0 spaceships found.
"""

NTZFIND_FIND = """\
Starting search

..o..
.ooo.
Length: 6
Spaceship found. (1)

Search terminated: spaceship found.
"""


def test_full_width_matches_symmetry_flags():
    # ntzfind's own usage text: "w6 v" is a full width of 12.
    assert shipfit.full_width(6, "v") == 12
    # and the w3/u run above printed rows five cells wide.
    assert shipfit.full_width(3, "u") == 5
    assert shipfit.full_width(6, "a") == 6
    assert shipfit.full_width(6, "g") == 13


def test_full_width_rejects_unknown_symmetry():
    with pytest.raises(ValueError):
        shipfit.full_width(6, "z")


def test_printable_box_tracks_card_config():
    box_w, box_h = shipfit.printable_box_mm()
    assert box_w == config.CARD_WIDTH_MM - 2 * config.CARD_MARGIN_MM
    assert box_h == config.CARD_HEIGHT_MM - 2 * config.CARD_MARGIN_MM


def test_cell_size_agrees_with_plot_svg():
    """shipfit predicts the cell size plot_svg will actually choose; if
    these drift, every fit score is measured against the wrong box."""
    cells, _ = rle.parse(GLIDER)
    _, _, _, cell_mm = plot_svg.ship_layout(cells, 0, [0] * 512)
    assert cell_mm == pytest.approx(shipfit.cell_size_mm(3, 3))


def test_cell_size_is_capped():
    # A 2x3 ship would scale to 25mm cells without the cap.
    assert shipfit.cell_size_mm(2, 3) == shipfit.MAX_CELL_MM


def test_height_band_brackets_the_ideal():
    ideal = 12 / shipfit.card_aspect()
    low, high = shipfit.height_band(12)
    assert low <= ideal <= high


def test_max_length_arg_lands_on_the_band_top():
    """m caps ntzfind's reported Length, and buffPattern emits one row per
    `period` search rows, so height = (Length-1)//period + 1 must come out
    exactly at the top of the accepted band -- no slack, no truncation."""
    for period in (4, 5, 6, 7):
        for width in (6, 7, 8):
            ship_width = shipfit.full_width(width, "v")
            _, high = shipfit.height_band(ship_width)
            arg = shipfit.max_length_arg(ship_width, period)
            assert (arg - 1) // period + 1 == high


def test_bounding_box_trims_margins_but_keeps_interior_gaps():
    rows = ["....", ".oo.", "....", ".o..", "...."]
    trimmed, width, height = shipfit.bounding_box(rows)
    assert trimmed == ["oo", "..", "o."]
    assert (width, height) == (2, 3)


def test_bounding_box_of_empty_pattern():
    assert shipfit.bounding_box(["....", "...."]) == ([], 0, 0)


def test_iter_ships_ignores_progress_dumps():
    assert list(shipfit.iter_ships(NTZFIND_DUMP)) == []


def test_iter_ships_reads_a_confirmed_find():
    found = list(shipfit.iter_ships(NTZFIND_FIND))
    assert len(found) == 1
    rows, length = found[0]
    assert rows == ["..o..", ".ooo."]
    assert length == 6


def test_evaluate_rejects_the_sliver():
    """12 wide wants ~18 tall on this card; 40 tall is the failure mode
    an unbounded search produces."""
    fit = shipfit.evaluate(["o" * 12] * 40)
    assert (fit.width, fit.height) == (12, 40)
    assert not fit.accepted
    assert fit.fill < 0.5


def test_evaluate_accepts_a_card_shaped_ship():
    height = round(12 / shipfit.card_aspect())
    fit = shipfit.evaluate(["o" * 12] * height)
    assert fit.accepted
    assert fit.fill > 0.95


def test_evaluate_rejects_a_sparse_ship_that_fits_the_box():
    """The failure mode a manual curation pass exposed: a wispy ship can
    sit dead on the card's aspect and still plot as scattered marks."""
    height = round(12 / shipfit.card_aspect())
    sparse = ["o" + "." * 11] * height  # correct shape, one cell per row
    fit = shipfit.evaluate(sparse)
    assert fit.width == 1
    assert not fit.accepted


def test_evaluate_counts_population():
    fit = shipfit.evaluate(["o.o", ".o.", "o.o"], min_pop=0)
    assert fit.pop == 5


def test_min_pop_is_independent_of_aspect():
    """A card-shaped ship still fails on population alone, and passes once
    the threshold is lowered -- so the two checks can't mask each other."""
    height = round(12 / shipfit.card_aspect())
    rows = ["o.o.o.o.o.o." for _ in range(height)]
    assert not shipfit.evaluate(rows, min_pop=999).accepted
    assert shipfit.evaluate(rows, min_pop=0).accepted


def test_evaluate_grades_the_real_bounding_box_not_the_search_width():
    """Ships come back narrower than the search width; padding must not
    count toward the fit."""
    height = round(12 / shipfit.card_aspect())
    padded = ["..%s.." % ("o" * 12)] * height
    assert shipfit.evaluate(padded).width == 12
