#!/bin/zsh
# One-shot setup for the automons pipeline on an Apple Silicon Mac.
# Idempotent: safe to re-run. See docs/HANDOFF.md for the why of each step.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> submodules"
git submodule update --init

echo "==> patch lifelib's cpads for clang 21 (escape in static_assert message)"
# Local, uncommitted patch inside the submodule — git submodule update
# reverts it, so this script must stay idempotent.
perl -0pi -e 's/#define colour_assert\(x, y\) static_assert\(x, "\\033\[32;1m" y "\\033\[0m"\)/#define colour_assert(x, y) static_assert(x, y)/' \
    submodules/lifelib/cpads/include/cpads/core.hpp

echo "==> build ntzfind"
(cd submodules/ntzfind && g++ -std=c++11 -O3 -march=native -o ntzfind ntzfind.cpp 2>/dev/null)

echo "==> arm64 venv (.venv): tests, search, totalistic plots"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

echo "==> x86_64 venv (.venv-x86): everything that imports lifelib (Rosetta)"
# lifelib's avxlife is x86 assembly with no arm64 port; Rosetta 2 runs it
# (SSE4.2). uv fetches a real x86_64 CPython.
uv python install cpython-3.12-macos-x86_64-none
[ -d .venv-x86 ] || uv venv --python cpython-3.12-macos-x86_64-none .venv-x86
VIRTUAL_ENV=.venv-x86 uv pip install -q -r requirements.txt

echo "==> smoke tests"
.venv/bin/python -m pytest tests/ -q
.venv-x86/bin/python -c "
from submodules import lifelib
from src import ruletable
assert ruletable.verify_oracle(lifelib)
print('lifelib oracle verified under Rosetta')
"
echo "setup complete"
