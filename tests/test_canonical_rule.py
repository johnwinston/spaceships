import pytest

from src import ruletable

# canonical_rule only touches lifelib's pure-Python genera package —
# no compiled rules needed, but the submodule must be checked out.
lifelib = pytest.importorskip("submodules.lifelib")


def test_already_canonical_passes_through():
    assert ruletable.canonical_rule("b3s23", lifelib) == "b3s23"
    assert (
        ruletable.canonical_rule("b2kn3-q4cinqz5knrs1e3eikny4-ajtz6c7e", lifelib)
        == "b2kn3-q4cinqz5knrs1e3eikny4-ajtz6c7e"
    )


def test_searched_rule_is_canonicalised():
    # exactly what auto_ntzfind emits: clauses and letters in random order
    raw = "b2kn3ykaciejnr4nzqci5krn/s6c7e1e4kewyiqcnr3nekiy"
    assert (
        ruletable.canonical_rule(raw, lifelib)
        == "b2kn3-q4cinqz5knrs1e3eikny4-ajtz6c7e"
    )


def test_slash_and_case_variants():
    assert ruletable.canonical_rule("B3/S23", lifelib) == "b3s23"
