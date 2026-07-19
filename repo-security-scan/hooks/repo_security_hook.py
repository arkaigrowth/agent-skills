#!/usr/bin/env python3
"""
Repo Security Hook: auto-scans after git clone, triggers reminders for installs.

PostToolUse hook on Bash. Detects:
  - git clone: runs Tier 1 scan automatically
  - npm install/ci (no package arg): runs Tier 1 scan
  - pip install -r: runs Tier 1 scan
  - Other installs: prints reminder

Output goes to Claude's context as a system message, so Claude can
relay findings to the user and suggest deeper scans if needed.

The scanner is resolved relative to this hook (../scripts/repo-security-scan.sh).
Override with the REPO_SCAN_SCANNER environment variable.
"""

import json
import sys
import os
import re
import subprocess


SCANNER = os.environ.get(
    "REPO_SCAN_SCANNER",
    os.path.normpath(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "scripts",
            "repo-security-scan.sh",
        )
    ),
)


def main():
    # Read hook context from stdin
    try:
        ctx = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    tool_name = ctx.get("tool_name", "")
    if tool_name != "Bash":
        return

    tool_input = ctx.get("tool_input", {})
    command = tool_input.get("command", "")
    output = str(ctx.get("tool_output", ""))

    # Fast exit for non-matching commands (< 1ms overhead)
    action = classify_command(command)
    if action is None:
        return

    target_dir = extract_target(action, command, output)

    if action == "git_clone" and target_dir and os.path.isdir(target_dir):
        run_scan(target_dir)
    elif action == "npm_project_install" and target_dir and os.path.isdir(target_dir):
        run_scan(target_dir)
    elif action == "pip_requirements" and target_dir and os.path.isdir(target_dir):
        run_scan(target_dir)
    elif action in ("npm_pkg_install", "pip_pkg_install", "cargo_install", "brew_install"):
        repo_name = os.path.basename(target_dir) if target_dir else "this project"
        print(f"[repo-security-hook] Package install detected ({action}). "
              f"Consider running: /repo-scan or "
              f"bash {SCANNER} {target_dir or '.'}")


def classify_command(command: str) -> str | None:
    """Classify the bash command into an action type, or None if irrelevant."""
    cmd = command.strip()

    # git clone
    if re.search(r"\bgit\s+clone\b", cmd):
        return "git_clone"

    # npm ci or npm install with no package argument
    if re.search(r"\bnpm\s+ci\b", cmd):
        return "npm_project_install"
    if re.search(r"\bnpm\s+(install|i)\s*$", cmd):
        return "npm_project_install"
    if re.search(r"\bnpm\s+(install|i)\s+-", cmd) and not re.search(r"\bnpm\s+(install|i)\s+\w", cmd):
        return "npm_project_install"
    if re.search(r"\bnpm\s+(install|i)\s+\w", cmd):
        return "npm_pkg_install"

    # pip install -r requirements.txt
    if re.search(r"\bpip3?\s+install\s+-r\b", cmd):
        return "pip_requirements"
    if re.search(r"\bpip3?\s+install\b", cmd):
        return "pip_pkg_install"

    # cargo
    if re.search(r"\bcargo\s+(add|install)\b", cmd):
        return "cargo_install"

    # brew
    if re.search(r"\bbrew\s+install\b", cmd):
        return "brew_install"

    return None


def extract_target(action: str, command: str, output: str) -> str | None:
    """Extract the target directory from the command or its output."""
    if action == "git_clone":
        # Parse from output: "Cloning into 'dir'..."
        m = re.search(r"Cloning into '([^']+)'", output)
        if m:
            path = m.group(1)
            if not os.path.isabs(path):
                path = os.path.join(os.getcwd(), path)
            return path

        # Parse from command: git clone [flags] URL [dir]
        parts = command.split()
        try:
            idx = parts.index("clone")
            args = [p for p in parts[idx + 1:] if not p.startswith("-")]
            if len(args) >= 2:
                return os.path.expanduser(args[-1])
            elif len(args) == 1:
                url = args[0]
                name = os.path.basename(url).rstrip("/").replace(".git", "")
                return os.path.join(os.getcwd(), name)
        except (ValueError, IndexError):
            pass

    # For install commands, target is the project directory (CWD)
    return os.getcwd()


def run_scan(target_dir: str):
    """Run Tier 1 scan and output results for Claude."""
    if not os.path.isfile(SCANNER):
        print(f"[repo-security-hook] Scanner not found at {SCANNER}")
        return

    repo_name = os.path.basename(target_dir)

    try:
        result = subprocess.run(
            ["bash", SCANNER, "--tier", "1", "--quiet", "--no-report", "--json", target_dir],
            capture_output=True,
            text=True,
            timeout=45,
        )

        if result.stdout:
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                print(f"[repo-security-hook] Scan completed but output was not valid JSON")
                return

            verdict = data.get("verdict", "UNKNOWN")
            score = data.get("score", "?")
            summary = data.get("summary", {})
            crit = summary.get("critical", 0)
            high = summary.get("high", 0)
            med = summary.get("medium", 0)

            if verdict == "CRITICAL":
                print(f"[repo-security-hook] CRITICAL: {repo_name} (score {score}/100)")
                print(f"  {crit} critical, {high} high, {med} medium findings")
                print(f"  Recommend deeper scan: bash {SCANNER} --tier 2 {target_dir}")
                # List critical findings
                for f in data.get("findings", []):
                    if f.get("severity") in ("CRITICAL", "HIGH"):
                        print(f"  - [{f['severity']}] {f.get('tool', '?')}: {f.get('message', '')}")
            elif verdict == "WARN":
                print(f"[repo-security-hook] WARNINGS: {repo_name} (score {score}/100)")
                print(f"  {crit} critical, {high} high, {med} medium findings")
                print(f"  Consider: bash {SCANNER} --tier 2 {target_dir}")
            else:
                print(f"[repo-security-hook] CLEAN: {repo_name} (score {score}/100)")
        else:
            print(f"[repo-security-hook] Scan produced no output for {repo_name}")

    except subprocess.TimeoutExpired:
        print(f"[repo-security-hook] Scan timed out for {repo_name} (45s limit)")
    except FileNotFoundError:
        print(f"[repo-security-hook] bash not found")


if __name__ == "__main__":
    main()
