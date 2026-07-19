# Patch Lifecycle

Use this lifecycle whenever a local dependency patch is created, updated, or audited.

## Preflight

Before patching:

1. Reproduce the bug or missing behavior.
2. Confirm the package manager and preferred patch system.
3. Check if upstream already fixed the issue.
4. Check whether a version change avoids the patch entirely.
5. Map where the dependency is used in the local repo.

## Creation

When creating the patch:

1. Keep the change as small and obvious as possible.
2. Add comments inside vendor code only when the fix would otherwise be confusing.
3. Prefer patching readable output over minified output whenever possible.
4. Record whether the patch touches probable transpiled output.

## Verification

After creating or updating the patch:

1. Reinstall from a clean state.
2. Confirm the patch reapplies cleanly.
3. Run the most relevant tests or smoke checks.
4. Call out any CI cache assumptions or install hooks that must stay in place.

## CI And Docker Hygiene

- Cache keys should include lockfiles, `package.json`, and patch files.
- Docker builds should copy `patches/` before the install step that applies them.
- Do not rely on stale `node_modules` caches to prove a patch works.

The helper can print a stable cache key:

```bash
PATCH_SKILL_DIR="${HOME}/.claude/skills/patch-package"
if [ ! -f "${PATCH_SKILL_DIR}/scripts/patch_registry.py" ]; then
  PATCH_SKILL_DIR="${HOME}/.codex/skills/patch-package"
fi
python3 "${PATCH_SKILL_DIR}/scripts/patch_registry.py" cache-key --repo .
```

## Required Metadata

Every patch needs all of the following:

- `reason`: why the patch exists
- `owner`: who owns checking and retiring it
- `removal_condition`: what lets the team delete it
- `review_date`: when to revisit it
- `patch_system`: `patch-package`, `bun-native`, `pnpm-native`, or `yarn-native`

Strongly recommended:

- `upstream_url`
- `upstream_status`
- `notes`

The helper script stores this in `patches/.patch-metadata.json` and renders `patches/README.md`.

## Review Cadence

Default review cadence: 30 days from creation or update.

Review questions:

1. Is the patch still needed on the current dependency version?
2. Has upstream released a fix?
3. Is the patch still small and understandable?
4. Can we replace it with an upgrade, override, or upstream release now?

## Retirement

Remove the patch when one of these becomes true:

- upstream released a fix and the repo adopted it
- a dependency version change made the patch irrelevant
- the local code no longer relies on the broken behavior
- the team replaced the patch with a proper fork or alternative approach

After retirement:

1. delete the patch file
2. remove its metadata entry
3. regenerate `patches/README.md`
4. rerun the audit helper

## Suggested Repo Convention

Inside the target repo:

```text
patches/
  README.md
  .patch-metadata.json
  some-package+1.2.3.patch
```

Keep the patch folder tracked in Git.
Do not allow anonymous patch files to accumulate without metadata coverage.
