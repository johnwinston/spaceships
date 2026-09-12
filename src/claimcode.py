"""Claim codes: the short code printed on the back of each card.

A buyer proves they hold a physical card by typing its code into the
player page (or scanning a QR that carries it).  The code is derived,
not stored: HMAC-SHA256 of the ship id under a secret kept out of the
repo, truncated to 40 bits and written in Crockford base32 --
``XXXX-XXXX`` -- an alphabet with no I, L, O or U, so a hand-plotted
code survives being read back off card stock.

Mirror of worker/src/claimcode.js -- keep the two in sync (the shared
test vector in tests/test_claimcode.py and worker/test/claimcode.test.js
pins them together).

    AUTOMONS_CLAIM_SECRET=... python -m src.claimcode --deck data/deck.json
    AUTOMONS_CLAIM_SECRET=... python -m src.claimcode p4-01
"""
import argparse
import hashlib
import hmac
import json
import os
import sys

from . import config

ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_CHARS = 8
GROUP = 4
_DIGEST_BYTES = CODE_CHARS * 5 // 8  # 40 bits
# Crockford decoding folds look-alikes onto the digit they resemble.
_LOOKALIKES = str.maketrans({"I": "1", "L": "1", "O": "0"})


def claim_secret(required=True):
    """The shared secret from the environment (never from the repo)."""
    secret = os.environ.get(config.CLAIM_SECRET_ENV, "").strip()
    if secret:
        return secret
    if required:
        raise SystemExit(
            "%s is not set -- claim codes need the shared secret. "
            "Generate one with: python -m src.claimcode --new-secret"
            % config.CLAIM_SECRET_ENV
        )
    return None


def new_secret():
    """A fresh 256-bit secret, hex encoded."""
    return os.urandom(32).hex()


def claim_code(ship_id, secret):
    """``XXXX-XXXX`` for ``ship_id`` under ``secret``."""
    if not ship_id:
        raise ValueError("ship id is empty")
    digest = hmac.new(
        secret.encode("utf-8"), ship_id.encode("utf-8"), hashlib.sha256
    ).digest()
    value = int.from_bytes(digest[:_DIGEST_BYTES], "big")
    chars = [
        ALPHABET[(value >> (5 * (CODE_CHARS - 1 - i))) & 31]
        for i in range(CODE_CHARS)
    ]
    return "-".join(
        "".join(chars[i:i + GROUP]) for i in range(0, CODE_CHARS, GROUP)
    )


def normalise(text):
    """What a person typed -> the bare 8 characters, or None if it cannot
    be a code.  Case, spacing, hyphens and look-alike letters are all
    forgiven."""
    if not isinstance(text, str):
        return None
    bare = "".join(ch for ch in text.upper() if ch.isalnum())
    bare = bare.translate(_LOOKALIKES)
    if len(bare) != CODE_CHARS or any(ch not in ALPHABET for ch in bare):
        return None
    return bare


def verify(ship_id, typed, secret):
    """True when ``typed`` is the code for ``ship_id``."""
    bare = normalise(typed)
    if bare is None:
        return False
    expected = claim_code(ship_id, secret).replace("-", "")
    return hmac.compare_digest(bare, expected)


def deck_codes(deck, secret):
    """[(ship_id, edition, code)] in deck order -- the booth's private
    sheet."""
    rows = []
    for ship_id, entry in deck.items():
        rows.append((ship_id, int(entry.get("edition", 0)), claim_code(ship_id, secret)))
    rows.sort(key=lambda r: r[1])
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ship", nargs="?", help="one ship id, e.g. p4-01")
    parser.add_argument("--deck", help="data/deck.json -> print every code")
    parser.add_argument("--new-secret", action="store_true",
                        help="print a fresh secret and exit")
    args = parser.parse_args(argv)
    if args.new_secret:
        print(new_secret())
        return
    if not args.ship and not args.deck:
        parser.print_help()
        return
    secret = claim_secret()
    if args.ship:
        print(claim_code(args.ship, secret))
    if args.deck:
        with open(args.deck) as f:
            deck = json.load(f)
        print("id\tedition\tcode")
        for ship_id, edition, code in deck_codes(deck, secret):
            print("%s\t%d\t%s" % (ship_id, edition, code))


if __name__ == "__main__":
    main(sys.argv[1:])
