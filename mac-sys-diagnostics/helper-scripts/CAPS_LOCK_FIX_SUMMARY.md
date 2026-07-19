# Caps Lock / Secure Input Fix

Documentation for the Secure Input helper scripts in this folder. On macOS,
Caps Lock and other keyboard shortcuts can stop responding when the system's
Secure Input mode gets stuck ON. This describes why that happens and the
several ways to clear it.

## Background: what causes it

macOS enables Secure Input while an app is reading a password so that other
processes cannot observe the keystrokes. If the app crashes, or fails to turn
Secure Input back off after a password or licensing dialog, the mode can stay
stuck ON. While it is stuck, tools that remap or capture keys (for example
Logitech Options+ with MX Keys) cannot see keystrokes, so Caps Lock and some
shortcuts appear dead.

The typical chain:

1. An app enables Secure Input for a password or licensing dialog.
2. The app crashes or does not release Secure Input properly.
3. macOS keeps Secure Input stuck ON.
4. Key-remapping software can no longer capture keystrokes, so Caps Lock stops
   working.
5. Other keyboard shortcuts also become unresponsive.

Apps commonly seen holding Secure Input include Microsoft Excel (password and
licensing prompts), password managers, VPN clients, and terminals prompting for
a password. This list is based on reports and observation, not a controlled
test.

## Ways to fix it

### Option 1: Ask Claude (with this skill installed)

Say something like `Check Secure Input` or `Caps Lock not working`. The skill's
Secure Input diagnostic reports whether Secure Input is stuck, which app (PID
and name) is holding it, and the commands to clear it.

### Option 2: Fish shell functions

Source `fish-caps-functions.fish` from your `~/.config/fish/config.fish`:

```fish
source /path/to/fish-caps-functions.fish
```

Then use:

```bash
caps-check    # diagnose
caps-fix      # attempt graceful, then force, kill of the offending PID
capsnow       # check, then prompt before fixing
```

### Option 3: Standalone bash script

```bash
chmod +x caps-lock-fix.sh
./caps-lock-fix.sh          # show diagnostic and suggested commands
./caps-lock-fix.sh --fix    # attempt to quit/kill the offending app
```

`--fix` tries a graceful quit first (AppleScript quit for known apps, otherwise
`kill -TERM`), waits, and only escalates to `kill -9` if Secure Input is still
stuck. Save your work in the offending app before running it.

### Option 4: Raw one-liner

Check only:

```bash
ioreg -l -d 1 -w 0 | grep SecureInput && echo "PID:" && \
  ioreg -l -d 1 -w 0 | grep SecureInput | \
  grep -o 'kCGSSessionSecureInputPID"=[0-9]*' | cut -d'=' -f2 | \
  xargs -I {} ps -p {} -o pid,comm,args
```

Diagnose and print the fix command:

```bash
secure_check=$(ioreg -l -d 1 -w 0 | grep SecureInput); \
if [ -z "$secure_check" ]; then echo "OFF"; else \
  pid=$(echo "$secure_check" | grep -o 'PID"=[0-9]*' | cut -d'=' -f2); \
  echo "STUCK - PID $pid:"; ps -p $pid -o comm,args | tail -1; \
  echo "Fix: kill $pid"; fi
```

## Prevention and monitoring

Watch Secure Input flip in real time while reproducing the issue:

```bash
watch -n 2 'ioreg -l -d 1 -w 0 | grep SecureInput'
```

Keeping the offending app and any key-remapping software up to date reduces how
often this happens:

```bash
# Check for macOS updates
softwareupdate -l
# App updates: use each app's own updater
```

## Escalation path (if the basic fix fails)

1. Run the script with `--fix` (handles graceful then force kill).
2. Force Quit the app from Activity Monitor by its PID.
3. Log out and back in, which resets Secure Input state by restarting
   WindowServer.
4. Reboot as a last resort.

## Verifying the fix

After quitting or killing the offending app:

```bash
ioreg -l -d 1 -w 0 | grep SecureInput
# No output means Secure Input is off (fixed).
```

Then test Caps Lock on the keyboard, confirm any key-remapping software no
longer shows a Secure Input warning, and test a few shortcuts.

## Limitations

- macOS only.
- The Secure Input PID is read from `ioreg`; on some macOS versions the field
  may be absent even when a stuck state is suspected, in which case the scripts
  report Secure Input as off and point you elsewhere (Bluetooth, key-remapping
  software, keyboard firmware).
- The scripts kill processes. They ask you to save work first, but a force kill
  (`kill -9`) can still lose unsaved state. Read what they print before letting
  them escalate.
