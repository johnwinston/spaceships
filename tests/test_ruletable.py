import pytest

from src import ruletable


def popcount(x):
    return bin(x).count("1")


def test_parse_totalistic_variants():
    assert ruletable.parse_totalistic("b3s23") == ({3}, {2, 3})
    assert ruletable.parse_totalistic("B3/S23") == ({3}, {2, 3})
    assert ruletable.parse_totalistic("b36s23") == ({3, 6}, {2, 3})
    assert ruletable.parse_totalistic("b2ce3aiy/s2ak") is None


def test_totalistic_table_life():
    table = ruletable.totalistic_table("b3s23")
    for idx in range(512):
        center = idx >> 8
        n = popcount(idx & 0xFF)
        expected = (n == 3) if center == 0 else (n in (2, 3))
        assert table[idx] == (1 if expected else 0)


def test_birth_count_matches_combinatorics():
    table = ruletable.totalistic_table("b3s23")
    births = sum(table[idx] for idx in range(256))
    assert births == 56  # C(8,3)


def test_hex_roundtrip():
    table = ruletable.totalistic_table("b36s245")
    hex_str = ruletable.table_to_hex(table)
    assert len(hex_str) == 128
    assert ruletable.table_from_hex(hex_str) == table


def test_hex_length_validation():
    with pytest.raises(ValueError):
        ruletable.table_from_hex("ff")


def test_table_for_rule_needs_lifelib_for_int():
    with pytest.raises(ValueError):
        ruletable.table_for_rule("b2ce3aiy/s2ak", lifelib=None)


def test_neighbourhood_rle_shape():
    # idx with center bit only -> single cell at (1,1)
    text = ruletable._neighbourhood_rle(256).format(rule="b3s23")
    from src import rle
    cells, _ = rle.parse(text)
    assert cells == [(0, 0)]  # normalised single cell
