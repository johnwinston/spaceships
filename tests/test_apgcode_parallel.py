import json

from src.apgcode_parallel import chunk, merge_parts


def test_chunk_covers_everything_in_order():
    items = ["a", "b", "c", "d", "e"]
    chunks = chunk(items, 2)
    assert [x for c in chunks for x in c] == items
    assert len(chunks) == 2


def test_chunk_never_exceeds_item_count():
    assert chunk(["a", "b"], 8) == [["a"], ["b"]]


def test_chunk_balances_sizes():
    sizes = [len(c) for c in chunk(list(range(10)), 3)]
    assert max(sizes) - min(sizes) <= 1


def test_merge_parts_combines_files(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text(json.dumps({"p1.rle": {"apgcode": "x"}}))
    b.write_text(json.dumps({"p2.rle": {"apgcode": "y"}}))
    merged = merge_parts([str(a), str(b)])
    assert set(merged) == {"p1.rle", "p2.rle"}
