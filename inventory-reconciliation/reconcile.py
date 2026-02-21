"""Inventory reconciliation: compare two CSV snapshots and report changes."""

import argparse
import csv
import json
import os
import re
from datetime import datetime

import config


# ---------------------------------------------------------------------------
# SKU normalization
# ---------------------------------------------------------------------------

def normalize_sku(raw_sku: str) -> str:
    """Normalize a SKU to uppercase with hyphen separator.

    Examples:
        "SKU005"  → "SKU-005"
        "sku-008" → "SKU-008"
        "SKU-001" → "SKU-001"
    """
    s = raw_sku.strip().upper()
    # Remove any existing separators to get the raw prefix + number
    digits = re.sub(r"^SKU[-_\s]*", "", s)
    return f"{config.SKU_PREFIX}{config.SKU_SEPARATOR}{digits}"


# ---------------------------------------------------------------------------
# Data loading & normalization
# ---------------------------------------------------------------------------

def apply_column_mapping(row: dict, mapping: dict) -> dict:
    """Map source column names to canonical names using the provided mapping."""
    mapped = {}
    for source_col, canonical_col in mapping.items():
        if source_col in row:
            mapped[canonical_col] = row[source_col]
    return mapped


def normalize_date(raw_date: str) -> tuple[str, bool]:
    """Parse a date string and return (ISO formatted string, had_issue).

    Returns the original string and True if no accepted format matched.
    """
    cleaned = raw_date.strip()
    for fmt in config.DATE_FORMATS_ACCEPTED:
        try:
            return datetime.strptime(cleaned, fmt).strftime(config.DATE_FORMAT_ISO), False
        except ValueError:
            continue
    return cleaned, True


def parse_quantity(raw_qty: str) -> tuple[int, list[str]]:
    """Parse a quantity string into an integer. Returns (value, list_of_issues).

    Flags floats (even if .0) and negatives as issues.
    """
    issues = []
    cleaned = raw_qty.strip()
    try:
        val = float(cleaned)
    except (ValueError, TypeError):
        return 0, [f"non-numeric quantity: {raw_qty!r}"]

    if val < 0:
        issues.append(f"negative quantity: {cleaned}")

    if "." in cleaned:
        issues.append(f"float quantity: {cleaned}")

    return int(val), issues


def load_snapshot(filepath: str, mapping: dict, label: str) -> tuple[dict, list[dict]]:
    """Load a CSV snapshot and return (records_by_sku, quality_issues).

    Records with duplicate SKUs are flagged and excluded from the
    returned dict so they don't silently corrupt the reconciliation.
    """
    records = {}
    issues = []
    seen_skus: dict[str, int] = {}  # normalized_sku → first row number

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row_num, raw_row in enumerate(reader, start=2):  # row 1 is header
            row = apply_column_mapping(raw_row, mapping)

            raw_sku = row.get("sku", "").strip()
            if not raw_sku:
                issues.append({
                    "source": label,
                    "row": row_num,
                    "field": "sku",
                    "value": "",
                    "issue": "missing SKU",
                    "severity": "error",
                })
                continue

            # Normalize SKU
            original_sku = raw_sku
            sku = normalize_sku(raw_sku)
            if original_sku != sku:
                issues.append({
                    "source": label,
                    "row": row_num,
                    "field": "sku",
                    "value": original_sku,
                    "issue": f"SKU formatting normalized to {sku}",
                    "severity": "warning",
                })

            # Normalize name (strip whitespace)
            raw_name = row.get("name", "")
            name = raw_name.strip()
            if raw_name != name:
                issues.append({
                    "source": label,
                    "row": row_num,
                    "field": "name",
                    "value": repr(raw_name),
                    "issue": "leading/trailing whitespace in name",
                    "severity": "warning",
                })

            # Parse quantity
            raw_qty = row.get("quantity", "0")
            quantity, qty_issues = parse_quantity(raw_qty)
            for qi in qty_issues:
                issues.append({
                    "source": label,
                    "row": row_num,
                    "field": "quantity",
                    "value": raw_qty.strip(),
                    "issue": qi,
                    "severity": "error" if "negative" in qi else "warning",
                })

            # Normalize date
            raw_date = row.get("date", "")
            date_str, date_issue = normalize_date(raw_date)
            if date_issue:
                issues.append({
                    "source": label,
                    "row": row_num,
                    "field": "date",
                    "value": raw_date.strip(),
                    "issue": "unrecognized date format",
                    "severity": "warning",
                })
            elif raw_date.strip() != date_str:
                issues.append({
                    "source": label,
                    "row": row_num,
                    "field": "date",
                    "value": raw_date.strip(),
                    "issue": f"date format normalized to {date_str}",
                    "severity": "warning",
                })

            # Normalize location
            location = row.get("location", "").strip()

            record = {
                "sku": sku,
                "name": name,
                "quantity": quantity,
                "location": location,
                "date": date_str,
            }

            # Duplicate detection
            if sku in seen_skus:
                issues.append({
                    "source": label,
                    "row": row_num,
                    "field": "sku",
                    "value": sku,
                    "issue": f"duplicate SKU (first seen row {seen_skus[sku]}); both rows excluded from reconciliation",
                    "severity": "error",
                })
                # Remove the first occurrence too — ambiguous data
                records.pop(sku, None)
                continue

            seen_skus[sku] = row_num
            records[sku] = record

    return records, issues


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

