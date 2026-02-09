# Tests for causely_notification.date
import unittest

from causely_notification.date import parse_iso_date


class TestParseIsoDate(unittest.TestCase):
    def test_parse_valid_iso_date(self):
        result = parse_iso_date("2025-08-07T18:51:54.164185287Z")
        self.assertIn("2025", result)
        self.assertIn("August", result)

    def test_parse_invalid_iso_date_returns_original_string(self):
        """Invalid or non-ISO string is returned as-is (exception path)."""
        invalid = "not-a-date"
        self.assertEqual(parse_iso_date(invalid), invalid)
        self.assertEqual(parse_iso_date(""), "")
