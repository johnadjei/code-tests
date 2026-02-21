"""Tests for reconciliation logic."""

from reconcile import reconcile


def _make_record(sku, name="Item", quantity=10, location="WH-A", date="2024-01-08"):
    return {"sku": sku, "name": name, "quantity": quantity, "location": location, "date": date}


class TestReconcileMatched:
    def test_matched_item_appears_in_matched(self):
        s1 = {"SKU-001": _make_record("SKU-001", quantity=100)}
        s2 = {"SKU-001": _make_record("SKU-001", quantity=110)}
        result = reconcile(s1, s2)
        assert len(result["matched"]) == 1
        assert result["matched"][0]["sku"] == "SKU-001"

    def test_quantity_delta_calculated(self):
        s1 = {"SKU-001": _make_record("SKU-001", quantity=100)}
        s2 = {"SKU-001": _make_record("SKU-001", quantity=80)}
        result = reconcile(s1, s2)
        assert result["matched"][0]["quantity_before"] == 100
        assert result["matched"][0]["quantity_after"] == 80
        assert result["matched"][0]["quantity_delta"] == -20

    def test_no_change_delta_is_zero(self):
        s1 = {"SKU-001": _make_record("SKU-001", quantity=50)}
        s2 = {"SKU-001": _make_record("SKU-001", quantity=50)}
        result = reconcile(s1, s2)
        assert result["matched"][0]["quantity_delta"] == 0

    def test_field_changes_detected(self):
        s1 = {"SKU-001": _make_record("SKU-001", name="Old Name", location="WH-A")}
        s2 = {"SKU-001": _make_record("SKU-001", name="New Name", location="WH-B")}
        result = reconcile(s1, s2)
        changes = result["matched"][0]["field_changes"]
        assert changes["name"] == {"before": "Old Name", "after": "New Name"}
        assert changes["location"] == {"before": "WH-A", "after": "WH-B"}

    def test_no_field_changes_empty_dict(self):
        s1 = {"SKU-001": _make_record("SKU-001")}
        s2 = {"SKU-001": _make_record("SKU-001")}
        result = reconcile(s1, s2)
        assert result["matched"][0]["field_changes"] == {}

    def test_matched_uses_snapshot_2_name(self):
        s1 = {"SKU-001": _make_record("SKU-001", name="Old")}
        s2 = {"SKU-001": _make_record("SKU-001", name="New")}
        result = reconcile(s1, s2)
        assert result["matched"][0]["name"] == "New"


class TestReconcileAdded:
    def test_item_only_in_snapshot_2_is_added(self):
        s1 = {}
        s2 = {"SKU-001": _make_record("SKU-001")}
        result = reconcile(s1, s2)
        assert len(result["added"]) == 1
        assert result["added"][0]["sku"] == "SKU-001"

    def test_added_contains_full_record(self):
        s1 = {}
        s2 = {"SKU-001": _make_record("SKU-001", name="Widget", quantity=40, location="WH-C")}
        result = reconcile(s1, s2)
        item = result["added"][0]
        assert item["name"] == "Widget"
        assert item["quantity"] == 40
        assert item["location"] == "WH-C"


class TestReconcileRemoved:
    def test_item_only_in_snapshot_1_is_removed(self):
        s1 = {"SKU-001": _make_record("SKU-001")}
        s2 = {}
        result = reconcile(s1, s2)
        assert len(result["removed"]) == 1
        assert result["removed"][0]["sku"] == "SKU-001"

    def test_removed_contains_full_record(self):
        s1 = {"SKU-001": _make_record("SKU-001", name="Widget", quantity=25, location="WH-B")}
        s2 = {}
        result = reconcile(s1, s2)
        item = result["removed"][0]
        assert item["name"] == "Widget"
        assert item["quantity"] == 25
        assert item["location"] == "WH-B"


class TestReconcileMixed:
    def test_mixed_scenario(self):
        s1 = {
            "SKU-001": _make_record("SKU-001", quantity=100),
            "SKU-002": _make_record("SKU-002", quantity=50),
        }
        s2 = {
            "SKU-001": _make_record("SKU-001", quantity=110),
            "SKU-003": _make_record("SKU-003", quantity=30),
        }
        result = reconcile(s1, s2)
        assert len(result["matched"]) == 1
        assert len(result["added"]) == 1
        assert len(result["removed"]) == 1
        assert result["matched"][0]["sku"] == "SKU-001"
        assert result["added"][0]["sku"] == "SKU-003"
        assert result["removed"][0]["sku"] == "SKU-002"

    def test_empty_snapshots(self):
        result = reconcile({}, {})
        assert result == {"matched": [], "added": [], "removed": []}

    def test_results_sorted_by_sku(self):
        s1 = {
            "SKU-003": _make_record("SKU-003"),
            "SKU-001": _make_record("SKU-001"),
        }
        s2 = {
            "SKU-003": _make_record("SKU-003"),
            "SKU-001": _make_record("SKU-001"),
        }
        result = reconcile(s1, s2)
        skus = [m["sku"] for m in result["matched"]]
        assert skus == ["SKU-001", "SKU-003"]
