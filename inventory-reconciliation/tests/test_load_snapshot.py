"""Tests for load_snapshot — the full data loading pipeline."""

import os

import config
from reconcile import load_snapshot

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestLoadSnapshotRecords:
    """Verify records are loaded, normalized, and keyed by SKU."""

    def test_record_count_excludes_duplicates(self):
        records, _ = load_snapshot(
            os.path.join(FIXTURES, "snapshot_1_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_1"],
            "snapshot_1",
        )
        # 5 rows, but SKU-004 appears twice → both excluded → 3 records
        assert len(records) == 3

    def test_sku_normalization_applied(self):
        records, _ = load_snapshot(
            os.path.join(FIXTURES, "snapshot_2_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_2"],
            "snapshot_2",
        )
        # SKU005 → SKU-005, sku-003 → SKU-003
        assert "SKU-005" in records
        assert "SKU-003" in records

    def test_quantity_parsed_as_int(self):
        records, _ = load_snapshot(
            os.path.join(FIXTURES, "snapshot_2_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_2"],
            "snapshot_2",
        )
        # "70.0" → 70
        assert records["SKU-005"]["quantity"] == 70

    def test_name_whitespace_stripped(self):
        records, _ = load_snapshot(
            os.path.join(FIXTURES, "snapshot_2_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_2"],
            "snapshot_2",
        )
        assert records["SKU-005"]["name"] == "Widget B"

    def test_date_normalized_to_iso(self):
        records, _ = load_snapshot(
            os.path.join(FIXTURES, "snapshot_2_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_2"],
            "snapshot_2",
        )
        assert records["SKU-003"]["date"] == "2024-01-15"


class TestLoadSnapshotQualityIssues:
    """Verify data quality issues are detected and reported."""

    def test_duplicate_sku_flagged(self):
        _, issues = load_snapshot(
            os.path.join(FIXTURES, "snapshot_1_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_1"],
            "snapshot_1",
        )
        dup_issues = [i for i in issues if "duplicate" in i["issue"]]
        assert len(dup_issues) == 1
        assert dup_issues[0]["value"] == "SKU-004"
        assert dup_issues[0]["severity"] == "error"

    def test_float_quantity_flagged(self):
        _, issues = load_snapshot(
            os.path.join(FIXTURES, "snapshot_2_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_2"],
            "snapshot_2",
        )
        float_issues = [i for i in issues if "float" in i["issue"]]
        assert len(float_issues) >= 1

    def test_sku_normalization_flagged(self):
        _, issues = load_snapshot(
            os.path.join(FIXTURES, "snapshot_2_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_2"],
            "snapshot_2",
        )
        norm_issues = [i for i in issues if "normalized to" in i["issue"] and i["field"] == "sku"]
        # SKU005 and sku-003 both get normalized
        assert len(norm_issues) >= 2

    def test_whitespace_in_name_flagged(self):
        _, issues = load_snapshot(
            os.path.join(FIXTURES, "snapshot_2_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_2"],
            "snapshot_2",
        )
        ws_issues = [i for i in issues if "whitespace" in i["issue"]]
        assert len(ws_issues) >= 1

    def test_date_format_normalization_flagged(self):
        _, issues = load_snapshot(
            os.path.join(FIXTURES, "snapshot_2_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_2"],
            "snapshot_2",
        )
        date_issues = [i for i in issues if "date" in i["field"] and "normalized" in i["issue"]]
        assert len(date_issues) >= 1

    def test_missing_sku_flagged(self):
        _, issues = load_snapshot(
            os.path.join(FIXTURES, "snapshot_2_small.csv"),
            config.COLUMN_MAPPINGS["snapshot_2"],
            "snapshot_2",
        )
        missing = [i for i in issues if i["issue"] == "missing SKU"]
        assert len(missing) == 1
        assert missing[0]["severity"] == "error"
