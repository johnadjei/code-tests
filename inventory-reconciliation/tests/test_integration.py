"""Integration test: full pipeline from CSV files to reconciliation results."""

import csv
import json
import os
import sys

from reconcile import main

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _run_pipeline(tmp_path, monkeypatch):
    """Run the full pipeline against small fixtures, return parsed JSON output."""
    snap1 = os.path.abspath(os.path.join(FIXTURES, "snapshot_1_small.csv"))
    snap2 = os.path.abspath(os.path.join(FIXTURES, "snapshot_2_small.csv"))
    out_dir = str(tmp_path / "output")

    monkeypatch.setattr(sys, "argv", ["reconcile.py", snap1, snap2, "-o", out_dir])
    main()

    with open(os.path.join(out_dir, "reconciliation.json")) as f:
        json_data = json.load(f)

    with open(os.path.join(out_dir, "summary.csv")) as f:
        csv_rows = list(csv.DictReader(f))

    return json_data, csv_rows


class TestIntegrationReconciliation:
    """Verify specific reconciliation results from fixture data."""

    def test_matched_skus(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        matched_skus = {m["sku"] for m in data["matched"]}
        assert matched_skus == {"SKU-001", "SKU-003"}

    def test_matched_quantity_delta(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        by_sku = {m["sku"]: m for m in data["matched"]}
        # SKU-001: 100 → 110
        assert by_sku["SKU-001"]["quantity_before"] == 100
        assert by_sku["SKU-001"]["quantity_after"] == 110
        assert by_sku["SKU-001"]["quantity_delta"] == 10
        # SKU-003: 30 → 30
        assert by_sku["SKU-003"]["quantity_delta"] == 0

    def test_matched_field_changes(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        by_sku = {m["sku"]: m for m in data["matched"]}
        # Both have date changes (2024-01-08 → 2024-01-15)
        assert by_sku["SKU-001"]["field_changes"]["date"] == {
            "before": "2024-01-08", "after": "2024-01-15",
        }
        assert by_sku["SKU-003"]["field_changes"]["date"] == {
            "before": "2024-01-08", "after": "2024-01-15",
        }

    def test_added_skus(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        added_skus = {a["sku"] for a in data["added"]}
        # SKU-005 (normalized from SKU005) and SKU-006 are new
        assert added_skus == {"SKU-005", "SKU-006"}

    def test_removed_skus(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        removed_skus = {r["sku"] for r in data["removed"]}
        # SKU-002 only in snapshot 1; SKU-004 excluded from both sides (duplicate in s1)
        assert removed_skus == {"SKU-002"}

    def test_duplicate_excluded_from_matched(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        all_matched_skus = {m["sku"] for m in data["matched"]}
        assert "SKU-004" not in all_matched_skus


class TestIntegrationQualityIssues:
    """Verify quality issues are detected and reported."""

    def test_total_issue_count(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        assert data["metadata"]["quality_issues"] == len(data["data_quality_issues"])

    def test_duplicate_flagged(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        dup_issues = [i for i in data["data_quality_issues"] if "duplicate" in i["issue"]]
        assert len(dup_issues) == 1
        assert dup_issues[0]["value"] == "SKU-004"

    def test_missing_sku_flagged(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        missing = [i for i in data["data_quality_issues"] if i["issue"] == "missing SKU"]
        assert len(missing) == 1

    def test_float_quantity_flagged(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        floats = [i for i in data["data_quality_issues"] if "float" in i["issue"]]
        assert len(floats) == 1
        assert floats[0]["value"] == "70.0"

    def test_sku_normalization_flagged(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        norm = [i for i in data["data_quality_issues"]
                if i["field"] == "sku" and "normalized" in i["issue"]]
        # SKU005 and sku-003
        assert len(norm) == 2

    def test_date_normalization_flagged(self, tmp_path, monkeypatch):
        data, _ = _run_pipeline(tmp_path, monkeypatch)
        dates = [i for i in data["data_quality_issues"]
                 if i["field"] == "date" and "normalized" in i["issue"]]
        assert len(dates) == 1
        assert dates[0]["value"] == "01/15/2024"


class TestIntegrationCsvOutput:
    """Verify the summary CSV matches the JSON results."""

    def test_csv_row_count_matches_json(self, tmp_path, monkeypatch):
        data, csv_rows = _run_pipeline(tmp_path, monkeypatch)
        expected = len(data["matched"]) + len(data["added"]) + len(data["removed"])
        assert len(csv_rows) == expected

    def test_csv_statuses(self, tmp_path, monkeypatch):
        _, csv_rows = _run_pipeline(tmp_path, monkeypatch)
        statuses = {r["status"] for r in csv_rows}
        assert statuses == {"matched", "added", "removed"}

    def test_csv_matched_row_content(self, tmp_path, monkeypatch):
        _, csv_rows = _run_pipeline(tmp_path, monkeypatch)
        matched = {r["sku"]: r for r in csv_rows if r["status"] == "matched"}
        assert matched["SKU-001"]["quantity_before"] == "100"
        assert matched["SKU-001"]["quantity_after"] == "110"
        assert matched["SKU-001"]["quantity_change"] == "10"
