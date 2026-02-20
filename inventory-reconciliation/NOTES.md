# Notes

## Approach

TODO: Fill in after implementation is complete.

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
