import os

import pytest

from src import config
from src.auto_ntzfind import AUTO_NTZFIND


@pytest.fixture
def searcher(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PIPELINE_BASE", str(tmp_path))

    def build(period):
        return AUTO_NTZFIND(1, period)

    return build


def test_combos_cover_the_full_sweep(searcher):
    combos = searcher(7).search_combos()
    assert len(combos) == (
        len(config.SEARCH_WIDTHS)
        * len(config.SEARCH_OFFSETS)
        * len(config.SEARCH_SYMMETRIES)
    )
    assert {s for _, _, s in combos} == set(config.SEARCH_SYMMETRIES)
    assert {w for w, _, _ in combos} == set(config.SEARCH_WIDTHS)


def test_combos_drop_superluminal_offsets(searcher):
    """k >= period is faster than light; ntzfind should never see it."""
    for _, offset, _ in searcher(2).search_combos():
        assert offset < 2


def test_combos_are_shuffled_per_rule(searcher):
    """process() stops at a rule's first ship, so a fixed order would hand
    nearly every card to whichever symmetry sits at the front."""
    search = searcher(7)
    orders = {tuple(search.search_combos()) for _ in range(25)}
    assert len(orders) > 1


def test_symmetry_sweep_reaches_both_width_parities():
    """The point of the sweep: v gives even widths, u and g odd ones."""
    from src import shipfit

    widths = {
        shipfit.full_width(w, s)
        for w in config.SEARCH_WIDTHS
        for s in config.SEARCH_SYMMETRIES
    }
    assert any(w % 2 == 0 for w in widths)
    assert any(w % 2 == 1 for w in widths)


def test_next_index_continues_an_existing_pool(searcher):
    """A second run must append, not overwrite the first batch."""
    search = searcher(4)
    assert search.next_index() == 0
    for n in (1, 2, 7):
        open(search.period_file_path + "pattern%d.lif" % n, "w").close()
    assert search.next_index() == 7


def test_run_appends_past_existing_patterns(searcher, monkeypatch):
    search = searcher(4)
    open(search.period_file_path + "pattern5.lif", "w").close()
    seen = []
    monkeypatch.setattr(
        search, "process",
        lambda rule, iteration: seen.append(iteration) or True,
    )
    search.iterations = 2
    search.run()
    # write_pattern uses iteration+1, so these become pattern6 and pattern7
    assert seen == [5, 6]


def test_run_honours_the_attempt_limit(searcher, monkeypatch):
    """Unattended runs must terminate even when no rule ever yields."""
    search = searcher(7)
    monkeypatch.setattr(search, "process", lambda rule, iteration: False)
    kept, tried = search.run(max_attempts=7)
    assert (kept, tried) == (0, 7)


def test_write_pattern_round_trips_through_lif2rle(searcher, tmp_path):
    """The Life 1.05 dialect lif2rle parses, metadata comments and all."""
    from src import lif2rle, shipfit

    search = searcher(4)
    fit = shipfit.evaluate(["o" * 12] * 18)
    search.write_pattern("b3/s23", 0, 6, 1, "v", 92, fit)

    written = open(search.period_file_path + "pattern1.lif").read()
    cells, rule = lif2rle.parse_life105(written)
    assert rule == "b3/s23"
    assert len(cells) == 12 * 18
    assert "#Search w6 p4 k1 v m92" in written
