from src import ship_sheet, shipurl

CATALOG = {
    "xq4_153": {"edition": None, "rle": "bo$2bo$3o!"},
    "p4-01": {"edition": "1", "rle": "bo$2bo$3o!", "period": "4", "rarity": "common"},
}


def test_ship_url_opens_the_ship_without_a_claim_code():
    url = ship_sheet.ship_url("p4-01", "https://example.com/")
    payload = shipurl.decode_payload(url.split("#", 1)[1])
    assert payload["apgcode"] == "p4-01"
    assert not payload.get("claim")
    assert "c=" not in url


def test_sheet_has_one_tile_per_card_and_no_codes():
    rows = ship_sheet.tiles(CATALOG, "https://example.com/")
    assert [r[0] for r in rows] == ["p4-01"]
    page = ship_sheet.render(rows, len(rows))
    assert page.count('class="tile"') == 1
    assert "Spaceship #1" in page
    assert "period 4 · common" in page
