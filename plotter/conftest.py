# pytest inserts this file's directory into sys.path, which makes the
# `lifeplot` package importable for plotter/tests/ without an install
# step -- the same trick as the repo-root conftest.py does for `src`.