def reconcile(snapshot_1: dict, snapshot_2: dict) -> dict:
    """Compare two snapshot dicts and return matched, added, and removed items."""
    all_skus = set(snapshot_1.keys()) | set(snapshot_2.keys())

    matched = []
    added = []
    removed = []

    for sku in sorted(all_skus):
        in_s1 = sku in snapshot_1
        in_s2 = sku in snapshot_2

        if in_s1 and in_s2:
            s1 = snapshot_1[sku]
            s2 = snapshot_2[sku]
            qty_delta = s2["quantity"] - s1["quantity"]
            changes = {}
            for field in ("name", "location", "date"):
                if s1[field] != s2[field]:
                    changes[field] = {"before": s1[field], "after": s2[field]}
            matched.append({
                "sku": sku,
                "name": s2["name"],
                "quantity_before": s1["quantity"],
                "quantity_after": s2["quantity"],
                "quantity_delta": qty_delta,
                "field_changes": changes,
            })
        elif in_s2:
            added.append(snapshot_2[sku])
        else:
            removed.append(snapshot_1[sku])

    return {"matched": matched, "added": added, "removed": removed}


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def write_json(results: dict, issues: list[dict], metadata: dict, filepath: str) -> None:
    """Write the full reconciliation report as JSON."""
    output = {
        "metadata": metadata,
        "data_quality_issues": issues,
        **results,
    }
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)


def write_summary_csv(results: dict, filepath: str) -> None:
    """Write a flat summary CSV for quick human review."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    rows = []

    for item in results["matched"]:
        rows.append({
            "sku": item["sku"],
            "name": item["name"],
            "status": "matched",
            "quantity_before": item["quantity_before"],
            "quantity_after": item["quantity_after"],
            "quantity_change": item["quantity_delta"],
        })
    for item in results["added"]:
        rows.append({
            "sku": item["sku"],
            "name": item["name"],
            "status": "added",
            "quantity_before": "",
            "quantity_after": item["quantity"],
            "quantity_change": "",
        })
    for item in results["removed"]:
        rows.append({
            "sku": item["sku"],
            "name": item["name"],
            "status": "removed",
            "quantity_before": item["quantity"],
            "quantity_after": "",
            "quantity_change": "",
        })

    fieldnames = ["sku", "name", "status", "quantity_before", "quantity_after", "quantity_change"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare two inventory snapshots and report changes."
    )
    parser.add_argument(
        "snapshot_1",
        nargs="?",
        default=config.DEFAULT_SNAPSHOT_1,
        help=f"Path to the first snapshot CSV (default: {config.DEFAULT_SNAPSHOT_1})",
    )
    parser.add_argument(
        "snapshot_2",
        nargs="?",
        default=config.DEFAULT_SNAPSHOT_2,
        help=f"Path to the second snapshot CSV (default: {config.DEFAULT_SNAPSHOT_2})",
    )
    parser.add_argument(
        "--output", "-o",
        default=config.DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {config.DEFAULT_OUTPUT_DIR})",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Resolve paths relative to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    snap1_path = os.path.join(script_dir, args.snapshot_1)
    snap2_path = os.path.join(script_dir, args.snapshot_2)
    output_dir = os.path.join(script_dir, args.output)

    print(f"Loading snapshot 1: {snap1_path}")
    snap1, issues1 = load_snapshot(snap1_path, config.COLUMN_MAPPINGS["snapshot_1"], "snapshot_1")

    print(f"Loading snapshot 2: {snap2_path}")
    snap2, issues2 = load_snapshot(snap2_path, config.COLUMN_MAPPINGS["snapshot_2"], "snapshot_2")

    all_issues = issues1 + issues2

    print(f"Reconciling {len(snap1)} items from snapshot 1 with {len(snap2)} items from snapshot 2...")
    results = reconcile(snap1, snap2)

    metadata = {
        "run_timestamp": datetime.now().isoformat(),
        "snapshot_1_path": args.snapshot_1,
        "snapshot_2_path": args.snapshot_2,
        "snapshot_1_records": len(snap1),
        "snapshot_2_records": len(snap2),
        "matched": len(results["matched"]),
        "added": len(results["added"]),
        "removed": len(results["removed"]),
        "quality_issues": len(all_issues),
    }

    json_path = os.path.join(output_dir, config.OUTPUT_JSON_FILENAME)
    csv_path = os.path.join(output_dir, config.OUTPUT_CSV_FILENAME)

    write_json(results, all_issues, metadata, json_path)
    write_summary_csv(results, csv_path)

    print(f"\nResults written to:")
    print(f"  {json_path}")
    print(f"  {csv_path}")
    print(f"\nSummary:")
    print(f"  Matched: {metadata['matched']}")
    print(f"  Added:   {metadata['added']}")
    print(f"  Removed: {metadata['removed']}")
    print(f"  Quality issues: {metadata['quality_issues']}")


if __name__ == "__main__":
    main()
