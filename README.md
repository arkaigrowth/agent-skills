# agent-skills

Nine Claude Code skills and one command pack I use daily, curated down from a larger private set to the ones worth showing.

The common thread: where a skill's behavior is predictable, it runs as code with a contract (JSON schemas, typed exit codes, golden-case tests), and the model's output gets validated before anything trusts it. Where judgment is genuinely required, the prompt design is the product, and those entries say so plainly.

## The skills

| Skill | What it does | The engineering |
|---|---|---|
| [repo-security-scan](repo-security-scan/) | Quarantine-clones untrusted repos and fans out Trivy, TruffleHog, Semgrep, GuardDog, and Scorecard into one scored verdict. Auto-scans on git clone via hook. | 1,100+ line scanner with tiered verdicts, graceful degradation when tools are missing, JSON output contract, smoke-tested. |
| [caveman-compress](caveman-compress/) | Compresses memory files (CLAUDE.md, todos) into terse prose to cut input tokens. | Treats the LLM as an untrusted step: regex validators prove URLs, code blocks, and headings survived; a targeted fix loop repairs violations without recompressing. |
| [patch-package](patch-package/) | Tracks local dependency hotfixes (patch-package, pnpm/yarn/bun patch) as reviewable, retire-able tech debt. | Registry script with package-manager detection across five ecosystems, 23 passing tests. |
| [signal-shadow](signal-shadow/) | Summarization that keeps the caveats: labeled inference anchors (quoted / paraphrased / inferred) plus a residual-risk self-audit. | Prompt architecture with a tested helper layer for source-type inference and metadata. |
| [cmux-orchestration](cmux-orchestration/) | Guardrails for letting terminal AI agents drive each other: two-phase verified sends, mandatory self-identification, injected-text-is-never-approval. | Safety patterns first, cmux command reference second. Born from running real multi-agent fleets. |
| [keychain-token](keychain-token/) | macOS Keychain conventions for agent-managed credentials: never-echo storage, a naming scheme that tells you what breaks when you rotate. | kc-store/kc-get wrappers with exit-code contract, 8 passing tests. |
| [duckdb-finance-analyst](duckdb-finance-analyst/) | Read-only DuckDB/MotherDuck analysis lanes for financial data with a safe schema-probe CLI. | Probe script with JSON contracts, tested against in-memory fixtures. |
| [video-download](video-download/) | yt-dlp for agents: size estimates before committing, resume-safe subprocess handling, caption-only mode. | 21 passing tests over the pure functions (sanitization, size estimation, progress parsing). |
| [mac-sys-diagnostics](mac-sys-diagnostics/) | Curated macOS troubleshooting playbook, including a stuck-Secure-Input fix most people never find. | Command reference with convenience wrappers; destructive operations are gated behind explicit warnings. |
| [caveman-commands](caveman-commands/) | Slash commands for graduated terse-response modes, terse commits, and one-line reviews. | Prompt design, plainly labeled as such. Sometimes a prompt is the right tool. |

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

## License

MIT. See [LICENSE](LICENSE).
