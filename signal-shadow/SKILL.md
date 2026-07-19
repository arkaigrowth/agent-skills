---
name: signal-shadow
description: >
  Nuance-preserving summarization. Compresses text while preserving the
  caveats, disagreement, chronology, dependencies, and uncertainty that
  determine how a careful reader should interpret the source. Closes with a
  residual-risk audit (largest inference, strongest omission risk,
  weakest-confidence claim) instead of checkbox rubric theater.

  Use when user says: "signal shadow", "signal+shadow", "nuance-preserving
  summary", "compress without flattening", "summarize this with caveats",
  "what's easy to miss", or when summarizing long-form content where
  meaning-changing nuance matters (academic papers, podcast/video/interview
  transcripts, news articles, social threads, technical docs, meeting
  minutes, long emails).

  Accepts: URL, file path, or piped/pasted text (plus an optional external
  transcript-CLI mode, see below). Adapts emphasis by source type (academic |
  transcript | news | thread | technical | general). Density dial 1-4 controls
  compression aggressiveness; default is 2. Output scales to the source and
  never pads to fill the density.
---

# signal-shadow

Nuance-preserving summarizer. Uses the `signal_shadow` prompt pattern (canonical copy shipped at `references/system.md`).

## When to Use This Skill

**Triggers:**
- Explicit: "signal shadow", "signal+shadow", "nuance-preserving summary"
- Task framing: "summarize and keep the caveats", "compress without flattening", "what's easy to miss", "what's the signal vs the shadow", "give me the nuance"
- Input types: long articles, podcast/video transcripts, academic papers, news, social threads, technical docs, meeting minutes, interview notes, dense emails

**Anti-triggers** (use other tools):
- Simple tl;dr or headline digest, use plain summarization
- Short code summaries, use code-comment tools
- Marketing copy generation, use a copywriting tool

## Invocation Patterns

**URL** (articles, papers, blog posts):
```
signal-shadow this URL: https://example.com/article
signal-shadow --url https://... --source-type news
```

**File**:
```
signal-shadow on ./paper.md at density 3
signal-shadow --file paper.md --source-type academic --density 3
```

**Piped text / paste**:
```
cat notes.md | signal-shadow
(paste text in chat) then: signal-shadow
```

**Transcript CLI (optional, external):** the helper also exposes an
`--arkai-id` mode that shells out to a separate `arkai` transcript CLI. That
CLI is not part of this skill and is not included in this repo. The mode is a
no-op unless an `arkai` binary is on your PATH, and the skill works fully
without it. If you do not have that CLI, ignore this mode and use `--url`,
`--file`, or piped text (paste your transcript in directly).

## Workflow

When invoked, follow these steps:

1. **Parse user intent.** Identify input source (url / file / pasted text, or the optional external transcript CLI), density (default 2), source-type (auto-infer from source; user may override).

2. **Prepare input.** Run the helper script:
   ```
   python3 scripts/signal_shadow.py \
     [--url <url> | --file <path>] \
     [--density N] \
     [--source-type <type>] \
     [--title "<title>"]
   ```
   The script outputs the source text with a `[META]` header prepended. For pasted text, skip the script and manually prepend the META block.

3. **Apply the pattern.** Load `references/system.md` as your system prompt. This is the canonical `signal_shadow` pattern. Apply it to the prepared input from step 2. Follow every rule in `references/system.md`, especially:
   - Decision-relevance gate (include nuance only if omitting would change interpretation)
   - Single-shot, source-only (no outside knowledge; label all inferences)
   - Residual-risk audit (name specifics, not a checkbox "all good")
   - No padding to fill density

4. **Output verbatim.** Your response should be ONLY the `signal_shadow` output envelope. It starts with `# Signal + Shadow: ...` and ends after `## Self-Audit`. No preamble, no commentary.

5. **Follow-ups.** After the initial output, you may break the envelope to answer questions about the summary.

## Source-Type Auto-Inference

| Input signal | Source type |
|---|---|
| external transcript CLI (`--arkai-id`) | `transcript` |
| URL with news/blog domain | `news` |
| URL with arxiv.org / scholar.google | `academic` |
| URL with twitter.com / x.com / linkedin.com | `thread` |
| `.md` / `.txt` file | `general` (ask user if ambiguous) |
| `.py` / `.js` / README files | `technical` |
| Pasted long-form text | `general` (ask user if unclear) |

User's `--source-type` always overrides.

## Density Dial

| Density | Core signals | Use when |
|---|---|---|
| 1 | 2-3 | short source, or max compression wanted |
| 2 (default) | 3-5 | most long-form content |
| 3 | 5-7 | dense academic papers, long transcripts |
| 4 | 7+ | explicitly requested; padding risk |

Output auto-scales to source length. Do not pad to satisfy density. It is a cap, not a quota.

## Output Format

See `references/system.md`, section OUTPUT INSTRUCTIONS, for the exact schema. Short form:

```
# Signal + Shadow: [title]

**Source type:** ...
**Density:** ...
**Summary meta:** ...

## Core Signal
- **[decision-relevant claim]**
  - Why it matters: ...
  - Easy to miss: ...
  - Anchor: ... (quoted | paraphrased | inferred)
  - Confidence: ... , [brief reason]

## Blind Spots / Open Questions
- ...

## Self-Audit
- Largest inference: ...
- Strongest omission risk: ...
- Weakest-confidence claim: ...
```

## Troubleshooting

- **URL returns raw HTML noise:** the helper uses the Python standard library only (no article extraction). If HTML is noisy, ask the user to paste cleaned text or save the page via reader mode first.
- **External transcript CLI not found:** the `--arkai-id` mode requires a separate `arkai` binary on your PATH. It is not bundled here. Use `--url`, `--file`, or piped text instead.
- **Long source, output truncated:** reduce density to 1 or split the source into sections.
- **Self-Audit says "none" three times:** expected on short or low-inference sources. Not automatically a bug. The pattern is designed to honestly report "none" when earned. On a long source (over 1000 words) with no real inferences, double-check that you are applying the rubric and not coasting.
- **Claude does not see this skill:** Claude Code may need to reload skills. Restart the session or run `claude` fresh.

## Limitations

- URL mode fetches raw HTML with no readability extraction, so paywalled, JavaScript-rendered, or markup-heavy pages may come through as noise. Paste cleaned text for those.
- The optional transcript CLI mode depends on external software that is not included and is not tested here.
- The pattern is a prompt, not a deterministic function. Output quality depends on the model applying it and the input quality.
- The helper script is tested on macOS with Python 3. It uses only the standard library, but other platforms are untested.

## Tests

Unit tests for the helper live in `tests/`. Run them with:
```
python3 -m unittest discover -s tests -v
```
They cover `build_meta_block`, `infer_default_source_type`, and argument parsing. They do not hit the network or the external transcript CLI.

## Related

- **Canonical prompt:** shipped in this repo at `references/system.md`.
- **Fabric CLI equivalent:** if you use the Fabric prompt runner, the same pattern text can be run as a Fabric pattern (`system.md`), which skips this skill's helper and calls a model directly. That path requires Fabric configured with your own API key.
