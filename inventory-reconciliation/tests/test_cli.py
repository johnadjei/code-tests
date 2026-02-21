"""Tests for CLI argument parsing and main entrypoint."""

import json
import os
import sys

import config
from reconcile import build_parser, main


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestBuildParser:
    def test_defaults_from_config(self):
        parser = build_parser()
        args = parser.parse_args([])
        assert args.snapshot_1 == config.DEFAULT_SNAPSHOT_1
        assert args.snapshot_2 == config.DEFAULT_SNAPSHOT_2
        assert args.output == config.DEFAULT_OUTPUT_DIR

    def test_positional_args(self):
        parser = build_parser()
        args = parser.parse_args(["a.csv", "b.csv"])
        assert args.snapshot_1 == "a.csv"
        assert args.snapshot_2 == "b.csv"

    def test_output_flag_short(self):
        parser = build_parser()
        args = parser.parse_args(["-o", "results/"])
        assert args.output == "results/"

    def test_output_flag_long(self):
        parser = build_parser()
        args = parser.parse_args(["--output", "results/"])
        assert args.output == "results/"

    def test_all_args_together(self):
        parser = build_parser()
        args = parser.parse_args(["snap1.csv", "snap2.csv", "-o", "out/"])
        assert args.snapshot_1 == "snap1.csv"
        assert args.snapshot_2 == "snap2.csv"
        assert args.output == "out/"


class TestMain:
    def _run_main(self, tmp_path, monkeypatch):
        """Helper: run main() with fixture CSVs, absolute paths to bypass script_dir joining."""
        snap1 = os.path.abspath(os.path.join(FIXTURES, "snapshot_1_small.csv"))
        snap2 = os.path.abspath(os.path.join(FIXTURES, "snapshot_2_small.csv"))
        out_dir = str(tmp_path / "output")

        # Pass absolute paths so os.path.join(script_dir, abs_path) == abs_path
        monkeypatch.setattr(
            sys, "argv",
            ["reconcile.py", snap1, snap2, "-o", out_dir],
        )

        main()
        return out_dir

    def test_creates_output_files(self, tmp_path, monkeypatch):
        out_dir = self._run_main(tmp_path, monkeypatch)
        assert os.path.exists(os.path.join(out_dir, "reconciliation.json"))
        assert os.path.exists(os.path.join(out_dir, "summary.csv"))

    def test_json_top_level_keys(self, tmp_path, monkeypatch):
        out_dir = self._run_main(tmp_path, monkeypatch)
        with open(os.path.join(out_dir, "reconciliation.json")) as f:
            data = json.load(f)
        assert "metadata" in data
        assert "data_quality_issues" in data
        assert "matched" in data
        assert "added" in data
        assert "removed" in data

    def test_metadata_counts(self, tmp_path, monkeypatch):
        out_dir = self._run_main(tmp_path, monkeypatch)
        with open(os.path.join(out_dir, "reconciliation.json")) as f:
            meta = json.load(f)["metadata"]
        # snapshot_1_small: 5 rows, SKU-004 duplicate → 3 records
        assert meta["snapshot_1_records"] == 3
        # snapshot_2_small: 5 rows, 1 missing SKU → 4 valid records
        assert meta["snapshot_2_records"] == 4
