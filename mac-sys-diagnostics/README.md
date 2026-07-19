# mac-sys-diagnostics

A macOS diagnostic command reference for memory leaks, zombie processes,
WindowServer bloat, MCP server issues, and stuck Secure Input (the usual cause
of Caps Lock and keyboard-shortcut failures).

This is an installable [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
skill (`SKILL.md`) plus a small set of helper scripts for the Secure Input /
Caps Lock workflow.

## What this is (and is not)

This is a curated collection of read-only diagnostic command blocks plus two
small wrapper scripts. It is a command reference and a couple of wrappers, not
a packaged, automated, or independently benchmarked tool. The commands are
standard macOS utilities (`ps`, `ioreg`, `vm_stat`, `lsof`, `launchctl`, and
similar). Anything that kills a process or deletes a file is left for you to
confirm and run yourself. macOS only.

## What is in here

| Path | Purpose |
|---|---|
| `SKILL.md` | The Claude Code skill: progressive triage, memory/zombie/WindowServer/MCP diagnostics, and the Secure Input workflow. |
| `references/advanced_scenarios.md` | Deeper scenarios: kernel panics, disk I/O, network hangs, launchd, code signing, memory-pressure crises. |
| `helper-scripts/caps-lock-fix.sh` | Bash Secure Input diagnostic with an optional `--fix` mode. |
| `helper-scripts/fish-caps-functions.fish` | Fish functions: `caps-check`, `caps-fix`, `capsnow`. |
| `helper-scripts/CAPS_LOCK_FIX_SUMMARY.md` | Background and usage docs for the Secure Input fix. |
| `tests/test_scripts.sh` | Syntax and frontmatter checks (see Tests below). |

## Install (as a Claude Code skill)

Copy or symlink this directory into your Claude Code skills directory:

```bash
mkdir -p ~/.claude/skills
cp -R mac-sys-diagnostics ~/.claude/skills/mac-sys-diagnostics
```

The skill activates when you describe a symptom, for example "run a system
triage", "check for zombie processes", "WindowServer is using too much memory",
or "Caps Lock stopped working".

## Install the helper scripts (optional, for use without Claude)

```bash
mkdir -p ~/bin
cp helper-scripts/caps-lock-fix.sh ~/bin/
chmod +x ~/bin/caps-lock-fix.sh

# Fish users, to get caps-check / caps-fix / capsnow:
echo "source ~/bin/fish-caps-functions.fish" >> ~/.config/fish/config.fish
```

## Usage

### Via Claude

Describe the symptom and let the skill run the matching diagnostic block:

- "Run system triage"
- "Check for zombies"
- "Find memory leaks"
- "WindowServer using too much memory"
- "Caps Lock not working" / "Check Secure Input"

### Secure Input / Caps Lock from the terminal

```bash
# Quick check: is Secure Input stuck?
ioreg -l -d 1 -w 0 | grep SecureInput   # no output means it is off

# Full diagnostic
~/bin/caps-lock-fix.sh

# Attempt an automatic fix (save your work first)
~/bin/caps-lock-fix.sh --fix
```

See `helper-scripts/CAPS_LOCK_FIX_SUMMARY.md` for the full workflow and the
Fish functions.

## Safety notes

- The triage and inspection blocks are read-only.
- Commands that terminate processes or delete files are marked and, where
  destructive, placed behind explicit warning blocks with safer alternatives
  first. Read those blocks before running them.
- `kill -9`, `sudo killall -9 WindowServer`, and any `rm -rf` are last resorts,
  not defaults. Prefer graceful termination and, for WindowServer, a normal log
  out / log in.

## Tests

`tests/test_scripts.sh` is a lightweight smoke test. It does not run any
diagnostic or fix (nothing is killed or deleted). It checks:

- `caps-lock-fix.sh` parses under `bash -n`.
- `fish-caps-functions.fish` parses under `fish -n` (skipped if `fish` is not
  installed).
- `SKILL.md` has valid frontmatter with a `name` and `description`.

Run it:

```bash
bash tests/test_scripts.sh
```

## Limitations

- macOS only. Several commands assume macOS tools (`ioreg`, `vm_stat`,
  `memory_pressure`, `launchctl`, `system_profiler`) and will not work on Linux.
- The command output snippets are illustrative and not benchmarks; thresholds
  such as "over 20% memory" are rules of thumb, not measured limits.
- The Secure Input scripts read a PID from `ioreg`; on some macOS versions the
  field may be absent, in which case they report Secure Input as off.

## License

MIT. See the repository root `LICENSE`.
