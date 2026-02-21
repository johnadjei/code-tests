# Notes

## Approach

The script loads two CSV snapshots, normalizes their schemas via config-driven column mappings, cleans up each field (SKU casing/hyphens, whitespace, date formats, quantity types), and flags anything suspicious along the way. Duplicates within a snapshot are excluded entirely — both rows get dropped rather than picking one arbitrarily.

The reconciliation step compares the two normalized snapshots by SKU — items present in both get a quantity delta and any field-level changes tracked, items only in snapshot 2 are flagged as added, and items only in snapshot 1 as removed. Results are sorted by SKU for deterministic output.

Output is written to two files: a JSON report with metadata, quality issues, and full reconciliation results for downstream consumption, and a flat summary CSV for quick human review. The CSV maps each item to a status (matched/added/removed) with before/after quantities.

The whole thing is driven by a CLI (`python reconcile.py`) that accepts optional snapshot paths and output directory, defaulting to paths in `config.py`. Paths are resolved relative to the script's location so it works the same whether invoked from the project root or elsewhere.

79 tests cover the following: normalization, column mapping, data loading, reconciliation logic, output generation, CLI argument parsing, and end-to-end integration (asserting on specific SKU classifications, quantity deltas, quality issue detection, and CSV/JSON output consistency).

## Key Decisions

- **Config-driven column mapping** — the two snapshots use different column names (`name` vs `product_name`, `quantity` vs `qty`, etc.). A mapping dict in `config.py` keeps this explicit and easy to update if schemas change.
- **Flag-and-skip for ambiguous data** — when a SKU appears twice in the same snapshot, both rows are excluded from reconciliation rather than guessing which is correct. Better to under-report than misreport.
- **JSON primary output + summary CSV** — JSON captures the full structure (metadata, deltas, quality issues) for downstream use. The CSV is a flat view for quick human review.
- **SKU normalization as a named function** — handles casing and missing hyphens (`sku005` → `SKU-005`). Clear, modifiable, no over-abstraction.
- **`pyproject.toml` over `requirements.txt`** — enforces `requires-python >= 3.10` at install time; pytest is the only dependency, listed under `[project.optional-dependencies] dev`.

## Data Quality Findings

13 issues across the two snapshots. Grouped by category:

**Whitespace in names (5)** — trailing space on `"Cable Ties 100pk "` and leading space on `" Compressed Air Can"` in snapshot 1. Snapshot 2 has leading space on `" Widget B"`, trailing on `"Mounting Bracket Large "`, and both on `" HDMI Cable 3ft "`. All stripped during normalization.

**Float quantities (2)** — snapshot 2 has `70.0` and `80.00` where integers are expected. Truncated to `70` and `80` but flagged as warnings.

**SKU formatting (3)** — snapshot 2 has `SKU005`, `sku-008`, and `SKU018` (missing hyphens, inconsistent casing). All normalized to `SKU-005`, `SKU-008`, `SKU-018`.

**Date format (1)** — snapshot 2 row 34 uses `01/15/2024` (US format) while everything else is ISO `2024-01-15`. Normalized on load.

**Duplicate SKU (1)** — `SKU-045` appears twice in snapshot 2 (rows 44 and 54). Row 54 also has a negative quantity (`-5`). Both rows excluded from reconciliation per the flag-and-skip policy. This means `SKU-045` shows up as "removed" since it's only usable in snapshot 1.

**Negative quantity (1)** — the duplicate `SKU-045` row 54 has `-5`. Flagged as an error alongside the duplicate.

## Reconciliation Results

- **72 matched** — all show a date change (`2024-01-08` → `2024-01-15`). Most have quantity decreases; two items (`SKU-006`, `SKU-007`) are unchanged.
- **5 added** — `SKU-076` through `SKU-080` (Stream Deck Mini, Stream Deck XL, Capture Card, USB-C Hub, Thunderbolt Cable). All in Warehouse A.
- **3 removed** — `SKU-025` (VGA Cable), `SKU-026` (DVI Cable), and `SKU-045` (Multimeter Pro, excluded due to duplicate in snapshot 2).

## Assumptions

- SKUs follow a `SKU-NNN` pattern. Anything matching `SKU` prefix with digits gets normalized to this format.
- Quantities should be non-negative integers. Floats are truncated (not rounded) and flagged. Negatives are flagged as errors but still loaded.
- When a SKU appears twice in the same snapshot, the data is considered ambiguous — both rows are dropped rather than choosing one. This is conservative but avoids silent misreporting.
- The `01/15/2024` date is assumed to be US format (`MM/DD/YYYY`), not `DD/MM/YYYY`. Since no day value exceeds 12 in the data, this is ambiguous — but US format is listed first in the accepted formats, and it matches the `2024-01-15` dates in the rest of snapshot 2.
- `SKU-045` appearing as "removed" is a side effect of the duplicate exclusion. In reality, it likely still exists — the snapshot 2 data is just unreliable for that item.

## Production Considerations

- **External config** — `config.py` works for a standalone script, but a production pipeline would load mappings from YAML/JSON or a database so non-engineers can update them without touching code.
- **Logging** — `print()` statements would become structured logging with levels, making it easier to pipe into monitoring tools.
- **Validation layer** — the current approach interleaves validation with loading. At scale, separating these into distinct stages (validate → load → reconcile → output) would make each independently testable and composable.
- **Idempotency** — output currently overwrites on each run. A production version would include run IDs or timestamps in filenames, or write to a versioned store.
