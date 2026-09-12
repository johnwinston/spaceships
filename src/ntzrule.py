"""ntzfind's rule semantics, in Python.

The search's own table generator (submodules/ntzfind/tab.cpp) is the
authority on what a rule string means -- every ship in the deck exists
because THAT table said so.  This module is a line-for-line port:
RULEKEYS is extracted verbatim from tab.cpp, parse_rule mirrors
parseRule, and NEIGH_PERM is decoded from ntzfind.cpp's slowEvolveBit
(bit j of the neighbourhood index is the ntzfind neighbour order NE, E,
SE, S, SW, W, NW, N -- NEIGH_PERM maps it onto ruletable.NEIGH_ORDER).

Why it exists: the gutter-symmetry search can emit patterns that are
not actually spaceships (the forced-empty centre column is never
re-verified, so a rule that births into the gutter breaks the "ship"
in open evolution).  is_ship() replays a candidate under the search's
own semantics and rejects the fakes -- 29 of 33 gutter ships in the
first full deck build failed it.

No lifelib, no compiled code: pure functions over the 512-entry table.
"""

from .ruletable import NEIGH_ORDER

# ntzfind neighbourhood bit j -> index into NEIGH_ORDER
NEIGH_PERM = (1, 2, 3, 4, 5, 6, 7, 0)

RULEKEYS = (
    '0', '1c', '1e', '2a', '1c', '2c', '2a', '3i',
    '1e', '2k', '2e', '3j', '2a', '3n', '3a', '4a',
    '1c', '2n', '2k', '3q', '2c', '3c', '3n', '4n',
    '2a', '3q', '3j', '4w', '3i', '4n', '4a', '5a',
    '1e', '2k', '2i', '3r', '2k', '3y', '3r', '4t',
    '2e', '3k', '3e', '4j', '3j', '4k', '4r', '5n',
    '2a', '3q', '3r', '4z', '3n', '4y', '4i', '5r',
    '3a', '4q', '4r', '5q', '4a', '5j', '5i', '6a',
    '1c', '2c', '2k', '3n', '2n', '3c', '3q', '4n',
    '2k', '3y', '3k', '4k', '3q', '4y', '4q', '5j',
    '2c', '3c', '3y', '4y', '3c', '4c', '4y', '5e',
    '3n', '4y', '4k', '5k', '4n', '5e', '5j', '6e',
    '2a', '3n', '3r', '4i', '3q', '4y', '4z', '5r',
    '3j', '4k', '4j', '5y', '4w', '5k', '5q', '6k',
    '3i', '4n', '4t', '5r', '4n', '5e', '5r', '6i',
    '4a', '5j', '5n', '6k', '5a', '6e', '6a', '7e',
    '1e', '2a', '2e', '3a', '2k', '3n', '3j', '4a',
    '2i', '3r', '3e', '4r', '3r', '4i', '4r', '5i',
    '2k', '3q', '3k', '4q', '3y', '4y', '4k', '5j',
    '3r', '4z', '4j', '5q', '4t', '5r', '5n', '6a',
    '2e', '3j', '3e', '4r', '3k', '4k', '4j', '5n',
    '3e', '4j', '4e', '5c', '4j', '5y', '5c', '6c',
    '3j', '4w', '4j', '5q', '4k', '5k', '5y', '6k',
    '4r', '5q', '5c', '6n', '5n', '6k', '6c', '7c',
    '2a', '3i', '3j', '4a', '3q', '4n', '4w', '5a',
    '3r', '4t', '4j', '5n', '4z', '5r', '5q', '6a',
    '3n', '4n', '4k', '5j', '4y', '5e', '5k', '6e',
    '4i', '5r', '5y', '6k', '5r', '6i', '6k', '7e',
    '3a', '4a', '4r', '5i', '4q', '5j', '5q', '6a',
    '4r', '5n', '5c', '6c', '5q', '6k', '6n', '7c',
    '4a', '5a', '5n', '6a', '5j', '6e', '6k', '7e',
    '5i', '6a', '6c', '7c', '6a', '7e', '7c', '8',
)


