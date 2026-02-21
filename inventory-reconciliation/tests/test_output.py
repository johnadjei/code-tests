"""Tests for JSON and CSV output generation."""

import csv
import json
import os

from reconcile import write_json, write_summary_csv


def _sample_results():
    return {
        "matched": [
            {
                "sku": "SKU-001",
                "name": "Widget A",
                "quantity_before": 100,
                "quantity_after": 110,
                "quantity_delta": 10,
                "field_changes": {"location": {"before": "WH-A", "after": "WH-B"}},
            },
        ],
        "added": [
            {"sku": "SKU-076", "name": "New Item", "quantity": 40, "location": "WH-D", "date": "2024-01-15"},
        ],
        "removed": [
            {"sku": "SKU-025", "name": "Old Item", "quantity": 30, "location": "WH-A", "date": "2024-01-08"},
        ],
    }


def _sample_issues():
    return [
        {"source": "snapshot_2", "row": 3, "field": "quantity", "value": "70.0", "issue": "float quantity: 70.0", "severity": "warning"},
    ]


def _sample_metadata():
    return {
        "run_timestamp": "2024-01-15T12:00:00",
        "snapshot_1_records": 75,
        "snapshot_2_records": 78,
        "matched": 1,
        "added": 1,
        "removed": 1,
        "quality_issues": 1,
    }


class TestWriteJson:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "out" / "report.json")
        write_json(_sample_results(), _sample_issues(), _sample_metadata(), path)
        assert os.path.exists(path)

    def test_creates_parent_directories(self, tmp_path):
        path = str(tmp_path / "nested" / "dir" / "report.json")
        write_json(_sample_results(), [], {}, path)
        assert os.path.exists(path)

    def test_contains_metadata(self, tmp_path):
        path = str(tmp_path / "report.json")
        write_json(_sample_results(), _sample_issues(), _sample_metadata(), path)
        with open(path) as f:
            data = json.load(f)
        assert data["metadata"]["matched"] == 1
        assert data["metadata"]["run_timestamp"] == "2024-01-15T12:00:00"

    def test_contains_quality_issues(self, tmp_path):
        path = str(tmp_path / "report.json")
        write_json(_sample_results(), _sample_issues(), _sample_metadata(), path)
        with open(path) as f:
            data = json.load(f)
        assert len(data["data_quality_issues"]) == 1
        assert data["data_quality_issues"][0]["issue"] == "float quantity: 70.0"

    def test_contains_reconciliation_results(self, tmp_path):
        path = str(tmp_path / "report.json")
        write_json(_sample_results(), _sample_issues(), _sample_metadata(), path)
        with open(path) as f:
            data = json.load(f)
        assert len(data["matched"]) == 1
        assert len(data["added"]) == 1
        assert len(data["removed"]) == 1

    def test_valid_json(self, tmp_path):
        path = str(tmp_path / "report.json")
        write_json(_sample_results(), _sample_issues(), _sample_metadata(), path)
        with open(path) as f:
            data = json.load(f)  # would raise if invalid
        assert isinstance(data, dict)


class TestWriteSummaryCsv:
    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "summary.csv")
        write_summary_csv(_sample_results(), path)
        assert os.path.exists(path)

    def test_header_row(self, tmp_path):
        path = str(tmp_path / "summary.csv")
        write_summary_csv(_sample_results(), path)
        with open(path) as f:
            reader = csv.reader(f)
            header = next(reader)
        assert header == ["sku", "name", "status", "quantity_before", "quantity_after", "quantity_change"]

    def test_row_count(self, tmp_path):
        path = str(tmp_path / "summary.csv")
        write_summary_csv(_sample_results(), path)
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # 1 matched + 1 added + 1 removed
        assert len(rows) == 3

    def test_matched_row(self, tmp_path):
        path = str(tmp_path / "summary.csv")
        write_summary_csv(_sample_results(), path)
        with open(path) as f:
            rows = list(csv.DictReader(f))
        matched = [r for r in rows if r["status"] == "matched"]
        assert len(matched) == 1
        assert matched[0]["sku"] == "SKU-001"
        assert matched[0]["quantity_before"] == "100"
        assert matched[0]["quantity_after"] == "110"
        assert matched[0]["quantity_change"] == "10"

    def test_added_row(self, tmp_path):
        path = str(tmp_path / "summary.csv")
        write_summary_csv(_sample_results(), path)
        with open(path) as f:
            rows = list(csv.DictReader(f))
        added = [r for r in rows if r["status"] == "added"]
        assert len(added) == 1
        assert added[0]["sku"] == "SKU-076"
        assert added[0]["quantity_before"] == ""
        assert added[0]["quantity_after"] == "40"

    def test_removed_row(self, tmp_path):
        path = str(tmp_path / "summary.csv")
        write_summary_csv(_sample_results(), path)
        with open(path) as f:
            rows = list(csv.DictReader(f))
        removed = [r for r in rows if r["status"] == "removed"]
        assert len(removed) == 1
        assert removed[0]["sku"] == "SKU-025"
        assert removed[0]["quantity_after"] == ""
        assert removed[0]["quantity_change"] == ""

    def test_empty_results(self, tmp_path):
        path = str(tmp_path / "summary.csv")
        write_summary_csv({"matched": [], "added": [], "removed": []}, path)
        with open(path) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 0
