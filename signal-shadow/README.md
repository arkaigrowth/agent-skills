# signal-shadow

A Claude Code skill that compresses long text without sanding off the caveats, disagreement, chronology, dependencies, and uncertainty that change how a careful reader should interpret it.

Most summaries keep the center of mass and quietly drop the details that carry the risk. This skill keeps those details, labels every anchor as quoted, paraphrased, or inferred, and closes with a residual-risk audit that names its own weakest points instead of printing a checkmark.

## What it is

Two parts:

1. A prompt pattern (`references/system.md`) that a model applies as a system prompt. It defines the summarization rubric and a strict output envelope.
2. A small Python helper (`scripts/signal_shadow.py`, standard library only) that fetches source text from a URL, a file, or stdin, and prepends a `[META]` header the pattern reads for source type and density.

There is also an optional mode that shells out to a separate transcript CLI. That CLI is not part of this repo. See "Optional external mode" below.

## Why

Summaries are lossy on purpose, but the wrong losses are dangerous. Dropping a "two members abstained" or a "results are not conclusive yet" turns a hedged source into false confidence. signal-shadow treats decision-relevance as the inclusion gate: if omitting something would change a reader's interpretation or action, it stays.

## Install

This is a Claude Code skill. Copy the folder into your skills directory:

```
cp -r signal-shadow ~/.claude/skills/signal-shadow
```

Then start (or restart) Claude Code so it picks up the skill. The helper script needs Python 3 and uses only the standard library, so there is nothing to `pip install`.

## Usage

Inside Claude Code, trigger the skill by asking for a nuance-preserving summary, for example:

```
signal-shadow on ./paper.md at density 3
signal-shadow this URL: https://example.com/article
```

Or paste text and ask for a "signal shadow" summary.

Under the hood the skill prepares input with the helper:

```
python3 scripts/signal_shadow.py --file paper.md --source-type academic --density 3
python3 scripts/signal_shadow.py --url https://example.com/article
cat notes.md | python3 scripts/signal_shadow.py
```

The helper writes the `[META]` header plus the source text to stdout. The model then applies `references/system.md` to that output.

### Density dial

`--density` ranges 1 to 4 (default 2). It caps how many core signals the summary carries; it does not force that many. Output scales to the source and does not pad.

## Example (before and after)

The output below is illustrative. It shows the envelope produced by applying `references/system.md` to the source, at density 2, source type transcript.

### Before (source)

```
Alice (PM): We're greenlighting the mobile redesign for Q3. Budget is approved.
Bob (Eng): I'm on board, but the timeline only works if the auth rewrite lands
  first. If that slips, the whole schedule slips.
Alice: Understood. Legal still hasn't signed off on the new data-sharing copy,
  so treat the launch date as tentative.
Jane (Design): One concern nobody has raised: we ran the usability test with 6
  people, all internal. I would not call the results conclusive yet.
Bob: Fair. Last quarter we assumed the API could handle the load and it could
  not, so I would want a load test before we commit.
```

### After (signal-shadow output)

```markdown
# Signal + Shadow: Mobile redesign greenlight meeting

**Source type:** transcript
**Density:** 2
**Summary meta:** 4 core signals, 1 open question

## Core Signal

- **The Q3 mobile redesign is approved, but the schedule is conditional, not fixed.**
  - Why it matters: treating Q3 as a committed date overstates certainty the meeting did not grant.
  - Easy to miss: approval of budget is not approval of timeline; two separate blockers remain.
  - Anchor: "Budget is approved." *(quoted)* paired with "treat the launch date as tentative." *(quoted)*
  - Confidence: high, both statements are explicit in the source.

- **The timeline depends on the auth rewrite landing first.**
  - Why it matters: this is a hard prerequisite; a slip here cascades to the whole schedule.
  - Easy to miss: it is stated as a conditional, not a risk to monitor. "If that slips, the whole schedule slips."
  - Anchor: "the timeline only works if the auth rewrite lands first" *(quoted)*
  - Confidence: high, direct quote.

- **Legal sign-off on data-sharing copy is still outstanding.**
  - Why it matters: an external gate the team does not control can move the launch date.
  - Easy to miss: framed in passing, but it is the stated reason the date is tentative.
  - Anchor: "Legal still hasn't signed off on the new data-sharing copy" *(quoted)*
  - Confidence: high, direct quote.

- **The usability evidence is weak and the team knows it.**
  - Why it matters: 6 internal testers is not a basis for confident design decisions.
  - Easy to miss: raised late, by one person, and flagged as inconclusive rather than settled.
  - Anchor: "we ran the usability test with 6 people, all internal ... I would not call the results conclusive yet" *(quoted)*
  - Confidence: high, direct quote.

## Blind Spots / Open Questions

- No load test is scheduled yet, and a past load assumption already failed once. Bob asks for one "before we commit," but the source does not show it being agreed to. *(inferred from Bob's request plus the absence of any agreement in the transcript)*

## Self-Audit

- **Largest inference**: that the load test is not yet agreed to. The source shows the request but no response, so this is an inference from silence, not a stated fact.
- **Strongest omission risk**: the auth-rewrite dependency. If a reader drops it, the whole "Q3 is on track" reading becomes wrong.
- **Weakest-confidence claim**: none beyond the labeled inference. Every core signal is a direct quote.
```

Notice what a flat summary would have deleted: the abstentions-style hedging (tentative date, inconclusive test), the hard dependency on the auth rewrite, and the unresolved load-test request. Those are exactly the parts that change what a reader should do next.

## Optional external mode

The helper exposes an `--arkai-id` flag that shells out to a separate `arkai` transcript CLI. That CLI is not part of this skill and is not included in this repo. The mode exits with an error if no `arkai` binary is on your PATH, and the skill is fully usable without it. For transcripts, prefer `--file`, `--url`, or pasting the transcript text directly.

## Tests

```
python3 -m unittest discover -s tests -v
```

The suite (19 tests) covers `build_meta_block`, `infer_default_source_type`, and argument parsing. It does not touch the network or the optional external CLI. All 19 pass on Python 3 (macOS).

## Limitations

- URL mode fetches raw HTML with no readability extraction. Paywalled, JavaScript-rendered, or markup-heavy pages may come through as noise; paste cleaned text for those.
- The pattern is a prompt, not a deterministic function. Output quality depends on the model applying it and on input quality. The example above is illustrative, not a benchmark.
- The optional transcript CLI mode depends on external software that is not included and is not tested here.
- The helper is tested on macOS with Python 3. It uses only the standard library, but other platforms are untested.

## License

See the repository root `LICENSE` (MIT).
