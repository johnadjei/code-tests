# Installation

Requires **Python 3.10+** (enforced by `pyproject.toml`).

## 1. Create a virtual environment

```bash
python3 -m venv .venv
```

Isolates project dependencies from your system Python. The `.venv` directory is already in `.gitignore`.

## 2. Activate and install

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

- `-e` (editable mode) links the project in-place so code changes take effect immediately without reinstalling.
- `.[dev]` installs the package itself plus the `dev` optional dependencies defined in `pyproject.toml` (currently just `pytest`).

## 3. Verify

```bash
python --version   # should be 3.10+
pytest --version   # should be installed
```

## Running the reconciliation

```bash
python reconcile.py
```

Uses default paths from `config.py` (`data/snapshot_1.csv`, `data/snapshot_2.csv`, output to `output/`). To specify paths explicitly:

```bash
python reconcile.py data/snapshot_1.csv data/snapshot_2.csv --output output/
```

## Running tests

```bash
pytest
```
