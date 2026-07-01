# hookman — Developer Tooling Reference

## Environment setup

This project uses a plain virtualenv (not pixi, despite the presence of `pixi.devenv.toml`).

```bash
python -m venv .venv

# Windows
.venv/Scripts/pip install -e . -r requirements_dev.txt

# Linux
.venv/bin/pip install -e . -r requirements_dev.txt
```

## Type checking

```bash
prek run mypy -a
```

## Running tests

```bash
# Windows
.venv/Scripts/pytest tests/test_hooks.py tests/test_hookman_utils.py -v

# Linux
.venv/bin/pytest tests/test_hooks.py tests/test_hookman_utils.py -v
```

Some tests require compiled C++ artifacts (see **Building** below). The
`add_artifacts_to_path` autouse fixture in `conftest.py` adds `build/artifacts`
to `sys.path` automatically, so no `PYTHONPATH` setup is needed.

## Building C++ artifacts

```bash
# Windows
.venv/Scripts/inv build

# Linux
.venv/bin/inv build
```

This compiles the test plugins (`.dll`/`.so`) and the pybind11 binding
(`.pyd`/`.so`), installing them to `build/artifacts/`. Must be re-run whenever
C++ source files change.

On Windows, requires Visual Studio with MSVC. On Linux, requires a C++ compiler
(e.g. `g++`) and `ninja`.

## Regenerating file regression snapshots

Some tests in `test_hookman_generator.py` use `pytest-regressions` to compare
generated files against stored snapshots. When the generator output changes
intentionally, regenerate the snapshots with:

```bash
# Windows
.venv/Scripts/pytest tests/test_hookman_generator.py --force-regen

# Linux
.venv/bin/pytest tests/test_hookman_generator.py --force-regen
```

Then verify the regenerated files look correct before committing them.

## Pre-commit / linting

```bash
prek run --all-files
```

This runs mypy, ruff, and other hooks defined in `.pre-commit-config.yaml`.
