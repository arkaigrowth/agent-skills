"""Tests for the deterministic validator (scripts/validate.py).

The validator is the trust boundary around the LLM step. These tests pin down
what it treats as a hard error (URL loss, code-block edits, heading-count
changes) versus what it merely warns about (path or bullet drift).
"""
import pathlib

import pytest

from scripts.validate import validate

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def _pair(stem):
    original = FIXTURES / f"{stem}.original.md"
    compressed = FIXTURES / f"{stem}.md"
    assert original.exists(), f"missing fixture: {original}"
    assert compressed.exists(), f"missing fixture: {compressed}"
    return original, compressed


def test_valid_compression_passes():
    """Prose is compressed but headings, URLs, and code blocks are intact."""
    original, compressed = _pair("valid_preserved")
    result = validate(original, compressed)
    assert result.is_valid is True
    assert result.errors == []


def test_dropped_url_is_error():
    """A compression that loses a URL must fail validation."""
    original, compressed = _pair("dropped_url")
    result = validate(original, compressed)
    assert result.is_valid is False
    assert any("URL" in e for e in result.errors)


def test_broken_code_and_missing_heading_are_errors():
    """Editing a fenced code block and dropping a heading both fail."""
    original, compressed = _pair("broken_code_and_heading")
    result = validate(original, compressed)
    assert result.is_valid is False
    assert any("Code blocks" in e for e in result.errors)
    assert any("Heading count" in e for e in result.errors)


def test_identical_text_is_trivially_valid(tmp_path):
    """A no-op compression preserves everything by construction."""
    src = FIXTURES / "valid_preserved.original.md"
    text = src.read_text()
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text(text)
    b.write_text(text)
    result = validate(a, b)
    assert result.is_valid is True
    assert result.errors == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
