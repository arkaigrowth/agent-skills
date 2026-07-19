#!/usr/bin/env python3
"""
signal_shadow: Input preparation helper for the signal-shadow Claude skill.

Fetches source text from one of several input modes and prepends the [META]
block expected by the signal_shadow pattern. Output goes to stdout; the
skill's caller (Claude) applies the system prompt (references/system.md)
to this output.

Usage:
  signal_shadow.py --url <url>                           # Fetch URL (raw HTML)
  signal_shadow.py --file <path>                         # Read local file
  signal_shadow.py                                       # Read stdin (paste/pipe)
  signal_shadow.py --density 3 --source-type academic    # Tune per invocation

  signal_shadow.py --arkai-id <content_id>               # OPTIONAL, EXTERNAL:
      Shells out to a separate `arkai` transcript CLI that is NOT part of this
      skill and is NOT bundled in this repo. This mode only works if an
      `arkai` binary happens to be on your PATH; otherwise it exits with an
      error. The skill is fully usable without it. Prefer --url, --file, or
      piped/pasted text.

Exit codes:
  0 = success
  1 = fetch failure (external CLI / url / file)
  2 = bad arguments
"""

import argparse
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Tuple


VALID_SOURCE_TYPES = ["academic", "transcript", "news", "thread", "technical", "general"]


def fetch_arkai(content_id: str) -> Tuple[str, str]:
    """Fetch a transcript via an OPTIONAL, EXTERNAL `arkai` CLI.

    This CLI is not part of this skill and is not included in this repo. If it
    is not on PATH, this exits with an error. Returns (text, title).
    """
    try:
        result = subprocess.run(
            ["arkai", "show", content_id, "--full"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        sys.stderr.write(
            "error: external `arkai` CLI not found on PATH. This mode is "
            "optional and not bundled with the skill. Use --url, --file, or "
            "piped/pasted text instead.\n"
        )
        sys.exit(1)
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"error: arkai show {content_id} timed out after 30s\n")
        sys.exit(1)

    if result.returncode != 0:
        sys.stderr.write(f"arkai error (exit {result.returncode}):\n{result.stderr}\n")
        sys.exit(1)

    text = result.stdout
    # Best-effort title: first non-empty line, capped
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = (lines[0] if lines else f"arkai:{content_id}")[:120]
    return text, title


def fetch_url(url: str) -> Tuple[str, str]:
    """Fetch URL (raw HTML, no extraction). Returns (text, title)."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "signal-shadow/1.0 (+https://github.com/arkaigrowth)"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        sys.stderr.write(f"error: URL fetch failed: {e}\n")
        sys.exit(1)

    # Best-effort title from <title> tag
    title = url
    lower = raw.lower()
    lo = lower.find("<title>")
    if lo != -1:
        hi = lower.find("</title>", lo)
        if hi != -1:
            title = raw[lo + 7:hi].strip()[:120]
    return raw, title


def read_file(path: str) -> Tuple[str, str]:
    """Read local file. Returns (text, title)."""
    p = Path(path).expanduser().resolve()
    if not p.exists():
        sys.stderr.write(f"error: file not found: {p}\n")
        sys.exit(1)
    text = p.read_text(encoding="utf-8", errors="replace")
    return text, p.stem[:120]


def read_stdin() -> Tuple[str, str]:
    return sys.stdin.read(), "stdin"


def build_meta_block(source_type: str, density: int, title: str) -> str:
    return (
        "[META]\n"
        f"Source type: {source_type}\n"
        f"Density: {density}\n"
        f"Title: {title}\n"
        "[/META]\n\n"
    )


def infer_default_source_type(mode: str, url: str = "") -> str:
    if mode == "arkai":
        return "transcript"
    if mode == "url":
        u = url.lower()
        if "arxiv.org" in u or "scholar.google" in u or "aclanthology" in u:
            return "academic"
        if "twitter.com" in u or "x.com" in u or "linkedin.com" in u or "threads.net" in u:
            return "thread"
        return "news"
    if mode == "file":
        return "general"
    return "general"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Prepare input for the signal_shadow pattern.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    src = ap.add_mutually_exclusive_group()
    src.add_argument(
        "--arkai-id",
        help="OPTIONAL, EXTERNAL: content_id for a separate `arkai` transcript "
        "CLI that is not bundled with this skill",
    )
    src.add_argument("--url", help="URL to fetch (raw HTML, no article extraction)")
    src.add_argument("--file", help="local file path")

    ap.add_argument(
        "--source-type",
        choices=VALID_SOURCE_TYPES,
        default=None,
        help="override source type (default: auto-infer from source)",
    )
    ap.add_argument(
        "--density",
        type=int,
        choices=[1, 2, 3, 4],
        default=2,
        help="density dial (default: 2)",
    )
    ap.add_argument("--title", default=None, help="override inferred title")
    return ap


def main(argv=None) -> None:
    ap = build_parser()
    args = ap.parse_args(argv)

    # Fetch based on input mode
    if args.arkai_id:
        text, inferred_title = fetch_arkai(args.arkai_id)
        mode = "arkai"
        url_for_inference = ""
    elif args.url:
        text, inferred_title = fetch_url(args.url)
        mode = "url"
        url_for_inference = args.url
    elif args.file:
        text, inferred_title = read_file(args.file)
        mode = "file"
        url_for_inference = ""
    else:
        text, inferred_title = read_stdin()
        mode = "stdin"
        url_for_inference = ""

    source_type = args.source_type or infer_default_source_type(mode, url_for_inference)
    title = args.title or inferred_title

    # Emit prepared input: META block + source text
    sys.stdout.write(build_meta_block(source_type, args.density, title))
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
