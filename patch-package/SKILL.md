---
name: patch-package
description: Use when you need to hotfix a Node dependency locally with patch-package, pnpm patch, yarn patch, or bun patch. Guides safe dependency patching, metadata tracking, audit checks, and patch retirement so temporary fixes do not become forgotten debt.
---

# Patch Package

Use this skill for safe, temporary dependency patching in Node projects.

Despite the name, this skill is not a blanket instruction to use `patch-package`.
Its first job is to choose the right patching path:

- `npm` or Yarn 1: `patch-package` is usually the right tool.
- `bun`: prefer `bun patch` and `bun patch --commit`.
- `pnpm`: prefer `pnpm patch` and `pnpm patch-commit`.
- Yarn 2+ / Berry: prefer `yarn patch` and `yarn patch-commit`.

If the repo is on `bun`, `pnpm`, or Yarn Berry, do not reach for `patch-package` by habit.

## Use This Skill When

- A dependency bug is blocking delivery and you need a local hotfix now.
- The fix is small, surgical, and easy to review as a diff.
- The user asks about `patch-package`, `pnpm patch`, `yarn patch`, or patching `node_modules`.
- A dependency patch already exists and needs auditing, documenting, updating, or retiring.

## Do Not Use This Skill When

- A normal upgrade, downgrade, `overrides`, `resolutions`, or configuration change will solve the problem more cleanly.
- The change is large, long-lived, security-sensitive, or should really live in a fork.
- The patch needs to change the dependency graph rather than the package contents.
- The target is a published library unless the user explicitly accepts the downstream risk.

## Default Workflow

All `patch_registry.py` commands below use the skill's bundled helper, not a file in the target repo.
Resolve the installed skill path once before using the helper:

```bash
PATCH_SKILL_DIR="${HOME}/.claude/skills/patch-package"
if [ ! -f "${PATCH_SKILL_DIR}/scripts/patch_registry.py" ]; then
  PATCH_SKILL_DIR="${HOME}/.codex/skills/patch-package"
fi
```

### 1. Audit Before Touching Anything

Run the bundled audit helper first:

```bash
python3 "${PATCH_SKILL_DIR}/scripts/patch_registry.py" audit --repo .
```

This checks:

- package manager and preferred patch system
- existing `patches/*.patch`
- `patch-package` dependency and `postinstall` setup where relevant
- metadata coverage in `patches/.patch-metadata.json`
- README coverage in `patches/README.md`
- probable transpiled or minified vendor edits
- a stable cache key for lockfiles and patch content

### 2. Prove the Patch Is the Right Move

Before editing vendor code:

- reproduce the bug or missing behavior locally
- check whether upstream already fixed it
- check whether a package upgrade or downgrade removes the need
- map where the dependency is used in the repo

When available, use semantic repo search to understand dependency usage before patching.
If the relevant package or repo surface is large, use recursive analysis tools to keep context bounded.

### 3. Choose the Right Patch Mechanism

For `npm` or Yarn 1:

```bash
# edit the installed dependency first
npx patch-package <package-name>
```

Make sure the target repo has:

- `patch-package` installed, usually in `devDependencies`
- `"postinstall": "patch-package"` in `package.json`
- `postinstall-postinstall` as a follow-up consideration for Yarn 1

For `bun`:

```bash
bun patch <package-name>
bun patch --commit <package-name>
```

Do not edit a Bun-managed dependency before running `bun patch <package-name>`.
Bun warns that skipping this step can accidentally edit its global cache.

For `pnpm`:

```bash
pnpm patch <package-name>
pnpm patch-commit <temp-dir>
```

For Yarn 2+ / Berry:

```bash
yarn patch <package-name>
yarn patch-commit -s <temp-dir>
```

### 4. Keep the Change Surgical

- Prefer the smallest fix that unblocks the app.
- Call out when you are patching transpiled output, bundled files, or minified files.
- Avoid changing package internals you do not understand.
- If the patch becomes multi-file, semantic, or invasive, stop and reconsider a fork.

### 5. Verify From a Clean Install

Do not trust a patch until it survives reinstall:

- reinstall dependencies from a clean state
- confirm the patch reapplies cleanly
- run the most relevant tests or verification path
- note any CI or cache assumptions that matter

For CI or Docker-heavy repos, print the cache key and make sure caches include it:

```bash
python3 "${PATCH_SKILL_DIR}/scripts/patch_registry.py" cache-key --repo .
```

At minimum, the dependency cache should change when lockfiles or patch files change.

### 6. Register the Lifecycle Metadata

Every patch must be documented with an owner, reason, upstream link when available, and a removal condition.

Use the helper:

```bash
python3 "${PATCH_SKILL_DIR}/scripts/patch_registry.py" register \
  --repo . \
  --patch-file patches/<patch-file>.patch \
  --reason "why this patch exists" \
  --removal-condition "what lets us delete it" \
  --upstream-url "https://..." \
  --owner "$USER"
```

This updates:

- `patches/.patch-metadata.json`
- `patches/README.md`

If metadata is edited manually later, regenerate the README:

```bash
python3 "${PATCH_SKILL_DIR}/scripts/patch_registry.py" sync-readme --repo .
```

### 7. Report the Debt Honestly

Always tell the user:

- which patching system was used
- whether the patch touches transpiled or minified output
- what upstream path exists, if any
- when the patch should be reviewed or removed

## Cross-Tool Integration

### Before patching: map dependency usage

When semantic repo search is available, use it before editing vendor code.
For example, with Auggie or an equivalent codebase retrieval tool, ask where the package is imported and how the affected API is used.

This helps catch:

- patches against codepaths the repo never calls
- secondary callsites that will inherit the behavior change
- local integration mistakes that look like dependency bugs

### After patching: persist the decision

When RLM or an equivalent long-context store is available, save a compact record keyed by the patch name or package version.
Example key: `patch:lodash+4.17.21`

Include:

- reason
- upstream URL
- removal condition
- review date
- patch system used

This keeps future sessions from rediscovering the same patch from scratch.

### Optional: create a debt ticket

If the active client has Jira or another ticketing connector, create a review ticket for patches likely to survive more than one sprint.

Suggested fields:

- summary: `[patch-debt] <package-name>+<version> review`
- due date: the metadata `review_date`
- labels: `patch-debt`, `tech-debt`
- body: reason, upstream URL, removal condition, and owner

## Safety Rules

- Never leave a patch without metadata.
- Never leave a patch without a removal condition.
- Never default to `patch-package` in `bun`, `pnpm`, or Yarn Berry repos.
- Never proceed when package-manager signals are mixed or ambiguous.
- Never hide long-lived patches inside vendor code without a review date.
- Prefer short-lived patches and upstream fixes over permanent local divergence.

## References

- [references/decision-matrix.md](references/decision-matrix.md): when to use `patch-package` versus native package-manager patching
- [references/lifecycle.md](references/lifecycle.md): lifecycle, risk model, and metadata conventions
- [scripts/patch_registry.py](scripts/patch_registry.py): deterministic audit and metadata helper
