"""Random-rule spaceship search, bounded to ships that fit the card.

Generates isotropic non-totalistic rules at random and hands each one to
ntzfind.  Rather than a single hardcoded search, every rule is swept
across the configured widths and speeds, and each invocation carries an
`m` argument derived from the card's printable box (see shipfit), so
over-long ships are pruned during the walk instead of being found and
then thrown away.  Whatever survives is graded on its real bounding box
before it is written.

Output stays in the Life 1.05 dialect lif2rle expects: a `#Life 1.05`
banner, the rule, the period, then `.`/`*` rows.  The extra `#` metadata
lines are ignored by that parser.
"""
import os
import re
import subprocess
import time
from random import randrange, sample

_PATTERN_RE = re.compile(r"^pattern(\d+)\.lif$")

from . import config
from . import ntzrule
from . import shipfit


class AUTO_NTZFIND:
    def __init__(self, iterations, period):
        self.golly_file_path = os.path.join(config.PIPELINE_BASE, "ntzfind_patterns/")
        self.period_file_path = self.golly_file_path + str(period) + "/"
        if not os.path.exists(self.period_file_path):
            os.makedirs(self.period_file_path)
        self.iterations = iterations
        self.period_n = int(period)
        self.period = "p" + str(period)
        self.numbers = list(range(1, 8))
        self.letters =\
          [
            ['c', 'e'],
            ['c', 'e', 'k', 'a', 'i', 'n'],
            ['c', 'e', 'k', 'a', 'i', 'n', 'y', 'q', 'j', 'r'],
            ['c', 'e', 'k', 'a', 'i', 'n', 'y', 'q', 'j', 'r', 't', 'w', 'z'],
            ['c', 'e', 'k', 'a', 'i', 'n', 'y', 'q', 'j', 'r'],
            ['c', 'e', 'k', 'a', 'i', 'n'],
            ['c', 'e']
          ]

    def generate_sub_rule(self):
        rule = ""
        for num in sample(self.numbers, randrange(1, 8)):
            rule += str(num)
            number_of_letters = randrange(1, len(self.letters[num-1]))
            for letter in sample(self.letters[num-1], number_of_letters):
                rule += letter
        return rule

    def generate_rule(self):
        rule = "b" + self.generate_sub_rule() +\
               "/s" + self.generate_sub_rule()
        return rule

    def search_combos(self):
        """(search_width, offset, symmetry) triples worth trying.

        k >= period would be superluminal, so those are dropped.  The
        order is shuffled per rule: `process` stops at the first ship a
        rule yields, so a fixed order would hand almost every card to
        whichever symmetry sits at the front of the list and undo the
        point of sweeping them.
        """
        combos = [
            (width, offset, symmetry)
            for width in config.SEARCH_WIDTHS
            for offset in config.SEARCH_OFFSETS
            for symmetry in config.SEARCH_SYMMETRIES
            if offset < self.period_n
        ]
        return sample(combos, len(combos))

    def invoke(self, rule, width, offset, symmetry, max_length):
        """Run one ntzfind search.  Returns stdout, or None if it gave up."""
        argv = [
            config.NTZFIND_BIN,
            rule,
            "w%d" % width,
            self.period,
            "k%d" % offset,
            symmetry,
            "l%d" % config.SEARCH_DEPTH_LIMIT,
            "m%d" % max_length,
        ]
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=config.SEARCH_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return None
        except OSError as exc:
            raise RuntimeError(
                "could not run ntzfind at %s: %s" % (config.NTZFIND_BIN, exc)
            ) from exc
        return completed.stdout

    def write_pattern(self, rule, iteration, width, offset, symmetry,
                      max_length, fit):
        """Write one accepted ship as Life 1.05 for lif2rle to pick up."""
        path = self.period_file_path + "pattern" + str(iteration + 1) + ".lif"
        lines = [
            "#Life 1.05",
            "#" + rule,
            "#Period " + self.period,
            "#Search w%d %s k%d %s m%d" % (
                width, self.period, offset, symmetry, max_length
            ),
            "#Fit %dx%d cells, %.2fmm cell, %d%% of box" % (
                fit.width, fit.height, fit.cell_mm, round(100 * fit.fill)
            ),
        ]
        lines += [row.replace("o", "*") for row in fit.rows]
        with open(path, "w") as handle:
            handle.write("\n".join(lines) + "\n")

    def process(self, rule, iteration):
        """Sweep one rule across the search grid; keep the first ship that fits."""
        for width, offset, symmetry in self.search_combos():
            ship_width = shipfit.full_width(width, symmetry)
            max_length = shipfit.max_length_arg(ship_width, self.period_n)
            stdout = self.invoke(rule, width, offset, symmetry, max_length)
            if not stdout:
                continue
            for rows, _length in shipfit.iter_ships(stdout):
                fit = shipfit.evaluate(rows)
                if not fit.accepted:
                    continue
                # ntzfind's gutter search never re-checks the forced-empty
                # centre column, so it can report patterns that aren't
                # spaceships once evolved on an open plane.  Replay every
                # candidate under the search's own rule semantics.
                cells = {
                    (x, y)
                    for y, row in enumerate(fit.rows)
                    for x, ch in enumerate(row) if ch == "o"
                }
                if not ntzrule.is_ship(cells, rule, self.period_n):
                    continue
                self.write_pattern(
                    rule, iteration, width, offset, symmetry, max_length, fit
                )
                for row in fit.rows:
                    print(row)
                print("%s  w%d k%d %s  %dx%d cells  %.2fmm cell  %d%% of box\n" % (
                    rule, width, offset, symmetry, fit.width, fit.height,
                    fit.cell_mm, round(100 * fit.fill),
                ))
                return True
        return False

    def next_index(self):
        """Highest patternN.lif already on disk.

        Numbering continues from here so a later run appends to the pool
        instead of overwriting the previous batch -- collecting a large
        pool for curation takes several sessions.
        """
        highest = 0
        for name in os.listdir(self.period_file_path):
            found = _PATTERN_RE.match(name)
            if found:
                highest = max(highest, int(found.group(1)))
        return highest

    def run(self, time_budget_s=None, max_attempts=None, resume=True):
        """Search until `iterations` ships are kept, or a bound is hit.

        Random rules mostly yield nothing, and a period with a large search
        space can run indefinitely, so unattended runs should pass a
        budget.  Ships are written as they are found, so stopping early
        keeps everything collected so far.
        """
        offset = self.next_index() if resume else 0
        successes = 0
        attempts = 0
        started = time.monotonic()
        while successes < self.iterations:
            elapsed = time.monotonic() - started
            if time_budget_s is not None and elapsed >= time_budget_s:
                print("  budget reached after %.0fs" % elapsed)
                break
            if max_attempts is not None and attempts >= max_attempts:
                print("  attempt limit reached")
                break
            attempts += 1
            if self.process(self.generate_rule(), offset + successes):
                successes += 1
                print("  kept %d/%d (pool %d) after %d rules, %.0fs" % (
                    successes, self.iterations, offset + successes,
                    attempts, elapsed
                ))
            elif attempts % 25 == 0:
                print("  %d rules tried, %d/%d ships kept, %.0fs" % (
                    attempts, successes, self.iterations, elapsed
                ))
        return successes, attempts
