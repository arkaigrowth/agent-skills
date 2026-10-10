# agent-skills

Eight Claude Code skills I designed and built, plus two entries adapted from Julius Brussee's [caveman](https://github.com/JuliusBrussee/caveman) (MIT), all curated down from a larger private set to the ones I use daily. See [Credits and attribution](#credits-and-attribution) for exactly what is mine and what is adapted.

The common thread: where a skill's behavior is predictable, it runs as code with a contract (JSON schemas, typed exit codes, golden-case tests), and the model's output gets validated before anything trusts it. Where judgment is genuinely required, the prompt design is the product, and those entries say so plainly.

## The skills

| Skill | What it does | The engineering |
|---|---|---|
| [repo-security-scan](repo-security-scan/) | Quarantine-clones untrusted repos and fans out Trivy, TruffleHog, Semgrep, GuardDog, and Scorecard into one scored verdict. Auto-scans on git clone via hook. | 1,100+ line scanner with tiered verdicts, graceful degradation when tools are missing, JSON output contract, smoke-tested. |
| [caveman-compress](caveman-compress/) | Compresses memory files (CLAUDE.md, todos) into terse prose to cut input tokens. **Adapted from [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman).** | Upstream design: the LLM is an untrusted step, regex validators prove URLs, code blocks, and headings survived, and a targeted fix loop repairs violations without recompressing. My additions: a pytest suite with golden fixtures, a dependency note, and a design write-up. |
| [patch-package](patch-package/) | Tracks local dependency hotfixes (patch-package, pnpm/yarn/bun patch) as reviewable, retire-able tech debt. | Registry script with package-manager detection across five ecosystems, 23 passing tests. |
| [signal-shadow](signal-shadow/) | Summarization that keeps the caveats: labeled inference anchors (quoted / paraphrased / inferred) plus a residual-risk self-audit. | Prompt architecture with a tested helper layer for source-type inference and metadata. |
| [cmux-orchestration](cmux-orchestration/) | Guardrails for letting terminal AI agents drive each other: two-phase verified sends, mandatory self-identification, injected-text-is-never-approval. | Safety patterns first, cmux command reference second. Born from running real multi-agent fleets. |
| [keychain-token](keychain-token/) | macOS Keychain conventions for agent-managed credentials: never-echo storage, a naming scheme that tells you what breaks when you rotate. | kc-store/kc-get wrappers with exit-code contract, 8 passing tests. |
| [duckdb-finance-analyst](duckdb-finance-analyst/) | Read-only DuckDB/MotherDuck analysis lanes for financial data with a safe schema-probe CLI. | Probe script with JSON contracts, tested against in-memory fixtures. |
| [video-download](video-download/) | yt-dlp for agents: size estimates before committing, resume-safe subprocess handling, caption-only mode. | 21 passing tests over the pure functions (sanitization, size estimation, progress parsing). |
| [mac-sys-diagnostics](mac-sys-diagnostics/) | Curated macOS troubleshooting playbook, including a stuck-Secure-Input fix most people never find. | Command reference with convenience wrappers; destructive operations are gated behind explicit warnings. |
| [caveman-commands](caveman-commands/) | Slash commands for graduated terse-response modes, terse commits, and one-line reviews. **Adapted from [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman).** | Upstream prompt design repackaged as Claude Code slash commands (`~/.claude/commands/` layout), with light wording edits. Plainly labeled as prompts, not tools. |

## Install

Each folder is a self-contained Claude Code skill. Copy (or symlink) a folder into your skills directory:

```bash
git clone https://github.com/arkaigrowth/agent-skills.git
ln -s "$(pwd)/agent-skills/repo-security-scan" ~/.claude/skills/repo-security-scan
```

Claude Code picks it up on the next session. Each skill's own README covers dependencies and usage; SKILL.md is the machine-facing entry point.

The one exception is [caveman-commands](caveman-commands/), which ships slash commands rather than a skill. It installs into `~/.claude/commands/` instead of `~/.claude/skills/`; its README covers the exact layout.

Most skills also work in Codex via a symlink into `~/.codex/skills/`.

## Why a collection

These evolved in one working environment and share conventions: scripts over prompts where behavior is predictable, tests on anything with a contract, honest limitation notes instead of marketing. Shipping them together keeps that standard visible.

## Credits and attribution

Eight of the ten entries are my own work: repo-security-scan, patch-package, signal-shadow, cmux-orchestration, keychain-token, duckdb-finance-analyst, video-download, and mac-sys-diagnostics. Most were implemented with Claude Code or Codex under my direction; the design, contracts, tests, and the decision about what to ship are mine.

Two entries are adapted from Julius Brussee's [caveman](https://github.com/JuliusBrussee/caveman) project and are not my design:

- **caveman-compress** derives from upstream's `caveman-compress/` skill as it stood in April 2026 (upstream commit `7d6aa3a`, MIT at the time). Upstream wrote the compression prompt, the detector, the validator, and the fix loop. This copy renames the skill to `caveman-compress`, removes em dashes and emoji from the prompt text, and adds `tests/`, `conftest.py`, `requirements.txt`, and a README explaining the design. Upstream has since moved on considerably and relicensed to Apache-2.0 from 3.0.0; this copy stays on the MIT snapshot it was taken from.
- **caveman-commands** repackages upstream's `caveman`, `caveman-commit`, and `caveman-review` prompts as `.md` slash commands for `~/.claude/commands/`. The wording is upstream's apart from em dash and arrow cleanup.

Each of those two folders carries upstream's MIT notice as `LICENSE-UPSTREAM` and an Attribution section in its README. If you want the current, actively maintained version, install it from the upstream repo.

## License

MIT for my own work, see [LICENSE](LICENSE). The two caveman-derived folders remain under Julius Brussee's MIT notice (`LICENSE-UPSTREAM` in each folder).
