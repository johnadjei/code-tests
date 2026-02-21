# Notes

## Approach

The script loads two CSV snapshots, normalizes their schemas via config-driven column mappings, cleans up each field (SKU casing/hyphens, whitespace, date formats, quantity types), and flags data quality issues along the way. It then compares the normalized snapshots by SKU — reporting matched items with quantity deltas, added items, and removed items. Output goes to a JSON report (full structure for downstream use) and a flat summary CSV (quick human review).

## Key Decisions

- **Config-driven column mapping** — the two snapshots use different column names (`name` vs `product_name`, `quantity` vs `qty`, etc.). A mapping dict in `config.py` keeps this explicit and easy to update if schemas change.
- **Flag-and-skip for duplicates** — when a SKU appears twice in the same snapshot, both rows are excluded rather than guessing which is correct. `SKU-045` appears as "removed" because of this — it's duplicated in snapshot 2, so only snapshot 1's record exists, and there's nothing to match against.
- **SKU normalization** — handles casing and missing hyphens (`sku005` → `SKU-005`) via a named function. Clear, modifiable, no over-abstraction.
- **Date ambiguity** — `01/15/2024` is treated as US format (`MM/DD/YYYY`). Since no day value exceeds 12 this is technically ambiguous, but it matches the `2024-01-15` pattern in the rest of snapshot 2.

## Data Quality Findings

13 issues found across the two snapshots:

- **Whitespace** (5) — leading/trailing spaces in product names across both snapshots, e.g. `" Widget B"`, `"Cable Ties 100pk "`. Stripped on load.
- **SKU formatting** (3) — missing hyphens and inconsistent casing in snapshot 2 (`SKU005`, `sku-008`, `SKU018`). Normalized to `SKU-NNN`.
- **Float quantities** (2) — `70.0` and `80.00` in snapshot 2. Truncated to integers and flagged.
- **Date format** (1) — `01/15/2024` instead of ISO. Normalized.
- **Duplicate + negative qty** (2) — `SKU-045` appears on rows 44 and 54 of snapshot 2; row 54 also has quantity `-5`. Both rows excluded.
