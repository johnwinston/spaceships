from src import shipurl, ruletable

RLE = "x = 3, y = 3, rule = B3/S23\nbob$2bo$3o!"


def test_roundtrip_self_contained():
    table_hex = ruletable.table_to_hex(ruletable.totalistic_table("b3s23"))
    fragment = shipurl.encode_payload(
        rule="b3s23", rle_text=RLE, apgcode="xq4_153",
        name="golden glider", table_hex=table_hex, claim="abc123",
    )
    decoded = shipurl.decode_payload(fragment)
    assert decoded["rule"] == "b3s23"
    assert decoded["rle_text"] == RLE
    assert decoded["apgcode"] == "xq4_153"
    assert decoded["name"] == "golden glider"
    assert decoded["table_hex"] == table_hex
    assert decoded["claim"] == "abc123"
    assert decoded["version"] == shipurl.PAYLOAD_VERSION


def test_roundtrip_catalog_form():
    fragment = shipurl.encode_payload(rule="b2ce3aiy/s2ak", apgcode="xq4_abc")
    decoded = shipurl.decode_payload(fragment)
    assert decoded == {
        "version": "1", "apgcode": "xq4_abc", "rule": "b2ce3aiy/s2ak",
    }


def test_decode_tolerates_leading_hash():
    fragment = "#" + shipurl.encode_payload(rule="b3s23")
    assert shipurl.decode_payload(fragment)["rule"] == "b3s23"


def test_player_url_uses_config_base():
    url = shipurl.player_url(base="https://ships.test/play/", apgcode="x")
    assert url.startswith("https://ships.test/play/#v=1&a=x")


def test_b64url_is_urlsafe():
    fragment = shipurl.encode_payload(rle_text="ab?&=+/~\n$!")
    assert "+" not in fragment.split("p=")[1]
    decoded = shipurl.decode_payload(fragment)
    assert decoded["rle_text"] == "ab?&=+/~\n$!"
