from src import ship_labels

CATALOG = {"p4-%02d" % i: {"edition": str(i), "rle": "bo$2bo$3o!"} for i in range(1, 33)}


def test_avery_5160_geometry():
    assert ship_labels.label_origin(0) == (0.1875, 0.5)
    assert ship_labels.label_origin(2) == (0.1875 + 2 * 2.75, 0.5)
    x, y = ship_labels.label_origin(29)  # bottom-right
    assert x + ship_labels.LABEL_W == 8.5 - 0.1875
    assert y + ship_labels.LABEL_H == 11 - 0.5


def test_labels_fill_sheets_in_edition_order():
    rows = ship_labels.tiles(CATALOG, "https://example.com/")
    page = ship_labels.render(rows)
    assert page.count('class="sheet"') == 2          # 32 labels -> 30 + 2
    assert page.count('class="label"') == 32
    assert page.index(">p4-01<") < page.index(">p4-30<") < page.index(">p4-31<")
    assert "Spaceship #" not in page
    assert "outline" not in page.split("<body>")[1]   # no borders on the real labels


def test_alignment_page_is_one_sheet_of_outlines():
    page = ship_labels.render([], test=True)
    assert page.count('class="sheet"') == 1
    assert page.count('class="label outline"') == 30
    assert 'class="qr"' not in page


def test_tall_ships_are_turned_lengthwise():
    svg, height = ship_labels._ship_svg_wide("o$o$o!")   # 1 wide, 3 tall
    assert 'viewBox="0 0 3 1"' in svg
    assert height <= ship_labels.ART_H
