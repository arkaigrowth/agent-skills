"""
Unit tests for pure helper functions in scripts/_deps.py.

These cover the deterministic, side-effect-free utilities:
sanitize_filename, estimate_size, format_duration, and
ProgressTracker.parse_progress. Network, filesystem, and yt-dlp
dependent functions are intentionally out of scope.

Run with either:
    python3 -m unittest discover -s tests
    python3 tests/test_deps.py
"""

import os
import sys
import unittest

# Make scripts/_deps.py importable regardless of the working directory.
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import _deps  # noqa: E402


class TestSanitizeFilename(unittest.TestCase):
    def test_replaces_ascii_and_fullwidth_colon_with_hyphen(self):
        self.assertEqual(_deps.sanitize_filename("a:b：c"), "a-b-c")

    def test_replaces_reserved_characters_with_underscore(self):
        self.assertEqual(
            _deps.sanitize_filename('a<b>"c/d\\e|f?g*h'),
            "a_b__c_d_e_f_g_h",
        )

    def test_truncates_to_max_length_and_strips_trailing_space(self):
        self.assertEqual(_deps.sanitize_filename("ab cd ef", max_length=6), "ab cd")

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(_deps.sanitize_filename("  hello  "), "hello")

    def test_short_name_is_unchanged(self):
        self.assertEqual(_deps.sanitize_filename("normal_name"), "normal_name")


class TestEstimateSize(unittest.TestCase):
    def test_audio_only_uses_audio_bitrate(self):
        # 60s at 0.32 Mbps: 0.32 * 60 / 8 = 2.4 MB.
        result = _deps.estimate_size(60, audio_only=True)
        self.assertEqual(result["bitrate_mbps"], 0.32)
        self.assertEqual(result["size_mb"], 2.4)
        self.assertEqual(result["size_gb"], 0.0)

    def test_hour_of_1080p_is_realistic(self):
        # 3600s at (8.0 + 0.32) Mbps: 8.32 * 3600 / 8 = 3744 MB (~3.66 GB).
        result = _deps.estimate_size(3600, quality="1080p")
        self.assertEqual(result["size_mb"], 3744.0)
        self.assertEqual(result["size_gb"], 3.66)

    def test_video_bitrate_includes_audio_component(self):
        # 1080p video bitrate (8.0) plus audio (0.32).
        result = _deps.estimate_size(0, quality="1080p")
        self.assertEqual(result["bitrate_mbps"], 8.32)
        self.assertEqual(result["size_mb"], 0.0)

    def test_unknown_quality_falls_back_to_default_bitrate(self):
        result = _deps.estimate_size(0, quality="unknown")
        # Falls back to 8.0 default, still plus audio 0.32.
        self.assertEqual(result["bitrate_mbps"], 8.32)

    def test_returns_expected_keys(self):
        result = _deps.estimate_size(10)
        self.assertEqual(set(result.keys()), {"size_mb", "size_gb", "bitrate_mbps"})


class TestFormatDuration(unittest.TestCase):
    def test_seconds_only(self):
        self.assertEqual(_deps.format_duration(45), "45s")

    def test_zero_seconds(self):
        self.assertEqual(_deps.format_duration(0), "0s")

    def test_minutes_and_seconds_zero_padded(self):
        self.assertEqual(_deps.format_duration(90), "1:30")

    def test_exact_minute(self):
        self.assertEqual(_deps.format_duration(120), "2:00")

    def test_hours_minutes_seconds(self):
        self.assertEqual(_deps.format_duration(3661), "1h 1m 1s")

    def test_exact_hour(self):
        self.assertEqual(_deps.format_duration(3600), "1h 0m 0s")


class TestProgressTrackerParseProgress(unittest.TestCase):
    def setUp(self):
        self.tracker = _deps.ProgressTracker()

    def test_parses_decimal_percentage(self):
        self.assertEqual(
            self.tracker.parse_progress("[download]  45.2% of ~1.23GiB at 5.67MiB/s"),
            45.2,
        )

    def test_parses_integer_percentage(self):
        self.assertEqual(self.tracker.parse_progress("[download] 100% of 1.00GiB"), 100.0)

    def test_parses_zero_percentage(self):
        self.assertEqual(self.tracker.parse_progress("[download]   0.0% of 1.00GiB"), 0.0)

    def test_non_progress_line_returns_none(self):
        self.assertIsNone(self.tracker.parse_progress("[info] Writing metadata"))

    def test_empty_line_returns_none(self):
        self.assertIsNone(self.tracker.parse_progress(""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
