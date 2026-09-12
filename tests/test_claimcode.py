import pytest

from src import claimcode, config

SECRET = "test-secret"
# Shared with worker/test/claimcode.test.js -- the two implementations
# must agree on these exactly.
VECTORS = {"p4-01": "GQE2-Q3K7", "xq4_153": "C6CZ-BH9W"}


def test_known_vectors_pin_both_implementations():
    for ship_id, code in VECTORS.items():
        assert claimcode.claim_code(ship_id, SECRET) == code


def test_code_shape_uses_plotter_safe_alphabet():
    for n in range(1, 60):
        code = claimcode.claim_code("p4-%02d" % n, SECRET)
        assert len(code) == 9 and code[4] == "-"
        bare = code.replace("-", "")
        assert all(ch in claimcode.ALPHABET for ch in bare)
        assert not set("ILOU") & set(bare)


def test_codes_differ_per_ship_and_per_secret():
    a = claimcode.claim_code("p4-01", SECRET)
    assert a != claimcode.claim_code("p4-02", SECRET)
    assert a != claimcode.claim_code("p4-01", "another-secret")


def test_verify_forgives_case_spacing_and_lookalikes():
    assert claimcode.verify("p4-01", "gqe2 q3k7", SECRET)
    assert claimcode.verify("p4-01", "GQE2Q3K7", SECRET)
    assert claimcode.verify("p4-01", " gqe2-q3k7 ", SECRET)
    # a hand-read 'O' for zero / 'I' for one must still verify
    code = claimcode.claim_code("xq4_153", SECRET)  # C6CZ-BH9W has no 0/1
    assert claimcode.verify("xq4_153", code.lower(), SECRET)


def test_verify_rejects_wrong_or_malformed_codes():
    assert not claimcode.verify("p4-01", "GQE2-Q3K8", SECRET)
    assert not claimcode.verify("p4-02", "GQE2-Q3K7", SECRET)
    assert not claimcode.verify("p4-01", "", SECRET)
    assert not claimcode.verify("p4-01", "GQE2-Q3K7-XX", SECRET)
    assert not claimcode.verify("p4-01", None, SECRET)
    assert not claimcode.verify("p4-01", "UUUU-UUUU", SECRET)  # U is not in the alphabet


def test_normalise_maps_lookalikes_onto_digits():
    assert claimcode.normalise("oi1l-abcd") == "0111ABCD"
    assert claimcode.normalise("short") is None


def test_deck_codes_in_edition_order():
    deck = {"p5-01": {"edition": 3}, "p4-01": {"edition": 1}, "p4-02": {"edition": 2}}
    rows = claimcode.deck_codes(deck, SECRET)
    assert [r[0] for r in rows] == ["p4-01", "p4-02", "p5-01"]
    assert rows[0][2] == VECTORS["p4-01"]


def test_secret_comes_from_environment_only(monkeypatch):
    monkeypatch.delenv(config.CLAIM_SECRET_ENV, raising=False)
    assert claimcode.claim_secret(required=False) is None
    with pytest.raises(SystemExit):
        claimcode.claim_secret()
    monkeypatch.setenv(config.CLAIM_SECRET_ENV, "  s3cret  ")
    assert claimcode.claim_secret() == "s3cret"


def test_new_secret_is_long_and_random():
    a, b = claimcode.new_secret(), claimcode.new_secret()
    assert len(a) == 64 and a != b
