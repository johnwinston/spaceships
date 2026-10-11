from src import claim_sheet, claimcode, shipurl

CATALOG = {
    "xq4_153": {"edition": None, "rle": "bo$2bo$3o!"},
    "p4-01": {"edition": "1", "rle": "bo$2bo$3o!"},
}


def test_claim_url_prefills_the_code():
    url = claim_sheet.claim_url("p4-01", "GQE2-Q3K7", "https://example.com/")
    payload = shipurl.decode_payload(url.split("#", 1)[1])
    assert payload["apgcode"] == "p4-01"
    assert payload["claim"] == "GQE2Q3K7"
    assert claimcode.verify("p4-01", payload["claim"], "test-secret")


def test_booklet_has_one_tile_per_card():
    rows = claim_sheet.tiles(CATALOG, "test-secret", "https://example.com/")
    assert [r[0] for r in rows] == ["p4-01"]
    page = claim_sheet.render(rows, len(rows))
    assert page.count('class="tile"') == 1
    assert "GQE2-Q3K7" in page
