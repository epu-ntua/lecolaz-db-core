"""Raw HAM protocol fixtures: ordered columns, transforms, missing and bad data."""

import unittest
from unittest.mock import patch

from infra.dagster.ham.catalog import load_catalog
from infra.dagster.ham.datalog import parse_datalog, transform_reading, validate_datalog


class DatalogTests(unittest.TestCase):
    def test_raw_validation_requires_data_without_applying_transforms(self):
        payload = b"\xef\xbb\xbf1767225600;;4500;;\r\n1767225660;2150;;;\r\n"
        with patch("infra.dagster.ham.datalog.transform_reading", side_effect=AssertionError("Conversion is downstream")):
            self.assertEqual(validate_datalog(payload, "e45:1"), 2)
        for payload in (b"", b" \n", b"\xef\xbb\xbf", b"1767225600;;2147483648;;\n"):
            with self.subTest(payload=payload), self.assertRaisesRegex(ValueError, "no measurements"):
                validate_datalog(payload, "e45:1")

    def test_raw_validation_checks_all_rows_and_rejects_invalid_timestamps(self):
        first = b"1767225600;2150;4500;2500;0\n"
        for last in (b"1e30;2150;4500;2500;0", b"nan;2150;4500;2500;0", b"1767225601;2150", b'"unterminated'):
            with self.subTest(last=last), self.assertRaisesRegex(ValueError, "line 2"):
                validate_datalog(first + last, "e45:1")

    def test_real_thermal_model_order_and_no_synthetic_samples(self):
        with patch("hamapi.hamapi", side_effect=AssertionError("SDK parser")):
            result = parse_datalog(
                b"1767225600;2150;4567;2500;123\r\n1767225660.125;-550;5000;1900;0\r\n",
                "e45:1",
            )
        self.assertEqual(result, {
            "timestamp": [1767225600, 1767225660.125],
            "T": [21.5, -5.5], "H": [45.67, 50], "TG": [25, 19], "WINDM": [1.23, 0],
        })

    def test_missing_fields_remain_aligned_and_are_not_forward_filled(self):
        result = parse_datalog(
            b"1767225600;;2147483648;2500;\n1767225660;2150;4500;;2147483648\n",
            "e45:1",
        )
        self.assertEqual(result["T"], [None, 21.5])
        self.assertEqual(result["H"], [None, 45])
        self.assertEqual(result["TG"], [25, None])
        self.assertEqual(result["WINDM"], [None, None])
        self.assertEqual({len(series) for series in result.values()}, {2})

    def test_output_columns_are_not_readings_and_can_be_text(self):
        result = parse_datalog(b"1767225600;2150;4500;1;command\n", "e20:1")
        self.assertEqual(set(result), {"timestamp", "T", "H", "IRR"})
        self.assertEqual(result["IRR"], [1])

    def test_empty_and_bom_payloads(self):
        for payload in (b"", b"\n\r\n", b"\xef\xbb\xbf"):
            self.assertEqual(parse_datalog(payload, "e45:1")["timestamp"], [])

    def test_previously_stored_missing_file_is_not_an_empty_datalog(self):
        for payload in (b'{"messages":["File not found"]}', b' { "messages": ["File not found"] }\n'):
            with self.assertRaisesRegex(ValueError, "file not found"):
                parse_datalog(payload, "e45:1")

    def test_malformed_payloads_fail_with_line_number(self):
        for line in (
            b"1767225660;2150", b"1767225660;2150;4500;2500;0;extra",
            b"bad;2150;4500;2500;0", b"nan;2150;4500;2500;0",
            b"1767225660;inf;4500;2500;0", b"1767225660;last;4500;2500;0",
            b'{"error":"denied"}', b"<html>failure</html>",
        ):
            with self.subTest(line=line), self.assertRaisesRegex(ValueError, "line 2"):
                parse_datalog(b"1767225600;2150;4500;2500;0\n" + line, "e45:1")
        with self.assertRaises(UnicodeDecodeError):
            parse_datalog(b"\xff", "e45:1")

    def test_unknown_model_missing_catalog_and_transform_fail(self):
        with self.assertRaisesRegex(ValueError, "Unknown HAM sensor model"):
            parse_datalog(b"", "unknown:1")
        with self.assertRaisesRegex(ValueError, "Missing reading catalog"):
            parse_datalog(b"", "e45:1", readings={})
        with self.assertRaisesRegex(ValueError, "Unsupported HAM reading transform"):
            parse_datalog(b"", "test:1", models={"test": {"readings": ["T"]}}, readings={"T": {"transform": "new_transform"}})

    def test_transform_units_and_clamps(self):
        cases = [
            (2150, "divide_by_100", 21.5), (-1, "absolute", -1),
            (3600000, "ws_to_kwh", 1), (37500000, "geocoordinates_translation", 37.5),
            (150000, "divide_by_1000_max_100", 100), (-1, "divide_by_100_max_100", 0),
            (2000, "divide_by_1000_max_1", 1), (12.9, "only_positive", 12),
            (-12, "only_positive", 0), (255, "binary_translation", 1),
            (-1, "binary_translation", 0), (0.1234, "percent_translation", 12.3),
            (1.2, "transform", 1.2), (3, None, 3),
        ]
        for value, transform, expected in cases:
            with self.subTest(transform=transform):
                self.assertEqual(transform_reading(value, transform), expected)

    def test_all_bundled_models_have_supported_reading_transforms(self):
        for model in load_catalog("models"):
            with self.subTest(model=model):
                result = parse_datalog(b"", f"{model}:1")
                self.assertEqual(result["timestamp"], [])
