# caveman-commands

Terse-output slash commands for Claude Code. Tell the assistant to drop the filler and keep the substance, so answers read like a smart caveman: short, exact, no throat-clearing.

## Attribution

These prompts are adapted from Julius Brussee's
[caveman](https://github.com/JuliusBrussee/caveman) project (MIT licensed at
the time, April 2026): upstream's `caveman` skill and its `caveman-commit` and
`caveman-review` commands. The wording and the intensity-level design are
upstream's. This folder repackages them as `.md` slash commands in the
`~/.claude/commands/` layout and replaces em dashes and arrow glyphs with plain
punctuation. Upstream's MIT notice is kept in [LICENSE-UPSTREAM](LICENSE-UPSTREAM).
Upstream has since relicensed to Apache-2.0 from 3.0.0 and ships its own
installer; use that for the maintained version.

## What this is

Three Claude Code custom slash commands, defined entirely as prompt instructions:

- `/caveman` sets a terse response style for the rest of the session (chat answers, explanations).
- `/caveman:commit` generates a Conventional Commits message with no fluff.
- `/caveman:review` writes one-line-per-finding code review comments.

These are prompt-design artifacts, not deterministic tools. A slash command in Claude Code is a Markdown file whose contents get prepended to the model's instructions. There is no parser, no linter, and no scoring step here. The files below shape how the model writes; the model still decides what to output, and results vary run to run. Treat the "intensity levels" as steering, not guarantees.

## Why

Default assistant output pads answers with pleasantries, articles, and hedging. For an experienced user that padding is pure token and reading overhead. These commands strip it while explicitly preserving code blocks, exact error text, technical terms, and numbers.

## Install

Claude Code discovers custom commands under `~/.claude/commands/`. Copy the files there, preserving the folder layout:

```
~/.claude/commands/
  caveman.md            ->  /caveman
  caveman/commit.md     ->  /caveman:commit
  caveman/review.md     ->  /caveman:review
```

From this repo:

```sh
mkdir -p ~/.claude/commands/caveman
cp caveman.md ~/.claude/commands/caveman.md
cp caveman/commit.md ~/.claude/commands/caveman/commit.md
cp caveman/review.md ~/.claude/commands/caveman/review.md
```

Restart or reload Claude Code so it picks up the new commands, then type `/caveman` to confirm they appear.

## Usage

```
/caveman              switch on terse mode (default intensity: full)
/caveman lite         gentler: no filler, keep articles and full sentences
/caveman ultra        heavier: abbreviations, arrows for causality
/caveman:commit       draft a commit message for the staged diff
/caveman:review       draft review comments for the current diff
```

Say "stop caveman" or "normal mode" to revert. The chosen level persists until you change it or the session ends.

## Modes and intensity

`/caveman` has an intensity dial. Higher levels compress harder:

| Level | What changes |
|-------|--------------|
| lite | No filler or hedging. Keeps articles and full sentences. |
| full | Drops articles, allows fragments, uses short synonyms. Default. |
| ultra | Abbreviations (DB, auth, config), arrows for causality, one word where one word does. |
| wenyan-* | Experimental classical-Chinese registers (lite/full/ultra) for maximum character reduction. |

The command file also carries an Auto-Clarity rule: it tells the model to drop terse mode for security warnings, destructive-action confirmations, and multi-step sequences where clipped fragments could be misread, then resume afterward. Whether the model actually honors that on a given turn is up to the model.

## Before / after

These pairs are taken from the command definitions themselves. They show the intended transformation, not a benchmark.

General answer, question "Why does my React component re-render?"

- Before (default assistant): "Sure! Your component is re-rendering because you're creating a new object reference on each render, which React sees as a changed prop..."
- After (full): "New object ref each render. Inline object prop = new ref = re-render. Wrap in `useMemo`."
- After (ultra): "Inline obj prop -> new ref -> re-render. `useMemo`."

Commit message, diff adds a profile endpoint

- Before: "feat: add a new endpoint to get user profile information from the database"
- After:
  ```
  feat(api): add GET /users/:id/profile

  Mobile client needs profile data without the full user payload
  to reduce LTE bandwidth on cold-launch screens.

  Closes #128
  ```

Code review, missing null check

- Before: "I noticed that on line 42 you're not checking if the user object is null before accessing the email property. This could potentially cause a crash..."
- After: `L42: 🔴 bug: user can be null after .find(). Add guard before .email.`

## Limitations

- Prompt steering, not enforcement. The model can and sometimes will ignore the style, especially on long or complex answers. There is no post-processing that guarantees terseness.
- No metrics. This repo makes no claim about token savings; actual reduction depends on the question, the model, and the intensity level. Measure it yourself if you need a number.
- Claude Code specific. The install path and slash-command mechanism are particular to Claude Code. The Markdown instructions could be adapted for other assistants, but they are not tested there.
- The `wenyan-*` classical-Chinese levels are experimental and were exercised far less than the English levels.
- `/caveman:commit` and `/caveman:review` only draft text. They do not stage, commit, approve, or run any tooling. You paste the output yourself.

## License

MIT. Upstream's notice is in [LICENSE-UPSTREAM](LICENSE-UPSTREAM) (Copyright (c) 2026 Julius Brussee).
