# keychain-token

Store, name, retrieve, and rotate API tokens in the macOS Keychain without the
secret ever hitting shell history, scrollback, or an agent's context.

This is an installable [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
skill (`SKILL.md`) plus two small shell wrappers (`kc-store`, `kc-get`) that
give the same workflow a defined exit-code contract for scripts and CI.

## Why

Secrets pasted into a normal command line end up in `~/.bash_history`,
scrollback, and sometimes an agent's transcript. The macOS Keychain is already
on every Mac and encrypts at rest, but the raw `security` commands are easy to
get wrong (secret leaked as an argument, no consistent naming, no clean error
signal). This skill fixes the naming and the leak paths, and the wrappers turn
"did it work?" into a real exit code.

## What is in here

| File | Purpose |
|---|---|
| `SKILL.md` | The Claude Code skill: naming convention, fish/bash one-liners, the never-echo rules. |
| `scripts/kc-store` | Read a secret from stdin, store or rotate it in the Keychain. |
| `scripts/kc-get` | Print a stored secret to stdout for capture in a script. |
| `tests/test_kc.sh` | Exit-code and round-trip tests (uses a throwaway keychain). |

## Install (as a Claude Code skill)

Copy or symlink this directory into your Claude Code skills directory:

```bash
mkdir -p ~/.claude/skills
cp -R keychain-token ~/.claude/skills/keychain-token
```

The skill activates when you ask about storing, naming, or reading a token.

## Usage (the wrappers)

Store or rotate a token. The secret comes in on stdin, never as an argument:

```bash
printf '%s' "$TOKEN" | scripts/kc-store gha-acme-prod-deploy acme "Vercel API token"
```

Read it back inside a script:

```bash
TOKEN=$(scripts/kc-get gha-acme-prod-deploy)
```

Naming follows `<consumer>-<scope>-<purpose>`, named for the machine that uses
the token, not the person who made it. See `SKILL.md` for the full convention.

### Exit codes

`kc-store`:

| Code | Meaning |
|---|---|
| 0 | stored |
| 2 | usage error (wrong args, or empty secret on stdin) |
| 4 | the underlying `security` command failed |
| 5 | not macOS (no `security` binary) |

`kc-get`:

| Code | Meaning |
|---|---|
| 0 | found (secret written to stdout) |
| 2 | usage error |
| 3 | not found |
| 5 | not macOS (no `security` binary) |

### Optional env

`KC_KEYCHAIN` points both wrappers at a specific keychain file instead of the
login keychain. The test suite uses it to avoid touching your real keychain.

## Tests

```bash
bash tests/test_kc.sh
```

The round-trip tests create a throwaway keychain, store and read a fake secret,
and delete the keychain on exit, so they never modify your login keychain.
Result on the author's machine (macOS 26.5, bash 5.3): 8 passed, 0 failed. The
contract tests run anywhere; the round-trip tests skip themselves if `security`
is absent (non-macOS).

## Limitations

- macOS only. Everything here depends on the `security` command and the macOS
  Keychain. There is no Linux or Windows path.
- Single-line secrets. `kc-store` reads one line from stdin, which fits API
  tokens but not multi-line blobs like PEM keys.
- `kc-store` passes the secret to `security` via `-w`, so it is briefly visible
  in that child process's arguments (for example to `ps`) for the duration of
  the call. This matches the standard `security add-generic-password` usage and
  keeps the secret out of your shell history, but it is not the same as a tool
  that reads the secret over a pipe end to end.
- No audit log or access policy beyond what the Keychain itself provides.

## License

MIT. See the repository root `LICENSE`.
