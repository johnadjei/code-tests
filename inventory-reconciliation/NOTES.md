# Notes

## Approach

The script loads two CSV snapshots, normalizes their schemas via config-driven column mappings, cleans up each field (SKU casing/hyphens, whitespace, date formats, quantity types), and flags anything suspicious along the way. Duplicates within a snapshot are excluded entirely — both rows get dropped rather than picking one arbitrarily.

The reconciliation step compares the two normalized snapshots by SKU — items present in both get a quantity delta and any field-level changes tracked, items only in snapshot 2 are flagged as added, and items only in snapshot 1 as removed. Results are sorted by SKU for deterministic output.

Output is written to two files: a JSON report with metadata, quality issues, and full reconciliation results for downstream consumption, and a flat summary CSV for quick human review. The CSV maps each item to a status (matched/added/removed) with before/after quantities.

The whole thing is driven by a CLI (`python reconcile.py`) that accepts optional snapshot paths and output directory, defaulting to paths in `config.py`. Paths are resolved relative to the script's location so it works the same whether invoked from the project root or elsewhere.

Tests cover the following: normalization, column mapping, data loading, reconciliation logic, output generation, CLI argument parsing, and end-to-end runs.

## Key Decisions

- **Config-driven column mapping** — the two snapshots use different column names (`name` vs `product_name`, `quantity` vs `qty`, etc.). A mapping dict in `config.py` keeps this explicit and easy to update if schemas change.
- **Flag-and-skip for ambiguous data** — when a SKU appears twice in the same snapshot, both rows are excluded from reconciliation rather than guessing which is correct. Better to under-report than misreport.
- **JSON primary output + summary CSV** — JSON captures the full structure (metadata, deltas, quality issues) for downstream use. The CSV is a flat view for quick human review.
- **SKU normalization as a named function** — handles casing and missing hyphens (`sku005` → `SKU-005`). Clear, modifiable, no over-abstraction.
- **`pyproject.toml` over `requirements.txt`** — enforces `requires-python >= 3.10` at install time; pytest is the only dependency, listed under `[project.optional-dependencies] dev`.

## Data Quality Findings

TODO: Fill in after running reconciliation against provided data.

## Assumptions

TODO: Fill in after implementation is complete.

## Production Considerations

TODO: Fill in after implementation is complete.
