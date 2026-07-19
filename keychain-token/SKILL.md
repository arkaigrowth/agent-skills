---
name: keychain-token
description: Store, name, retrieve, and rotate API tokens/secrets in the macOS Keychain safely. Use whenever the user gets a new API token/key/secret, asks how to store or name a credential, needs the paste-to-keychain one-liner, or asks to read a stored token into a script. Covers the consumer-scope-purpose naming convention, fish and bash variants, and the never-echo rules.
---

# Keychain token storage

One canonical pattern for getting a secret from a clipboard into the macOS
login Keychain without it touching shell history, scrollback, or an agent's
context, plus a naming scheme that lets you find it again a year later.

macOS only: this relies on the `security` command and the login Keychain.

## Naming convention (decide BEFORE storing)

`<consumer>-<scope>-<purpose>`, naming the token for the MACHINE that uses it,
never the human who made it. Test: reading only the name, you know what breaks
if you revoke it.

| Piece | Examples |
|---|---|
| consumer | `gha` (GitHub Actions), `codex`, `claude`, `n8n`, `cron` |
| scope | `acme-prod`, `acme-billing`, `internal` |
| purpose | `deploy`, `readonly`, `api`, `webhook` |

Examples: `gha-acme-prod-deploy`, `cron-acme-billing-readonly`.
Use the SAME string for the Keychain service (`-s`) and label (`-l`).

## Store (interactive paste, nothing echoed)

Fill in: NAME (per convention), ACCOUNT (owning identity or org, e.g.
`acme`, `api@vendor.com`), KIND (human-readable type, e.g. "Vercel API
token").

fish:

```fish
read -s -P "Paste NAME token: " TOK; and security add-generic-password -U -a ACCOUNT -s NAME -l NAME -D "KIND" -w "$TOK"; and set -e TOK
```

bash/zsh:

```bash
read -rs -p "Paste NAME token: " TOK && security add-generic-password -U -a ACCOUNT -s NAME -l NAME -D "KIND" -w "$TOK"; unset TOK
```

Notes: `-U` updates in place if the entry exists (this is also the rotation
command); `read -s` keeps the paste out of the terminal and history; the
trailing `set -e`/`unset` clears the env var immediately.

Alternative with no shell variable at all (Keychain prompts you):

```bash
security add-generic-password -U -a ACCOUNT -s NAME -l NAME -D "KIND" -w
```

## Retrieve (in scripts)

```bash
TOK=$(security find-generic-password -s NAME -w)
```

Prefer lookup by service (`-s`). If an entry was renamed in the Keychain
Access GUI, only its LABEL changed, so fall back to `-l NAME`.

## Verify it stored (without printing the secret)

```bash
security find-generic-password -s NAME | grep -E '"svce"|"acct"|"labl"'
```

## Helper scripts

`scripts/kc-store` and `scripts/kc-get` wrap the two commands above with a
defined exit-code contract, so scripts and CI can branch on failure instead of
parsing text. The secret goes in on stdin (kc-store) and comes out on stdout
(kc-get); neither is ever a command-line argument to the wrapper.

```bash
printf '%s' "$TOKEN" | scripts/kc-store gha-acme-prod-deploy acme "Vercel API token"
TOKEN=$(scripts/kc-get gha-acme-prod-deploy)
```

See `README.md` for the full exit-code table.

## Auth browser launches (provenance note)

When a stored token belongs to an OAuth or consent flow, do not blindly
`open` the consent URL from an automated session. With several agent sessions
running at once, an unlabeled auth tab is hard to trace back to the process
that spawned it. Announce in the terminal which session and purpose is opening
a tab before triggering it, or route the URL through your own click-to-confirm
launcher so a human approves each one. Browser launches made internally by a
binary cannot be intercepted; for those, announce before triggering.

## Rules (non-negotiable)

1. NEVER echo, print, or log the secret; never pass it as a visible CLI arg
   in a command an agent composes. Agents: have the USER run the store
   command; scripts read via `find-generic-password` (or `kc-get`) at runtime.
2. No `set -x` anywhere near these commands.
3. One entry per token. Rotation = same command with `-U`, new value.
4. Person-named tokens are banned for CI/automation.
5. When a token is revoked upstream, delete the entry:
   `security delete-generic-password -s NAME`.

## Drift control

If you symlink this skill into more than one agent home (for example a
Claude Code skills directory and a Codex skills directory), keep ONE canonical
copy and point the others at it with directory symlinks. Edit only the
canonical copy so the variants never drift apart.
