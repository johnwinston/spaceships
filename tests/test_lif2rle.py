import os

import pytest

from src import lif2rle, rle

GLIDER_LIF = """#Life 1.05
#b3/s23
#Period p4
.*.
..*
***
"""


def test_parse_life105_cells_and_rule():
    cells, rule = lif2rle.parse_life105(GLIDER_LIF)
    assert rule == "b3/s23"
    assert sorted(cells) == [(0, 2), (1, 0), (1, 2), (2, 1), (2, 2)]


def test_parse_life105_standard_rule_line():
    text = GLIDER_LIF.replace("#b3/s23", "#R b2ce3aiy/s2ace3i")
    _, rule = lif2rle.parse_life105(text)
    assert rule == "b2ce3aiy/s2ace3i"


def test_parse_life105_rejects_missing_rule():
    with pytest.raises(ValueError, match="rule"):
        lif2rle.parse_life105("#Life 1.05\n.*.\n***\n")


def test_parse_life105_rejects_empty_body():
    with pytest.raises(ValueError, match="live cells"):
        lif2rle.parse_life105("#Life 1.05\n#b3/s23\n...\n...\n")


def test_parse_life105_rejects_stray_characters():
    with pytest.raises(ValueError, match="unexpected character"):
        lif2rle.parse_life105("#Life 1.05\n#b3/s23\n.*o\n")


def test_roundtrip_through_rle_codec():
    cells, rule = lif2rle.parse_life105(GLIDER_LIF)
    text = rle.serialize(cells, rule)
    reparsed_cells, reparsed_rule = rle.parse(text)
    assert reparsed_rule == rule
    assert reparsed_cells == sorted(cells)


def test_convert_period_writes_rle_layout(tmp_path):
    src_dir = tmp_path / "ntzfind_patterns" / "4"
    src_dir.mkdir(parents=True)
    (src_dir / "pattern1.lif").write_text(GLIDER_LIF)
    (src_dir / "pattern2.lif").write_text("#Life 1.05\nbroken")  # skipped
    (src_dir / "notes.txt").write_text("ignored")

    written = lif2rle.convert_period(4, base=str(tmp_path))

    assert written == 1
    out = tmp_path / "rles" / "4" / "pattern1.rle"
    assert out.exists()
    cells, rule = rle.parse(out.read_text())
    assert rule == "b3/s23"
    assert len(cells) == 5


def test_convert_period_missing_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        lif2rle.convert_period(9, base=str(tmp_path))
