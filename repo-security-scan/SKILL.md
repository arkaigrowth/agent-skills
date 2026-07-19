---
name: repo-security-scan
description: Scan a repository for secrets, malware, risky dependencies, unsafe install scripts, and supply-chain issues. Use when evaluating whether a repo is safe to clone, run, or trust.
---

# Repository Security Scan

Trigger: "scan repo", "security scan", "check repo security", "safe-clone", "quarantine clone", "audit this repo", "scan for vulnerabilities", "repo-scan", "is this repo safe"

## Overview

Point-in-time security assessment for repositories using tiered scanning.
Wraps widely used open-source tools: Trivy, TruffleHog, Gitleaks, GuardDog, OSSF Scorecard, Semgrep, Syft, and Grype. Each tool is optional: the scanner detects what is installed and skips the rest, so it still runs (with reduced coverage) when some tools are missing.

The scanner ships with this skill at `scripts/repo-security-scan.sh`. The commands below assume you run them from the skill directory; adjust the path if you invoke it from elsewhere.

## Quick Commands

### Scan current project
```bash
bash scripts/repo-security-scan.sh .
```

### Scan with deeper analysis
```bash
bash scripts/repo-security-scan.sh --tier 2 /path/to/repo
```

### Full deep scan
```bash
bash scripts/repo-security-scan.sh --tier 3 /path/to/repo
```

### Quarantine clone (clone, scan, promote if clean)
```bash
bash scripts/repo-security-scan.sh --quarantine-clone https://github.com/user/repo ~/repo
```

### JSON output (for automation)
```bash
bash scripts/repo-security-scan.sh --tier 1 --json /path/to/repo
```

## Tiers

| Tier | Approx time | Tools | Use when |
|------|-------------|-------|----------|
| 1 (fast) | seconds | trivy, gitleaks, guarddog, heuristics | Every new clone, quick check |
| 2 (standard) | 1-3 min | + scorecard, syft then grype, semgrep, trufflehog | Before using a repo for real work |
| 3 (deep) | 3+ min | + full git history, license audit | Sensitive or high-stakes projects |

Times are rough guidance and depend on repo size, installed tools, and network conditions. They are not guaranteed.

## Quarantine Workflow

The safest approach for unknown repos:

1. **Clone to quarantine**: `--quarantine-clone` clones to `~/.quarantine/repos/` with `--depth 1`.
2. **Auto-scan**: Runs the specified tier of scans.
3. **Verdict-based promotion**:
   - CLEAN (score >= 80): auto-promoted to the destination.
   - WARN (score 50-79): promoted with a caution note.
   - CRITICAL (score < 50): stays in quarantine, you decide.

## Interpreting Results

### Score and verdict
- **80-100 (CLEAN)**: no blocking findings. Review any info notes.
- **50-79 (WARN)**: warnings present. Review findings before proceeding.
- **0-49 (CRITICAL)**: do not run install scripts until findings are resolved.

Score starts at 100 and subtracts per finding: critical -25, high -10, medium -3, low -1 (floored at 0). Exit code follows the verdict: 0 for CLEAN, 1 for WARN, 2 for CRITICAL.

### Severity
- **CRITICAL**: live credentials, known malicious packages, active threats.
- **HIGH**: unverified secrets, dangerous install scripts, .pth persistence files.
- **MEDIUM**: outdated deps with known CVEs, missing lockfiles, npm install scripts.
- **LOW**: minor vulns, style issues, info-level findings.

## What Gets Scanned

### Tier 1 (fast)
- **Trivy**: vulnerabilities, secrets, misconfigurations in all files.
- **Gitleaks**: secret/credential patterns in current files.
- **GuardDog**: known malicious packages in Python/npm dependencies.
- **Heuristics**: .pth files, dangerous setup.py calls, shell dotfiles, symlinks, .env files.
- **Posture**: Dependabot, SECURITY.md, pre-commit hooks, CI security scanning.

### Tier 2 (standard)
- **OSSF Scorecard**: supply chain health score (requires GITHUB_TOKEN and a GitHub remote).
- **Syft then Grype**: SBOM generation plus vulnerability scan.
- **Semgrep**: static analysis with security-audit and secrets rulesets.
- **TruffleHog**: deep secret scan with live credential verification.

### Tier 3 (deep)
- **TruffleHog Git**: full git history secret scan (every commit).
- **Trivy Licenses**: license compliance audit.

## Hook Integration

The skill bundles an optional PostToolUse hook at `hooks/repo_security_hook.py`.
When wired into your Claude Code `settings.json` as a PostToolUse hook on Bash, it automatically triggers a Tier 1 scan when:
- `git clone` is detected
- `npm ci` or a project-level `npm install` is detected
- `pip install -r` is detected

Other install commands (`npm install <pkg>`, `pip install <pkg>`, `cargo add`, `brew install`) trigger a reminder to scan.

The hook resolves the scanner relative to itself (`../scripts/repo-security-scan.sh`). Override the location with the `REPO_SCAN_SCANNER` environment variable if needed.

## Reports

By default a markdown report is written to `./reports/repo-scan-{name}-{timestamp}.md`. Override the directory with the `REPORT_DIR` environment variable, or pass `--no-report` to skip report generation.

## Environment Variables

- `REPORT_DIR`: report output directory (default `./reports`).
- `QUARANTINE_DIR`: quarantine clone directory (default `~/.quarantine/repos`).
- `REPO_SCAN_TIMEOUT`: per-tool timeout in seconds (default 60).
- `REPO_SCAN_LIB`: optional path to a shell file defining `send_alert` for desktop notifications. Skipped if unset.
- `GITHUB_TOKEN`: enables the OSSF Scorecard check in Tier 2.
