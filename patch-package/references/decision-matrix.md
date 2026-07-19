# Decision Matrix

This skill is about safe dependency patching in general, not blindly using `patch-package`.

## Preferred Tool by Package Manager

| Repo signal | Preferred tool | Why |
| --- | --- | --- |
| `package-lock.json` or `npm-shrinkwrap.json` | `patch-package` | No native npm patch workflow comparable to pnpm/Yarn |
| `bun.lock` or `bun.lockb` | `bun patch` | Bun has a native patch workflow and tracks patched dependencies |
| `yarn.lock` without `.yarnrc.yml` | `patch-package` | Yarn 1 works with `node_modules` and `postinstall` |
| `pnpm-lock.yaml` | `pnpm patch` + `pnpm patch-commit` | Native workflow, cleaner manifest integration |
| `yarn.lock` with `.yarnrc.yml` or `packageManager: "yarn@3/4"` | `yarn patch` + `yarn patch-commit` | Native workflow, patch protocol support |

If multiple lockfiles exist, stop and resolve the real package manager before patching.
Treat mixed lockfiles as a hard error, not a soft warning.

## Green / Yellow / Red Cases

### Green: patch locally

- Small behavioral bug in a dependency
- Missing guard, null check, type fix, or narrow logic correction
- You can test the fix locally and keep the diff small
- There is a plausible upstream fix path, but you need to unblock now

### Yellow: proceed only with explicit callout

- Patch touches transpiled output in `dist/`, `build/`, or bundled artifacts
- Patch affects a dependency used in many critical codepaths
- Patch has no upstream issue yet, but you have a concrete reason and removal plan
- Patch is likely to survive for more than a sprint

### Red: do not use local patching as the default

- A simple version change fixes the issue
- The real need is `overrides`, `resolutions`, or package-manager dependency metadata
- The patch must change the dependency graph
- The change is large, hard to review, or security-sensitive
- The repo is an npm library intended for broad external consumption

## Alternatives Before Patching

Try these before editing vendor code:

1. Upgrade or downgrade the dependency.
2. Use `overrides` or `resolutions` to force a better subdependency version.
3. Fix local configuration or integration code.
4. Use native package-manager patching if the repo already supports it.
5. Fork when the change is large, strategic, or likely to be long-lived.

## Brutal Honesty

- `patch-package` is a band-aid, not a platform.
- Patches are version-bound and often break quietly during upgrades.
- Patching compiled output is sometimes necessary, but it is debt and should be treated like debt.
- A patch without an owner and retirement path is a future outage waiting to happen.
- CI caches and Docker layers must account for patch files, or you will debug ghosts.

## Official References

- `patch-package`: [npm](https://www.npmjs.com/package/patch-package) and [GitHub](https://github.com/ds300/patch-package)
- Bun patching: [bun patch](https://bun.sh/docs/pm/cli/patch)
- `pnpm patch`: [pnpm patch](https://pnpm.io/cli/patch) and [pnpm patch-commit](https://pnpm.io/cli/patch-commit)
- Yarn native patching: [feature overview](https://yarnpkg.com/features/patching) and [yarn patch](https://yarnpkg.com/cli/patch)
