"""Test the validate-then-fix retry loop in scripts/compress.py.

The LLM is treated as an untrusted step: its first output is allowed to be
wrong. This test replaces the model call with a deterministic stub (no network,
no API key) that returns a broken compression first, then a corrected one, and
asserts that the deterministic validator drives the retry to a valid result.
"""
import pathlib

import pytest

import scripts.compress as compress_mod
from scripts.validate import validate

SOURCE = """# Notes

See the guide at https://example.com/guide for details.
"""

# First model output drops the URL -> validator rejects it.
BAD_OUTPUT = """# Notes

See guide for details.
"""

# Second model output restores the URL -> validator accepts it.
GOOD_OUTPUT = """# Notes

See guide at https://example.com/guide for info.
"""


def test_retry_recovers_from_bad_first_output(tmp_path, monkeypatch):
    target = tmp_path / "notes.md"
    target.write_text(SOURCE)

    calls = []

    def fake_call_claude(prompt):
        calls.append(prompt)
        return BAD_OUTPUT if len(calls) == 1 else GOOD_OUTPUT

    monkeypatch.setattr(compress_mod, "call_claude", fake_call_claude)

    ok = compress_mod.compress_file(target)

    assert ok is True
    # One compress call plus one fix call.
    assert len(calls) == 2
    # Backup holds the untouched original.
    backup = target.with_name("notes.original.md")
    assert backup.read_text() == SOURCE
    # Final file is the corrected output and passes validation.
    assert target.read_text() == GOOD_OUTPUT
    assert validate(backup, target).is_valid is True


def test_retry_restores_original_when_fix_never_succeeds(tmp_path, monkeypatch):
    target = tmp_path / "notes.md"
    target.write_text(SOURCE)

    def always_bad(prompt):
        return BAD_OUTPUT

    monkeypatch.setattr(compress_mod, "call_claude", always_bad)

    ok = compress_mod.compress_file(target)

    assert ok is False
    # On give-up, the original content is restored and the backup removed.
    assert target.read_text() == SOURCE
    assert not target.with_name("notes.original.md").exists()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
