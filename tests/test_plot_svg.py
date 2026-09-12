import re

import pytest

from src import config, plot_svg, rle, ruletable

GLIDER = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!"
PLAYER_URL = "https://john-winston.com/automons/#v=1&a=xq4_153&r=b3s23"


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


def test_back_svg_is_stroke_only():
    svg = plot_svg.card_back_svg(PLAYER_URL)
    assert 'fill="black"' not in svg  # a pen cannot fill
    assert 'stroke-linecap="butt"' in svg


def test_back_qr_hatching_matches_matrix():
    """Reconstruct module coverage from the emitted strokes: every dark
    module inked, no stroke touching a light module."""
    svg = plot_svg.card_back_svg(PLAYER_URL)
    matrix = plot_svg.qr_matrix(PLAYER_URL)
    n = len(matrix)
    module = config.QR_TARGET_MM / n
    pen = config.PEN_WIDTH_MM
    qx = (config.CARD_WIDTH_MM - config.QR_TARGET_MM) / 2
    qy = (config.CARD_HEIGHT_MM - config.QR_TARGET_MM) / 2

    qr_layer = svg.split('inkscape:label="qr"')[1]
    segs = re.findall(r"M([\d.]+) ([\d.]+)H([\d.]+)", qr_layer)
    assert segs

    covered = set()
    for x1s, ys, x2s in segs:
        x1, y, x2 = float(x1s), float(ys), float(x2s)
        row = int((y - qy) // module)
        col_start = round((x1 - qx - pen / 2) / module)
        col_end = round((x2 - qx + pen / 2) / module)
        assert 0 <= row < n
        assert col_end > col_start
        for col in range(col_start, col_end):
            assert matrix[row][col], "stroke crosses a light module"
            covered.add((row, col))
    dark = {(r, c) for r in range(n) for c in range(n) if matrix[r][c]}
    assert covered == dark


def test_hatch_offsets_cover_band():
    pen = 0.35
    for band in (0.3, 0.5, 0.9, 1.2, 8.0):
        offsets = plot_svg._hatch_offsets(band, pen)
        assert offsets == sorted(offsets)
        if band > pen:
            assert offsets[0] == pytest.approx(pen / 2)
            assert offsets[-1] == pytest.approx(band - pen / 2)
            gaps = [b - a for a, b in zip(offsets, offsets[1:])]
            assert all(g <= pen * 0.8 + 1e-9 for g in gaps)
        else:
            assert offsets == [band / 2]


def test_back_svg_requires_quiet_zone(monkeypatch):
    monkeypatch.setattr(config, "QR_TARGET_MM", 60.0)
    with pytest.raises(ValueError, match="quiet zone"):
        plot_svg.card_back_svg(PLAYER_URL)


def test_card_dimensions_in_mm():
    cells, _ = rle.parse(GLIDER)
    svg = plot_svg.card_front_svg(cells)
    assert 'width="63.5mm"' in svg
    assert 'height="88.9mm"' in svg


def test_back_svg_plots_claim_code_under_qr():
    svg = plot_svg.card_back_svg(PLAYER_URL, code="GQE2-Q3K7")
    assert 'inkscape:label="claim"' in svg
    claim_layer = svg.split('inkscape:label="claim"')[1]
    ys = [float(y) for y in re.findall(r"[ML][\d.]+ ([\d.]+)", claim_layer)]
    assert ys
    _, _, _, qy, quiet = plot_svg.back_geometry(PLAYER_URL)
    assert min(ys) > qy + config.QR_TARGET_MM + quiet     # below the quiet zone
    assert max(ys) < config.CARD_HEIGHT_MM - config.CARD_MARGIN_MM  # inside the margin


def test_back_svg_without_code_has_no_claim_layer():
    assert 'inkscape:label="claim"' not in plot_svg.card_back_svg(PLAYER_URL)


def test_claim_code_must_fit_under_qr(monkeypatch):
    monkeypatch.setattr(config, "CARD_CLAIM_CAP_MM", 30.0)
    with pytest.raises(ValueError, match="does not fit"):
        plot_svg.card_back_svg(PLAYER_URL, code="GQE2-Q3K7")
