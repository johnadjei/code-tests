"""Tests for column mapping."""

from reconcile import apply_column_mapping


class TestApplyColumnMapping:
    def test_snapshot_1_mapping(self):
        row = {
            "sku": "SKU-001",
            "name": "Widget A",
            "quantity": "100",
            "location": "Warehouse A",
            "last_counted": "2024-01-08",
        }
        mapping = {
            "sku": "sku",
            "name": "name",
            "quantity": "quantity",
            "location": "location",
            "last_counted": "date",
        }
        result = apply_column_mapping(row, mapping)
        assert result == {
            "sku": "SKU-001",
            "name": "Widget A",
            "quantity": "100",
            "location": "Warehouse A",
            "date": "2024-01-08",
        }

    def test_snapshot_2_mapping(self):
        row = {
            "sku": "SKU-001",
            "product_name": "Widget A",
            "qty": "110",
            "warehouse": "Warehouse A",
            "updated_at": "2024-01-15",
        }
        mapping = {
            "sku": "sku",
            "product_name": "name",
            "qty": "quantity",
            "warehouse": "location",
            "updated_at": "date",
        }
        result = apply_column_mapping(row, mapping)
        assert result == {
            "sku": "SKU-001",
            "name": "Widget A",
            "quantity": "110",
            "location": "Warehouse A",
            "date": "2024-01-15",
        }

    def test_missing_source_column_skipped(self):
        row = {"sku": "SKU-001", "name": "Widget A"}
        mapping = {
            "sku": "sku",
            "name": "name",
            "quantity": "quantity",
        }
        result = apply_column_mapping(row, mapping)
        assert result == {"sku": "SKU-001", "name": "Widget A"}

    def test_extra_source_columns_ignored(self):
        row = {"sku": "SKU-001", "name": "Widget A", "color": "red"}
        mapping = {"sku": "sku", "name": "name"}
        result = apply_column_mapping(row, mapping)
        assert result == {"sku": "SKU-001", "name": "Widget A"}
