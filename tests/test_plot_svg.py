from src import plot_svg, rle, ruletable

GLIDER = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!"


def test_front_svg_contains_ship_squares():
    cells, _ = rle.parse(GLIDER)
    svg = plot_svg.card_front_svg(cells)
    assert svg.startswith("<svg")
    assert svg.count("M") >= 5  # five live cells drawn
    assert 'inkscape:label="ship"' in svg
    assert 'fill="none"' in svg


def test_front_svg_with_trails_has_layers():
    cells, _ = rle.parse(GLIDER)
    table = ruletable.totalistic_table("b3s23")
    svg = plot_svg.card_front_svg(cells, table=table, trail_generations=3)
    for g in (1, 2, 3):
        assert 'inkscape:label="trail-gen%d"' % g in svg


def test_back_svg_embeds_qr_path():
    svg = plot_svg.card_back_svg("https://automons.example.com/#v=1&a=xq4_153")
    assert svg.startswith("<svg")
    assert 'inkscape:label="qr"' in svg
    assert "<path d=" in svg


def test_card_dimensions_in_mm():
    cells, _ = rle.parse(GLIDER)
    svg = plot_svg.card_front_svg(cells)
    assert 'width="63.5mm"' in svg
    assert 'height="88.9mm"' in svg
