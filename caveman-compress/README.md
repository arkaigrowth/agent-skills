# caveman-compress

Shrink natural-language memory files (CLAUDE.md, todo lists, preference notes)
into terse "caveman" phrasing so they cost fewer input tokens, while a
deterministic validator guarantees the load-bearing parts (code blocks, URLs,
file paths, headings) survive the rewrite untouched.

This is a Claude Code skill. It pairs an LLM rewrite step with a plain-Python
checker that treats the model's output as untrusted until it passes.

## Attribution

This skill is adapted from Julius Brussee's
[caveman](https://github.com/JuliusBrussee/caveman) project (the
`caveman-compress/` skill as of upstream commit `7d6aa3a`, April 2026, MIT
licensed at the time). The compression prompt, the natural-language detector,
the regex validator, and the fix-loop design are upstream's work. Upstream's MIT
notice is kept in [LICENSE-UPSTREAM](LICENSE-UPSTREAM).

What changed in this copy:

- renamed the skill from `compress` to `caveman-compress`
- removed em dashes and emoji from prompt and console text
- added `tests/` (pytest, golden fixtures for a clean pass, a dropped URL, and a
  broken code block plus heading), `conftest.py`, and `requirements.txt`
- wrote this README to explain the design

Upstream has since grown into a much larger project and relicensed to
Apache-2.0 from 3.0.0. This copy stays on the MIT snapshot it was taken from.
For the maintained version, install from the upstream repo.

## Why this exists

Long memory files get re-read on every turn, so their prose is a recurring
token cost. A model can compress that prose, but a naive "please shorten this"
prompt will happily paraphrase a shell command, drop a URL, or reword a heading
you were relying on. The interesting part of this skill is not the compression
prompt. It is the checker that refuses to accept a compression that damaged
something it should not have.

## Design: deterministic validator, LLM as an untrusted step

The pipeline is:

1. `detect.py` decides (no model call) whether the file is natural language at
   all. Code and config files are skipped.
2. `compress.py` sends the prose to the model with strict "do not touch code,
   URLs, headings" instructions and writes the result, keeping the untouched
   original as `<name>.original.md`.
3. `validate.py` compares original and compressed with regexes only, no model
   in the loop. It extracts and diffs headings, fenced code blocks, URLs,
   paths, and bullet counts.
4. If validation reports errors, `compress.py` sends a narrow fix prompt (the
   specific errors plus the original as reference, with an instruction not to
   recompress) and re-validates. It retries up to twice.
5. If it still fails, the original file is restored and the backup removed, so a
   bad run cannot silently corrupt your memory file.

The framing that makes this robust: the LLM is the one part of the system whose
output you cannot trust, so it is never the last word. A deterministic checker
that never calls a model is the gate. The model is allowed to be wrong on the
first try; the checker is what turns "usually preserves your code blocks" into
"the write only lands if the code blocks are byte-for-byte identical."

What the validator enforces as hard errors (a failing run):

- Heading count changed.
- Any fenced code block is not preserved exactly.
- The set of URLs changed (one lost or invented).

What it treats as warnings only (does not fail the run):

- File-path set drift (path detection is heuristic and false-positive prone).
- Bullet count drift beyond a threshold.

This split is deliberate: the checks that are exact (code fences, URL strings,
heading counts) block the write; the checks that are fuzzy (path regexes) only
warn, so the validator does not reject good compressions over a detection quirk.

## Install

Copy this directory into your Claude Code skills folder, for example:

```bash
cp -r caveman-compress ~/.claude/skills/caveman-compress
```

`SKILL.md` carries the frontmatter Claude Code needs to register the skill. The
compression and fix prompts assume Claude, either through the `anthropic` SDK or
the `claude` CLI (see Dependencies).

## Usage

As a skill inside Claude Code:

```
/caveman:compress <absolute-filepath>
```

Or run the package directly:

```bash
cd caveman-compress
python3 -m scripts <absolute-filepath>
```

The original is backed up to `<name>.original.md` before anything is
overwritten. If that backup already exists, the run aborts rather than risk
clobbering it.

### Validate or benchmark a pair by hand

The validator and benchmark are usable on their own, without the model step:

```bash
# Pass/fail check on an original/compressed pair
python3 scripts/validate.py original.md compressed.md

# Token delta for a pair (uses tiktoken if available, else word count)
python3 scripts/benchmark.py original.md compressed.md
```

## Dependencies

Core detection and validation use only the Python standard library. The two
model-facing extras are optional (soft) dependencies; see `requirements.txt`.

- `anthropic` (optional): used by `compress.py` when `ANTHROPIC_API_KEY` is set.
  If it is not installed, the code falls back to shelling out to the `claude`
  CLI, which handles desktop auth.
- `tiktoken` (optional): used by `benchmark.py` for exact token counts. If it is
  not installed, the benchmark falls back to a whitespace word count.
- `pytest` (dev only): to run the test suite.

## Tests

```bash
cd caveman-compress
python3 -m pytest tests/ -v
```

The suite is offline. It exercises the validator against fixture pairs (a valid
compression, a dropped URL, a broken code block plus a dropped heading) and
drives the compress-validate-fix retry loop with a stubbed model call, so no API
key or network is required. Result at time of writing: 6 passed.

## Limitations

- Compression quality depends on the model; the validator guarantees
  preservation of code, URLs, and heading counts, not that the prose reads well.
- Token savings vary with the input and are not a fixed figure. The included
  benchmark reports the delta for a given pair rather than a headline number.
- Path preservation is a warning, not a guarantee. The path regex is heuristic
  and can miss or over-match, which is exactly why it does not fail a run.
- `detect.py` classification for extensionless files is heuristic and can
  misjudge unusual files.
- The skill is designed for and tested on macOS with Python 3.11. Other setups
  are untested.
- Compression is lossy on prose by design. Keep the `.original.md` backup if the
  exact wording ever matters.

## License

MIT. Upstream's notice is in [LICENSE-UPSTREAM](LICENSE-UPSTREAM) (Copyright (c) 2026 Julius Brussee); the additions listed above are under the repository root `LICENSE`.
