"""Configuration for inventory reconciliation."""

# Column mapping: source column names → canonical names
# Each snapshot may use different column names. Map them here.
COLUMN_MAPPINGS = {
    "snapshot_1": {
        "sku": "sku",
        "name": "name",
        "quantity": "quantity",
        "location": "location",
        "last_counted": "date",
    },
    "snapshot_2": {
        "sku": "sku",
        "product_name": "name",
        "qty": "quantity",
        "warehouse": "location",
        "updated_at": "date",
    },
}

# SKU normalization: uppercase, ensure hyphen after "SKU" prefix
# e.g. "sku005" → "SKU-005", "sku-008" → "SKU-008"
SKU_PREFIX = "SKU"
SKU_SEPARATOR = "-"

# Default file paths (relative to script location)
DEFAULT_SNAPSHOT_1 = "data/snapshot_1.csv"
DEFAULT_SNAPSHOT_2 = "data/snapshot_2.csv"
DEFAULT_OUTPUT_DIR = "output"

# Date format: normalize everything to ISO 8601
DATE_FORMAT_ISO = "%Y-%m-%d"
DATE_FORMATS_ACCEPTED = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
]
