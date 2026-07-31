"""Minimal RLE codec for two-state patterns.

Mirrors web/js/rle.js — keep the two implementations in sync.
Coordinates are (x, y) with y increasing downward, matching Golly/lifelib.
"""
import re


def parse(text):
    """Parse RLE text into (cells, rule).

    cells is a sorted list of (x, y) tuples for live cells, translated so
    the bounding box starts at (0, 0).  rule is the rule string from the
    header if present, else None.
    """
    rule = None
    body_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("x"):
            m = re.search(r"rule\s*=\s*([^,\s]+)", line)
            if m:
                rule = m.group(1)
            continue
        body_lines.append(line)
    body = "".join(body_lines)

    cells = []
    x = y = 0
    count = ""
    for ch in body:
        if ch.isdigit():
            count += ch
            continue
        n = int(count) if count else 1
        count = ""
        if ch == "b" or ch == ".":
            x += n
        elif ch == "$":
            y += n
            x = 0
        elif ch == "!":
            break
        elif ch.isalpha():  # 'o' or any multistate letter counts as alive
            for _ in range(n):
                cells.append((x, y))
                x += 1
    if not cells:
        return [], rule
    min_x = min(c[0] for c in cells)
    min_y = min(c[1] for c in cells)
    return sorted((cx - min_x, cy - min_y) for cx, cy in cells), rule


def serialize(cells, rule):
    """Serialize live cells (iterable of (x, y)) into RLE text."""
    cells = sorted(set(cells), key=lambda c: (c[1], c[0]))
    if not cells:
        return "x = 0, y = 0, rule = %s\n!" % rule
    min_x = min(c[0] for c in cells)
    min_y = min(c[1] for c in cells)
    cells = [(x - min_x, y - min_y) for x, y in cells]
    width = max(c[0] for c in cells) + 1
    height = max(c[1] for c in cells) + 1

    runs = []

    def emit(count, tag):
        if count <= 0:
            return
        runs.append((str(count) if count > 1 else "") + tag)

    prev_x, prev_y = -1, 0
    for x, y in cells:
        if y != prev_y:
            emit(y - prev_y, "$")
            prev_x = -1
            prev_y = y
        emit(x - prev_x - 1, "b")
        # coalesce consecutive live cells
        if runs and runs[-1].endswith("o") and x == prev_x + 1:
            tail = runs.pop()
            n = int(tail[:-1]) if len(tail) > 1 else 1
            runs.append(str(n + 1) + "o")
        else:
            emit(1, "o")
        prev_x = x
    runs.append("!")

    body = "".join(runs)
    lines = [body[i:i + 70] for i in range(0, len(body), 70)]
    header = "x = %d, y = %d, rule = %s" % (width, height, rule)
    return header + "\n" + "\n".join(lines)
