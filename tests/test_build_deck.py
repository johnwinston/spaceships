import pytest

from src import shipurl
from src.build_deck import assign_ids


DECK = [
    ("4", "pattern2.rle"), ("4", "pattern11.rle"),
    ("5", "pattern3.rle"),
    ("7", "pattern9.rle"),
]


def test_ids_number_within_period_and_edition_across_deck():
    deck = assign_ids(DECK)
    assert list(deck) == ["p4-01", "p4-02", "p5-01", "p7-01"]
    assert deck["p4-02"] == ("4", "pattern11.rle", 2)
    assert deck["p7-01"][2] == 4  # edition is deck-wide, not per-period


def test_ids_zero_pad_so_lexicographic_order_is_deck_order():
    deck = assign_ids([("4", "pattern%d.rle" % n) for n in range(1, 13)])
    assert sorted(deck) == list(deck)


def test_player_url_accepts_ship_id():
    url = shipurl.player_url(ship_id="p4-01")
    assert url.endswith("#v=1&a=p4-01")
    assert shipurl.decode_payload(url.split("#")[1])["apgcode"] == "p4-01"


def test_ship_id_and_apgcode_are_mutually_exclusive():
    with pytest.raises(ValueError):
        shipurl.encode_payload(ship_id="p4-01", apgcode="xq4_153")


def test_sticker_carries_code_band_only_when_given():
    import qrcode
    from src import build_deck
    qr = qrcode.make("https://john-winston.com/automons/#v=1&a=p4-01")
    plain = build_deck.sticker_image(qr)
    coded = build_deck.sticker_image(qr, "GQE2-Q3K7")
    assert plain.size == (build_deck.QR_PX, build_deck.QR_PX)
    assert coded.size == (build_deck.QR_PX, build_deck.QR_PX + build_deck.CODE_BAND_PX)
    band = coded.crop((0, build_deck.QR_PX, build_deck.QR_PX, coded.size[1]))
    assert band.convert("L").getextrema()[0] < 128  # ink in the band
