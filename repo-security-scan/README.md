# repo-security-scan

Decide whether a repository is safe to clone, run, or trust before you execute a
single line of its code. This is an installable Claude Code skill that wraps a
tiered shell scanner over a set of open-source security tools and returns a
single verdict plus a machine-readable JSON summary.

## What it does

`repo-security-scan` runs a point-in-time security assessment of a local
directory (or a repo it clones into quarantine first). It layers several
scanners into three tiers, collects their findings, scores the result, and
prints a CLEAN / WARN / CRITICAL verdict with a matching exit code. It also
generates a markdown report and can emit JSON for automation.

## Why

Cloning and running an unknown repo executes other people's install scripts,
build steps, and dependencies on your machine. A fast pre-flight scan catches
the common problems (committed secrets, known-malicious packages, unsafe
`setup.py`/`postinstall` scripts, persistence tricks, vulnerable dependencies)
before you opt in to running any of it.

## How it works

- **Tiered scanning**: Tier 1 is fast surface checks; Tier 2 adds supply-chain
  and static analysis; Tier 3 adds full git-history and license auditing.
- **Graceful degradation**: every external tool is optional. The scanner
  detects what is installed, uses it, and skips the rest. With no tools
  installed it still runs the built-in heuristics and posture checks.
- **Scored verdict**: findings are weighted by severity into a 0-100 score,
  mapped to a verdict and a shell exit code.

## Install

This is a Claude Code skill. Place the `repo-security-scan/` directory in your
Claude Code skills directory (for example `~/.claude/skills/`). The scanner
itself is a standalone bash script and can also be run directly:

```bash
bash scripts/repo-security-scan.sh --tier 1 /path/to/repo
```

Requires `bash` and standard Unix utilities (`find`, `git`, `date`). `python3`
is used by the optional hook and by the test. Install any of the scanners below
to increase coverage.

## Prerequisites

No scanner is strictly required. The table shows what each tool adds and how the
scan degrades when it is absent.

| Tool | Tier | Required? | Adds | If missing |
|------|------|-----------|------|------------|
| bash + find + git | 1 | Yes | Heuristics, posture, quarantine clone | Scanner cannot run |
| jq | 1 | Recommended | Parses tool JSON into counted findings | Tool output is not tallied into findings |
| trivy | 1, 3 | Optional | Vulns, secrets, misconfigs, license audit | Those checks are skipped |
| gitleaks | 1 | Optional | Secret detection in current files | Skipped |
| guarddog | 1 | Optional | Known-malicious package detection | Skipped |
| scorecard | 2 | Optional | OSSF supply-chain health score | Skipped (also needs GITHUB_TOKEN + GitHub remote) |
| syft | 2 | Optional | SBOM generation (paired with grype) | SBOM vuln scan skipped |
| grype | 2 | Optional | Vulnerability scan of the SBOM | SBOM vuln scan skipped |
| semgrep | 2 | Optional | Static analysis (security + secrets rules) | Skipped |
| trufflehog | 2, 3 | Optional | Verified live-credential + git-history scan | Skipped |

## Usage

```bash
# Fast Tier 1 scan of the current directory
bash scripts/repo-security-scan.sh .

# Standard scan of a specific path
bash scripts/repo-security-scan.sh --tier 2 /path/to/repo

# Deep scan including full git history
bash scripts/repo-security-scan.sh --tier 3 /path/to/repo

# Clone an unknown repo into quarantine, scan, promote only if clean
bash scripts/repo-security-scan.sh --quarantine-clone https://github.com/user/repo ~/repo

# JSON output for automation
bash scripts/repo-security-scan.sh --tier 1 --json /path/to/repo
```

### Example

Scanning the bundled known-clean fixture:

```bash
$ bash scripts/repo-security-scan.sh --tier 1 --json --no-report tests/fixtures/clean-sample
{
  "version": "1.0",
  "tier": 1,
  "verdict": "CLEAN",
  "score": 100,
  "summary": { "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0, "errors": 0 },
  "findings": []
}
```

(Output trimmed for readability. The real output includes timestamp, target,
ecosystems, and tool lists.)

## Tiered verdict

The scanner starts every scan at a score of 100 and subtracts per finding:

| Severity | Score impact |
|----------|--------------|
| Critical | -25 |
| High | -10 |
| Medium | -3 |
| Low | -1 |

The score is floored at 0 and mapped to a verdict and exit code:

| Score | Verdict | Exit code | Meaning |
|-------|---------|-----------|---------|
| 80-100 | CLEAN | 0 | No blocking findings. Review any info notes. |
| 50-79 | WARN | 1 | Warnings present. Review before proceeding. |
| 0-49 | CRITICAL | 2 | Do not run install scripts until resolved. |

In the quarantine workflow the verdict decides promotion: CLEAN and WARN are
promoted (WARN with a caution note), CRITICAL stays quarantined for manual
review.

## Hook (optional)

`hooks/repo_security_hook.py` is a PostToolUse hook for Claude Code. Wire it into
your `settings.json` to auto-run a Tier 1 scan after `git clone`, `npm ci`,
project-level `npm install`, or `pip install -r`, and to print a reminder for
single-package installs. It resolves the scanner relative to itself; override
with `REPO_SCAN_SCANNER`.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `REPORT_DIR` | `./reports` | Markdown report output directory |
| `QUARANTINE_DIR` | `~/.quarantine/repos` | Quarantine clone location |
| `REPO_SCAN_TIMEOUT` | `60` | Per-tool timeout in seconds |
| `REPO_SCAN_LIB` | unset | Shell file defining `send_alert` for notifications |
| `GITHUB_TOKEN` | unset | Enables the OSSF Scorecard check |

## Testing

```bash
bash tests/smoke_test.sh
```

The smoke test runs a Tier 1 scan against `tests/fixtures/clean-sample` and
asserts the exit code is 0 and the JSON verdict shape is valid. It needs only
bash and python3, so it passes whether or not the optional scanners are
installed.

## Limitations

- **macOS / BSD focused.** The heuristic file check uses BSD `find` syntax
  (`-perm +111`), which is what ships on macOS. On systems with GNU `find`
  (most Linux distributions) that specific check will error out; the rest of the
  scan is unaffected. This skill has been exercised on macOS only.
- **Point-in-time, not a guarantee.** A CLEAN verdict means the enabled checks
  found nothing blocking at scan time. It does not prove a repo is safe. New
  findings can appear as tools, rules, and vulnerability databases update.
- **Coverage depends on installed tools.** With few scanners present the scan
  falls back to heuristics and posture checks only. The verdict reflects what
  was actually run, not full coverage.
- **Network and auth dependent.** OSSF Scorecard needs a `GITHUB_TOKEN` and a
  GitHub remote; several tools consult remote vulnerability data and can be rate
  limited or time out. Timeouts are recorded as scan errors, not silent passes.
- **Heuristic thresholds.** Some checks are intentionally simple (for example
  flagging more than five non-standard executables) and can produce false
  positives or miss cleverly disguised issues. Treat findings as a prompt to
  review, not a final judgment.

## License

MIT. See the LICENSE file at the repository root.
