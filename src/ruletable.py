"""Canonical 512-entry transition tables for Moore-neighbourhood rules.

This is the interchange format between the Python pipeline and the web
player: instead of re-implementing Hensel isotropic non-totalistic (INT)
notation in JavaScript (easy to get subtly wrong), we compute the full
transition table once, here, and ship it as 128 hex characters.

Table layout
------------
index = center * 256 + sum(neighbour_i << i)

where neighbours are ordered clockwise starting north:

    i:  0  1   2  3   4  5   6  7
        N  NE  E  SE  S  SW  W  NW

table[index] is 1 if the centre cell is alive next generation.
Hex encoding: 512 bits -> 128 hex chars, 4 bits per char, bit j of the
table stored in hex char j//4 at bit position j%4 (little-endian nibbles).

Keep web/js/engine.js in sync with this layout.

Two generators are provided:

* ``totalistic_table`` handles outer-totalistic rules (``b3s23``) with no
  dependencies — used for tests and the golden-glider demo.
* ``int_table_via_lifelib`` handles any rule lifelib can load (including
  every Hensel INT rule ntzfind finds) by brute-forcing all 512 local
  configurations through lifelib, one generation each.  lifelib is the
  oracle, so the table is exactly as correct as the search pipeline.
"""
import importlib
import re

# (dx, dy) for N, NE, E, SE, S, SW, W, NW with y increasing downward.
NEIGH_ORDER = [
    (0, -1), (1, -1), (1, 0), (1, 1),
    (0, 1), (-1, 1), (-1, 0), (-1, -1),
]

TABLE_SIZE = 512


def table_to_hex(table):
    """Pack a 512-entry 0/1 sequence into 128 hex chars."""
    chars = []
    for i in range(0, TABLE_SIZE, 4):
        nibble = (
            (table[i] << 0)
            | (table[i + 1] << 1)
            | (table[i + 2] << 2)
            | (table[i + 3] << 3)
        )
        chars.append("%x" % nibble)
    return "".join(chars)


def table_from_hex(hex_str):
    """Unpack 128 hex chars into a 512-entry list of 0/1."""
    if len(hex_str) != TABLE_SIZE // 4:
        raise ValueError("table hex must be %d chars" % (TABLE_SIZE // 4))
    table = [0] * TABLE_SIZE
    for j, ch in enumerate(hex_str):
        nibble = int(ch, 16)
        for k in range(4):
            table[j * 4 + k] = (nibble >> k) & 1
    return table


def _popcount(x):
    return bin(x).count("1")


def parse_totalistic(rule):
    """Parse an outer-totalistic rule string into (birth, survival) sets.

    Accepts 'b3s23', 'B3/S23', '23/3' style strings.  Returns None if the
    rule contains INT letters (use lifelib for those).
    """
    r = rule.lower().replace("/", "")
    m = re.fullmatch(r"b(\d*)s(\d*)", r)
    if not m:
        return None
    return set(int(d) for d in m.group(1)), set(int(d) for d in m.group(2))


def totalistic_table(rule):
    """Build the 512-entry table for an outer-totalistic rule."""
    parsed = parse_totalistic(rule)
    if parsed is None:
        raise ValueError("not an outer-totalistic rule: %r" % rule)
    birth, survival = parsed
    table = [0] * TABLE_SIZE
    for idx in range(TABLE_SIZE):
        center = idx >> 8
        n = _popcount(idx & 0xFF)
        alive = n in birth if center == 0 else n in survival
        table[idx] = 1 if alive else 0
    return table


def _neighbourhood_rle(idx):
    """RLE for local configuration ``idx`` on a 3x3 grid, centre at (1,1)."""
    live = set()
    if idx >> 8:
        live.add((1, 1))
    for i, (dx, dy) in enumerate(NEIGH_ORDER):
        if (idx >> i) & 1:
            live.add((1 + dx, 1 + dy))
    rows = []
    for y in range(3):
        rows.append("".join("o" if (x, y) in live else "b" for x in range(3)))
    return "x = 3, y = 3, rule = {rule}\n" + "$".join(rows) + "!"


def canonical_rule(rule, lifelib):
    """Return lifelib's canonical form of an isotropic rule string.

    auto_ntzfind emits clauses in random order (``b3ya2kn.../s6c1e...``);
    lifelib's ``str2tab`` refuses such strings but names the canonical
    form in its error message.  Parsing that message keeps lifelib as the
    only Hensel-notation authority (see the module docstring) — pinned by
    a test against the vendored lifelib.  Pure Python, no compiled rules
    needed.
    """
    genera = importlib.import_module(lifelib.__name__ + ".genera")
    isotropic = importlib.import_module(lifelib.__name__ + ".genera.isotropic")
    rule = genera.sanirule(rule)
    try:
        isotropic.str2tab(rule)
        return rule
    except Exception as e:
        m = re.search(r"non-canonical version of (\S+)", str(e))
        if not m:
            raise
        return m.group(1)


def int_table_via_lifelib(rule, lifelib):
    """Build the 512-entry table for any rule lifelib understands.

    For each of the 512 local configurations, place it on an empty
    universe, advance one generation, and read back the centre cell.
    Because all cells outside the 3x3 block start dead, the centre's next
    state is exactly the local transition.
    """
    rule = canonical_rule(rule, lifelib)
    lt = lifelib.load_rules(rule).lifetree(n_layers=1)
    probe = lt.pattern("x = 3, y = 3, rule = %s\n3b$bob$3b!" % rule)
    table = [0] * TABLE_SIZE
    for idx in range(TABLE_SIZE):
        rle_text = _neighbourhood_rle(idx).format(rule=rule)
        pat = lt.pattern(rle_text)
        try:
            adv = pat[1]  # lifelib: pattern[n] = pattern advanced n gens
        except Exception:
            adv = pat.advance(1)
        table[idx] = 1 if (adv & probe).population else 0
    return table


def table_for_rule(rule, lifelib=None):
    """Best-effort table: totalistic directly, otherwise via lifelib."""
    if parse_totalistic(rule) is not None:
        return totalistic_table(rule)
    if lifelib is None:
        raise ValueError(
            "rule %r needs lifelib to build its transition table" % rule
        )
    return int_table_via_lifelib(rule, lifelib)


def verify_oracle(lifelib, rule="b3s23"):
    """Sanity check: the lifelib oracle must agree with the direct
    totalistic construction.  Run this once on any machine with lifelib
    before trusting generated INT tables."""
    direct = totalistic_table(rule)
    oracle = int_table_via_lifelib(rule, lifelib)
    if direct != oracle:
        bad = [i for i in range(TABLE_SIZE) if direct[i] != oracle[i]]
        raise AssertionError(
            "oracle mismatch for %s at %d indices, e.g. %s"
            % (rule, len(bad), bad[:5])
        )
    return True
