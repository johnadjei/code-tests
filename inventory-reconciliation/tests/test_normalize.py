"""Tests for SKU normalization, date normalization, and quantity parsing."""

from reconcile import normalize_sku, normalize_date, parse_quantity


class TestNormalizeSku:
    def test_already_normalized(self):
        assert normalize_sku("SKU-001") == "SKU-001"

    def test_missing_hyphen(self):
        assert normalize_sku("SKU005") == "SKU-005"

    def test_lowercase(self):
        assert normalize_sku("sku-008") == "SKU-008"

    def test_lowercase_no_hyphen(self):
        assert normalize_sku("sku005") == "SKU-005"

    def test_underscore_separator(self):
        assert normalize_sku("SKU_010") == "SKU-010"

    def test_whitespace_stripped(self):
        assert normalize_sku("  SKU-001  ") == "SKU-001"


class TestNormalizeDate:
    def test_iso_format_passthrough(self):
        date_str, had_issue = normalize_date("2024-01-08")
        assert date_str == "2024-01-08"
        assert had_issue is False

    def test_us_date_format(self):
        date_str, had_issue = normalize_date("01/15/2024")
        assert date_str == "2024-01-15"
        assert had_issue is False

    def test_unrecognized_format(self):
        date_str, had_issue = normalize_date("Jan 15, 2024")
        assert date_str == "Jan 15, 2024"
        assert had_issue is True

    def test_whitespace_stripped(self):
        date_str, had_issue = normalize_date("  2024-01-08  ")
        assert date_str == "2024-01-08"
        assert had_issue is False


class TestParseQuantity:
    def test_integer(self):
        val, issues = parse_quantity("100")
        assert val == 100
        assert issues == []

    def test_float_flagged(self):
        val, issues = parse_quantity("70.0")
        assert val == 70
        assert any("float" in i for i in issues)

    def test_negative_flagged(self):
        val, issues = parse_quantity("-5")
        assert val == -5
        assert any("negative" in i for i in issues)

    def test_non_numeric(self):
        val, issues = parse_quantity("abc")
        assert val == 0
        assert any("non-numeric" in i for i in issues)

    def test_whitespace_stripped(self):
        val, issues = parse_quantity("  42  ")
        assert val == 42
        assert issues == []
