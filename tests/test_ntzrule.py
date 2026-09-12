import pytest

from src import ntzrule

# Life's LWSS, as ntzfind prints it (b3/s23 w5 p4 k2 a).
LWSS_ROWS = ["..o..", ".ooo.", ".o.oo", "..ooo", "..oo."]
LWSS = {(x, y) for y, r in enumerate(LWSS_ROWS)
        for x, c in enumerate(r) if c == "o"}

BLOCK = {(0, 0), (1, 0), (0, 1), (1, 1)}


def test_rulekeys_is_the_full_neighbourhood_map():
    assert len(ntzrule.RULEKEYS) == 256
    assert ntzrule.RULEKEYS[0] == "0"
    assert ntzrule.RULEKEYS[1] == "1c"


def test_parse_rule_reproduces_life():
    """b3/s23: born on exactly 3, survives on 2 or 3 -- 140 live entries
    across the 512-entry table."""
    table = ntzrule.parse_rule("b3/s23")
    assert len(table) == 512
    assert sum(table) == 140


def test_parse_rule_handles_negated_clauses():
    """'b2-a' is every 2-neighbour configuration except 2a."""
    full = ntzrule.parse_rule("b2/s")
    minus = ntzrule.parse_rule("b2-a/s")
    assert sum(minus) < sum(full)
    for i, key in enumerate(ntzrule.RULEKEYS):
        if key == "2a":
            assert full[i] == 1 and minus[i] == 0


def test_parse_rule_rejects_malformed():
    for bad in ("x3/s23", "b3s23", "b3/s23/", "b3/s2--3"):
        with pytest.raises(ValueError):
            ntzrule.parse_rule(bad)


def test_lwss_is_a_period_4_ship():
    assert ntzrule.is_ship(LWSS, "b3/s23", 4)


def test_lwss_fails_at_the_wrong_period():
    assert not ntzrule.is_ship(LWSS, "b3/s23", 3)


def test_still_life_is_not_a_ship():
    """A block returns to its own shape at every period, but never
    moves.  Accepting it would have let a card sit frozen in the
    player, which is how the wrong-table build stayed invisible."""
    assert not ntzrule.is_ship(BLOCK, "b3/s23", 1)
    assert not ntzrule.is_ship(BLOCK, "b3/s23", 4)


def test_oscillator_is_not_a_ship():
    """A blinker is period 2 and stays put."""
    blinker = {(1, 0), (1, 1), (1, 2)}
    assert ntzrule.displacement(blinker, "b3/s23", 2) == (0, 0)
    assert not ntzrule.is_ship(blinker, "b3/s23", 2)


def test_displacement_measures_lwss_travel():
    # ntzfind prints ships travelling up the page: 2 cells per period.
    assert ntzrule.displacement(LWSS, "b3/s23", 4) == (0, -2)
    assert ntzrule.displacement(LWSS, "b3/s23", 3) is None


def test_neigh_order_table_agrees_with_step():
    """neigh_order_table must be the same rule as parse_rule, only
    reindexed -- so engine.step (NEIGH_ORDER) and ntzrule.step
    (ntzfind order) evolve a pattern identically."""
    from src import engine

    table = ntzrule.neigh_order_table("b3/s23")
    assert len(table) == 512
    native = ntzrule.parse_rule("b3/s23")
    assert sum(table) == sum(native)

    cells = set(LWSS)
    mine = set(LWSS)
    for _ in range(4):
        cells = engine.step(cells, table)
        mine = ntzrule.step(mine, native)
    assert cells == mine


def test_dying_pattern_is_not_a_ship():
    assert not ntzrule.is_ship({(0, 0)}, "b3/s23", 4)


def test_empty_input_is_not_a_ship():
    assert not ntzrule.is_ship(set(), "b3/s23", 4)


def test_step_matches_life_on_a_blinker():
    table = ntzrule.parse_rule("b3/s23")
    blinker = {(1, 0), (1, 1), (1, 2)}
    once = ntzrule.step(blinker, table)
    assert once == {(0, 1), (1, 1), (2, 1)}
    assert ntzrule.step(once, table) == blinker
