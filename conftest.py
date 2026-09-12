# Root conftest so `pytest tests/` works no matter how it's invoked:
# pytest prepends this file's directory to sys.path, making `src`
# importable without an install step.