def parse_rule(rule):
    """Rule string -> 512-entry table, exactly as tab.cpp parseRule.

    Index: 256*center + sum(neighbour_bit_j << j) with ntzfind's bit
    order (see NEIGH_PERM).  Raises ValueError on malformed rules.
    """
    tab = [0] * 512
    p = 0
    for bs in (0, 256):
        expected = "bB" if bs == 0 else "sS"
        if p >= len(rule) or rule[p] not in expected:
            raise ValueError("expected %s at position %d" % (expected[0], p))
        p += 1
        while p < len(rule) and rule[p] != "/":
            if not rule[p].isdigit():
                raise ValueError("missing number at position %d" % p)
            dig = rule[p]
            p += 1
            neg = False
            nxt = rule[p] if p < len(rule) else ""
            if nxt in ("", "/", "-") or nxt.isdigit():
                for i in range(256):
                    if RULEKEYS[i][0] == dig:
                        tab[bs + i] = 1
            while p < len(rule) and rule[p] != "/" and not rule[p].isdigit():
                ch = rule[p]
                if ch == "-":
                    if neg:
                        raise ValueError("multiple negation signs")
                    neg = True
                elif "a" <= ch <= "z":
                    used = 0
                    for i in range(256):
                        if RULEKEYS[i][0] == dig and len(RULEKEYS[i]) > 1                                 and RULEKEYS[i][1] == ch:
                            tab[bs + i] = 0 if neg else 1
                            used += 1
                    if not used:
                        raise ValueError("unexpected %r in rule" % ch)
                else:
                    raise ValueError("unexpected %r in rule" % ch)
                p += 1
        if bs == 0:
            if p >= len(rule) or rule[p] != "/":
                raise ValueError("missing slash between b and s")
            p += 1
        elif p != len(rule):
            raise ValueError("unparsed junk at end of rule")
    return tab


def step(cells, table):
    """One generation on the infinite plane under an ntzfind table."""
    candidates = set(cells)
    for x, y in cells:
        for dx, dy in NEIGH_ORDER:
            candidates.add((x + dx, y + dy))
    nxt = set()
    for x, y in candidates:
        idx = 256 if (x, y) in cells else 0
        for j, pos in enumerate(NEIGH_PERM):
            dx, dy = NEIGH_ORDER[pos]
            if (x + dx, y + dy) in cells:
                idx |= 1 << j
        if table[idx]:
            nxt.add((x, y))
    return nxt


def neigh_order_table(rule):
    """The rule's 512-entry table in ruletable.NEIGH_ORDER bit order.

    parse_rule indexes neighbours in ntzfind's own order; ruletable and
    web/js/engine.js index them clockwise from north.  Same transitions,
    reindexed -- so the player runs exactly the semantics the search
    used, without a compiler or a rule cache in the loop.
    """
    native = parse_rule(rule)
    table = [0] * 512
    for idx in range(512):
        src = idx & 256
        for bit, pos in enumerate(NEIGH_PERM):
            if idx & (1 << pos):
                src |= 1 << bit
        table[idx] = native[src]
    return table


def _normalized(cells):
    min_x = min(x for x, _ in cells)
    min_y = min(y for _, y in cells)
    return sorted((x - min_x, y - min_y) for x, y in cells)


def displacement(cells, rule, period, growth_limit=6):
    """How far `cells` travels in `period` generations, or None.

    None means the pattern does not come back to its own shape at all,
    so it is neither ship nor oscillator.  (0, 0) means it does come
    back but stays put -- an oscillator, not a spaceship.
    """
    try:
        table = parse_rule(rule)
    except ValueError:
        return None
    cells = set(cells)
    if not cells:
        return None
    start_pop = len(cells)
    current = set(cells)
    for _ in range(period):
        current = step(current, table)
        if not current or len(current) > growth_limit * start_pop:
            return None
    if len(current) != start_pop:
        return None
    if _normalized(cells) != _normalized(current):
        return None
    return (min(x for x, _ in current) - min(x for x, _ in cells),
            min(y for _, y in current) - min(y for _, y in cells))


def is_ship(cells, rule, period, growth_limit=6):
    """Replay a candidate: a real ship returns to its own shape,
    translated, after exactly `period` generations.

    The translation has to be non-zero -- a pattern that comes back to
    where it started is an oscillator, and a card that never leaves the
    middle of the board is not what the deck is selling.

    growth_limit bounds transient blow-ups (fakes usually explode);
    population above growth_limit times the initial aborts early.
    """
    moved = displacement(cells, rule, period, growth_limit)
    return moved is not None and moved != (0, 0)
