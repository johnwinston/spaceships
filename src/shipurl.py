"""Canonical player-URL scheme for QR codes and NFT metadata.

Mirror of web/js/shipurl.js — keep the two implementations in sync.

The URL fragment (after '#') is a query string, so nothing reaches the
server and the player works on static hosting:

    https://<site>/#v=1&a=<apgcode>&r=<rule>              (catalog lookup)
    https://<site>/#v=1&r=<rule>&p=<b64url rle>&t=<hex>   (self-contained)

Parameters
    v   payload version (currently 1)
    a   apgcode — the player looks the ship up in catalog.json
    r   rule string (Hensel INT notation, e.g. b2ce3aiy4as6c/s2ak3nq)
    p   base64url-encoded RLE text (no padding)
    t   optional 128-hex-char transition table (see ruletable.py); when
        absent the player derives the table for totalistic rules or reads
        it from the catalog
    n   optional display name
    c   optional claim token for minting (see chain/README.md)

Short QR payloads matter for pen plotting (fewer modules = cleaner plot),
so prefer the catalog form for production cards and keep the
self-contained form for previews and permanence.
"""
import base64
from urllib.parse import urlencode, parse_qs

from . import config

PAYLOAD_VERSION = "1"


def _b64url_encode(text):
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")


def _b64url_decode(data):
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding).decode("utf-8")


def encode_payload(rule=None, rle_text=None, apgcode=None, name=None,
                   table_hex=None, claim=None, ship_id=None):
    """Build the fragment (no leading '#').

    `a` is the catalog key.  Historically that was an apgcode; the deck
    now keys by its own ship ids (see build_deck.py), so `ship_id` and
    `apgcode` name the same parameter.
    """
    if ship_id and apgcode:
        raise ValueError("pass ship_id or apgcode, not both")
    params = [("v", PAYLOAD_VERSION)]
    if ship_id or apgcode:
        params.append(("a", ship_id or apgcode))
    if rule:
        params.append(("r", rule))
    if rle_text:
        params.append(("p", _b64url_encode(rle_text)))
    if table_hex:
        params.append(("t", table_hex))
    if name:
        params.append(("n", name))
    if claim:
        params.append(("c", claim))
    return urlencode(params)


def decode_payload(fragment):
    """Inverse of encode_payload.  Accepts fragment with or without '#'."""
    fragment = fragment.lstrip("#")
    raw = parse_qs(fragment, keep_blank_values=True)
    out = {}
    mapping = {
        "v": "version", "a": "apgcode", "r": "rule",
        "t": "table_hex", "n": "name", "c": "claim",
    }
    for short, long_name in mapping.items():
        if short in raw:
            out[long_name] = raw[short][0]
    if "p" in raw:
        out["rle_text"] = _b64url_decode(raw["p"][0])
    return out


def player_url(base=None, **kwargs):
    """Full URL for the web player.  kwargs as for encode_payload."""
    base = base or config.SITE_BASE_URL
    return base + "#" + encode_payload(**kwargs)


def catagolue_url(apgcode, rule):
    return config.CATAGOLUE_URL + apgcode + "/" + rule
