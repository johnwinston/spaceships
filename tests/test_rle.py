from src import rle

GLIDER = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!"
GLIDER_CELLS = [(0, 2), (1, 0), (1, 2), (2, 1), (2, 2)]


def test_parse_glider():
    cells, rule = rle.parse(GLIDER)
    assert rule == "B3/S23"
    assert cells == sorted(GLIDER_CELLS)


def test_parse_ignores_comments_and_whitespace():
    text = "#C a comment\n  x = 3, y = 3, rule = b2ce3aiy/s2ak\n bo b$2bo$3o !\n"
    cells, rule = rle.parse(text)
    assert rule == "b2ce3aiy/s2ak"
    assert len(cells) == 5


def test_parse_multichar_counts():
    cells, _ = rle.parse("x = 12, y = 1, rule = B3/S23\n12o!")
    assert cells == [(x, 0) for x in range(12)]


def test_roundtrip():
    cells, rule = rle.parse(GLIDER)
    text = rle.serialize(cells, rule)
    cells2, rule2 = rle.parse(text)
    assert cells2 == cells
    assert rule2 == rule


def test_serialize_normalises_origin():
    shifted = [(x + 5, y + 7) for x, y in GLIDER_CELLS]
    text = rle.serialize(shifted, "b3s23")
    cells, _ = rle.parse(text)
    assert cells == sorted(GLIDER_CELLS)


def test_empty_pattern():
    cells, rule = rle.parse(rle.serialize([], "b3s23"))
    assert cells == []
