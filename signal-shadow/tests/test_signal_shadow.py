#!/usr/bin/env python3
"""Unit tests for the signal_shadow helper.

Covers the pure helper functions and argument parsing. These tests do not hit
the network and do not invoke the optional external transcript CLI.

Run with:
    python3 -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

# Make the scripts/ directory importable regardless of the working directory.
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import signal_shadow as ss  # noqa: E402


class TestBuildMetaBlock(unittest.TestCase):
    def test_exact_format(self):
        block = ss.build_meta_block("academic", 3, "My Paper")
        expected = (
            "[META]\n"
            "Source type: academic\n"
            "Density: 3\n"
            "Title: My Paper\n"
            "[/META]\n\n"
        )
        self.assertEqual(block, expected)

    def test_opens_and_closes_tags(self):
        block = ss.build_meta_block("general", 2, "x")
        self.assertTrue(block.startswith("[META]\n"))
        self.assertTrue(block.endswith("[/META]\n\n"))

    def test_density_is_stringified(self):
        block = ss.build_meta_block("news", 1, "t")
        self.assertIn("Density: 1\n", block)

    def test_title_passthrough_preserves_spaces(self):
        block = ss.build_meta_block("thread", 4, "a long title here")
        self.assertIn("Title: a long title here\n", block)


class TestInferDefaultSourceType(unittest.TestCase):
    def test_arkai_mode_is_transcript(self):
        self.assertEqual(ss.infer_default_source_type("arkai"), "transcript")

    def test_file_mode_is_general(self):
        self.assertEqual(ss.infer_default_source_type("file"), "general")

    def test_stdin_mode_is_general(self):
        self.assertEqual(ss.infer_default_source_type("stdin"), "general")

    def test_url_academic_domains(self):
        for u in [
            "https://arxiv.org/abs/1234.5678",
            "https://scholar.google.com/x",
            "https://aclanthology.org/paper",
        ]:
            self.assertEqual(ss.infer_default_source_type("url", u), "academic", u)

    def test_url_thread_domains(self):
        for u in [
            "https://twitter.com/user/status/1",
            "https://x.com/user/status/1",
            "https://www.linkedin.com/posts/xyz",
            "https://www.threads.net/@user/post/1",
        ]:
            self.assertEqual(ss.infer_default_source_type("url", u), "thread", u)

    def test_url_default_is_news(self):
        self.assertEqual(
            ss.infer_default_source_type("url", "https://example.com/story"),
            "news",
        )

    def test_url_domain_match_is_case_insensitive(self):
        self.assertEqual(
            ss.infer_default_source_type("url", "https://ARXIV.org/abs/1"),
            "academic",
        )


class TestArgParsing(unittest.TestCase):
    def setUp(self):
        self.parser = ss.build_parser()

    def test_defaults(self):
        args = self.parser.parse_args([])
        self.assertEqual(args.density, 2)
        self.assertIsNone(args.source_type)
        self.assertIsNone(args.url)
        self.assertIsNone(args.file)
        self.assertIsNone(args.arkai_id)
        self.assertIsNone(args.title)

    def test_url_and_density(self):
        args = self.parser.parse_args(["--url", "https://a.com", "--density", "3"])
        self.assertEqual(args.url, "https://a.com")
        self.assertEqual(args.density, 3)

    def test_file_and_source_type(self):
        args = self.parser.parse_args(
            ["--file", "paper.md", "--source-type", "academic"]
        )
        self.assertEqual(args.file, "paper.md")
        self.assertEqual(args.source_type, "academic")

    def test_arkai_id_is_dest_normalized(self):
        args = self.parser.parse_args(["--arkai-id", "abc123"])
        self.assertEqual(args.arkai_id, "abc123")

    def test_mutually_exclusive_sources_rejected(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["--url", "https://a.com", "--file", "p.md"])

    def test_invalid_density_rejected(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["--density", "9"])

    def test_invalid_source_type_rejected(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["--source-type", "bogus"])

    def test_title_override(self):
        args = self.parser.parse_args(["--title", "Custom Title"])
        self.assertEqual(args.title, "Custom Title")


if __name__ == "__main__":
    unittest.main()
