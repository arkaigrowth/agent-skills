# patch-package (Claude Code skill)

A Claude Code skill for patching a Node dependency locally without letting the
patch become forgotten debt. It picks the right patch tool for the repo
(`patch-package`, `bun patch`, `pnpm patch`, or `yarn patch`), then tracks every
patch with an owner, a reason, and a removal condition.

## What this is

Local dependency patches are easy to create and easy to forget. They are
version-bound, they break quietly on upgrade, and a patch with no owner and no
retirement path is a future incident. This skill guides the workflow and ships a
deterministic helper (`scripts/patch_registry.py`) that audits a repo's patch
setup and records lifecycle metadata so patches stay reviewable.

The skill has two parts:

- `SKILL.md`: the instructions Claude Code loads. It chooses the right patching
  path for the package manager, keeps changes surgical, and enforces metadata.
- `scripts/patch_registry.py`: a standalone Python helper you can run yourself.
  No network calls, no dependencies beyond the standard library.

## Why the package manager matters

"patch-package" is the name of one tool, not the only way to patch. The helper
detects the repo's package manager and recommends the native path:

| Repo signal | Recommended patch system |
| --- | --- |
| `package-lock.json` / `npm-shrinkwrap.json` | `patch-package` |
| `yarn.lock` without `.yarnrc.yml` (Yarn 1) | `patch-package` |
| `pnpm-lock.yaml` | `pnpm patch` + `pnpm patch-commit` |
| `bun.lock` / `bun.lockb` | `bun patch` |
| `yarn.lock` with `.yarnrc.yml` (Yarn 2+) | `yarn patch` + `yarn patch-commit` |

If more than one lockfile is present, the helper reports `ambiguous` and stops
rather than guessing.

## Install as a Claude Code skill

Copy this folder into your skills directory:

```bash
cp -R patch-package ~/.claude/skills/patch-package
```

Claude Code discovers it by the frontmatter in `SKILL.md`. The skill activates
when you ask about patching a Node dependency, `patch-package`, `pnpm patch`,
`yarn patch`, `bun patch`, or auditing existing patches.

## Use the helper directly

The helper needs only Python 3.8 or newer. It has four subcommands:

```bash
# Audit a repo's patch setup (package manager, patches, metadata, cache key)
python3 scripts/patch_registry.py audit --repo /path/to/repo

# Register or update lifecycle metadata for a patch, and regenerate the README
python3 scripts/patch_registry.py register \
  --repo /path/to/repo \
  --patch-file patches/left-pad+1.3.0.patch \
  --reason "guard against undefined padding length" \
  --removal-condition "upstream 1.4.0 ships the null check" \
  --upstream-url "https://github.com/example/left-pad/pull/42" \
  --owner "$USER"

# Regenerate patches/README.md from patches/.patch-metadata.json
python3 scripts/patch_registry.py sync-readme --repo /path/to/repo

# Print a stable cache key derived from lockfiles, package.json, and patches
python3 scripts/patch_registry.py cache-key --repo /path/to/repo
```

## Quickstart

```bash
# 1. Audit before touching anything
python3 scripts/patch_registry.py audit --repo .

# 2. Create the patch with the recommended tool, for example on pnpm:
pnpm patch some-package
# edit the files pnpm opens, then:
pnpm patch-commit <temp-dir>

# 3. Record the lifecycle metadata so the patch is not anonymous
python3 scripts/patch_registry.py register \
  --repo . \
  --patch-file patches/some-package+1.2.3.patch \
  --reason "why this exists" \
  --removal-condition "what lets us delete it" \
  --owner "$USER"

# 4. Re-audit to confirm the patch is now tracked
python3 scripts/patch_registry.py audit --repo .
```

## Sample audit output

Running `audit` against a pnpm repo whose one patch edits minified `dist/`
output and has no metadata yet:

```text
package_manager: pnpm
recommended_patch_system: pnpm-native
patch_count: 1
metadata_file: missing
readme_file: missing
patch_package_dependency: missing
postinstall: (none)
patches:
  - left-pad+1.3.0.patch | lines=2 | transpiled=yes
warnings:
  - Patch files exist but patches/.patch-metadata.json is missing.
  - Patch files exist but patches/README.md is missing.
  - Patch file left-pad+1.3.0.patch has no metadata entry.
  - Patch left-pad+1.3.0.patch likely edits transpiled or bundled output: node_modules/left-pad/dist/index.min.js
cache_key: 8b9a8c8f6969c10f8fa81cbcd1c5c37f3235b6cbb4b8ee4726d93d3d3fd64b53
```

The `cache_key` is a SHA-256 over the repo's lockfiles, `package.json`, and
patch files, so it changes whenever any of those change. Use it in CI or Docker
cache keys so a patch change actually busts the dependency cache.

`audit` exits non-zero when there are fatal issues (an ambiguous package
manager, or patch files with no determinable package manager). Pass `--strict`
to also fail on warnings.

## Layout

```text
patch-package/
  SKILL.md                     installable Claude Code skill (frontmatter + guide)
  scripts/patch_registry.py    deterministic audit and metadata helper
  references/decision-matrix.md when to use patch-package vs native patching
  references/lifecycle.md       lifecycle, risk model, metadata conventions
  agents/openai.yaml            optional agent-interface descriptor (see file header)
  tests/test_patch_registry.py  pytest suite for the helper
```

## Run the tests

```bash
python3 -m pytest -q
# or, isolated:
uv run --with pytest pytest -q
```

Current status: 23 tests pass (covers `detect_package_manager` across npm,
pnpm, yarn classic, yarn berry, bun, ambiguous, and unknown, plus
`parse_patch_file` path extraction, changed-line counting, transpiled-output
detection, and dev-only naming).

## Limitations

- Package-manager detection is a heuristic based on lockfiles and the
  `packageManager` field. It does not invoke the package managers themselves.
- Transpiled-output detection is a path-substring heuristic (`/dist/`,
  `.min.js`, and similar). It flags likely bundled edits; it can miss unusual
  layouts and can false-positive on a source path that happens to contain one of
  those substrings.
- The helper audits and records metadata. It does not create patches, run the
  underlying patch tools, or install anything.
- The shell examples target macOS and Linux. Commands were exercised on macOS
  with Python 3.11; the helper targets Python 3.8 or newer.
- The skill guidance is written for Claude Code; the `agents/openai.yaml`
  descriptor is optional and can be deleted if unused.

## License

MIT. See the repository root `LICENSE`.
