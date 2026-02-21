"""Inventory reconciliation: compare two CSV snapshots and report changes."""

import csv
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
