---
name: mac-sys-diagnostics
description: macOS system diagnostics for memory leaks, zombie processes, MCP server issues, WindowServer problems, and Secure Input keyboard issues (Caps Lock failures). Use when user reports system slowness, high memory usage, zombie processes, keyboard malfunctions, or requests system health checks. Provides copy-paste command blocks with clear sections for progressive diagnosis and remediation.
---

# macOS System Diagnostics

A security-conscious diagnostic reference for identifying and resolving memory leaks, zombie processes, and system performance issues on macOS.

> **What this is (and is not):** This skill is a curated collection of
> read-only diagnostic command blocks plus two small helper wrappers for the
> Secure Input / Caps Lock workflow. It is a command reference and a set of
> wrappers, not a packaged, automated, or independently tested tool. The
> commands are standard macOS utilities (`ps`, `ioreg`, `vm_stat`, `lsof`,
> `launchctl`, and similar). Read each block before running it, and treat every
> command that kills processes or deletes files as something you confirm
> yourself. macOS only.

## When to Use This Skill

- User reports system slowness or high memory usage
- Zombie processes suspected (especially MCP servers)
- WindowServer consuming excessive resources
- **Keyboard issues: Caps Lock not working, shortcuts dead, Logitech Options+ warnings**
- Need to identify memory leaks or process bottlenecks
- Post-mortem analysis of system crashes or hangs
- Routine system health checks

## Diagnostic Philosophy

This skill provides **progressive diagnosis**: start with quick triage, then drill down into specific problem areas. Each command block is:
- **Single-block executable**: Copy/paste entire section for comprehensive output
- **Sectioned with comments**: Grab just the parts you need
- **Security-conscious**: No destructive operations without explicit user confirmation
- **Output-optimized**: Designed for readability and actionable insights

## Helper Tools (Optional)

For quick command-line access without Claude, standalone scripts are available:
- **`caps-lock-fix.sh`** - Secure Input diagnostic with `--fix` auto-mode (bash)
- **`fish-caps-functions.fish`** - Fish shell functions: `caps-check`, `caps-fix`, `capsnow`
- **`CAPS_LOCK_FIX_SUMMARY.md`** - Complete documentation and usage guide

These implement the Secure Input diagnostic workflow (see below) for rapid troubleshooting.

## Quick Triage

Start here. This gives you a system health snapshot: top memory hogs, zombie process count, WindowServer status, and active MCP servers. It is read-only.

```bash
echo "=== SYSTEM HEALTH SNAPSHOT ===" && \
echo "" && \
echo "📊 Top 10 Memory Consumers:" && \
ps aux | sort -k4 -r | head -11 | awk 'NR==1 || NR>1 {printf "%-20s %8s %8s %s\n", substr($1,1,20), $3"%", $4"%", $11}' && \
echo "" && \
echo "🧟 Zombie Process Count:" && \
ps aux | awk '$8=="Z" {count++} END {print (count ? count " zombie(s) detected ⚠️" : "No zombies detected ✅")}' && \
echo "" && \
echo "🪟 WindowServer Status:" && \
ps aux | grep -i windowserver | grep -v grep | awk '{printf "CPU: %s%% | Memory: %s%% | PID: %s\n", $3, $4, $2}' && \
echo "" && \
echo "🤖 Active MCP Servers:" && \
ps aux | grep -i mcp | grep -v grep | wc -l | awk '{print $1 " MCP process(es) running"}' && \
echo "" && \
echo "💾 Memory Pressure:" && \
memory_pressure && \
echo "" && \
echo "⏱️  System Uptime:" && \
uptime
```

**What to look for:**
- Memory % > 80%: Investigate those processes
- Zombie count > 0: Run "Zombie Process Hunter"
- WindowServer > 1GB (10%+ on 16GB system): Run "WindowServer Deep Dive"
- Memory pressure = "warn" or "critical": Immediate action needed
- Many MCP processes: Run "MCP Diagnostics"

## Memory Deep Dive

Identifies memory leaks, tracks memory growth over time, and shows detailed memory attribution.

### Option A: Real-time Memory Monitoring (60s sample)
Watch memory consumption in real-time to catch growing processes:

```bash
echo "=== REAL-TIME MEMORY MONITOR (60s) ===" && \
echo "Sampling every 5s to detect memory growth..." && \
echo "" && \
for i in {1..12}; do
  echo "Sample $i/12 ($(date +%H:%M:%S)):" && \
  ps aux | sort -k4 -r | head -6 | awk 'NR>1 {printf "  %-25s %8s %8s MB | PID: %s\n", substr($11,1,25), $4"%", int($6/1024), $2}' && \
  [ $i -lt 12 ] && sleep 5
done && \
echo "" && \
echo "✅ Monitoring complete. Look for processes with increasing memory."
```

### Option B: Memory Leak Suspects
Processes with unusually high memory growth patterns:

```bash
echo "=== MEMORY LEAK SUSPECTS ===" && \
echo "" && \
echo "📈 Processes with >1GB memory (leak candidates):" && \
ps aux | awk '$6 > 1048576 {printf "%-30s %10.2f GB | CPU: %s%% | PID: %s\n", substr($11,1,30), $6/1048576, $3, $2}' && \
echo "" && \
echo "🔍 Process Tree (helps identify parent/child leaks):" && \
ps axjf | grep -v grep | head -30 && \
echo "" && \
echo "💾 Detailed Memory Regions (system-wide):" && \
vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages\s+([^:]+)[^\d]+(\d+)/ and printf("%-20s %10.2f MB\n", "$1:", $2 * $size / 1048576);'
```

**What to look for:**
- Same process appearing repeatedly with increasing memory
- Processes > 2GB that aren't expected (browsers, IDEs OK)
- "Pages wired down" or "Pages active" growing disproportionately

## Process Inspector

Comprehensive process analysis: hung processes, high CPU, orphaned children, and process trees.

```bash
echo "=== PROCESS DEEP DIVE ===" && \
echo "" && \
echo "🔥 High CPU Consumers (>20%):" && \
ps aux | awk '$3 > 20 {printf "%-25s CPU: %s%% | MEM: %s%% | PID: %s | TIME: %s\n", substr($11,1,25), $3, $4, $2, $10}' && \
echo "" && \
echo "😴 Hung/Stuck Processes (state = U):" && \
ps aux | awk '$8 ~ /U/ {printf "%-25s State: %s | PID: %s | Started: %s\n", substr($11,1,25), $8, $2, $9}' && \
echo "" && \
echo "👶 Orphaned Children (PPID = 1):" && \
ps -eo pid,ppid,comm,state | awk '$2 == 1 && NR > 1 {printf "PID: %-8s Parent: %-8s State: %s | %s\n", $1, $2, $4, $3}' && \
echo "" && \
echo "🌳 Full Process Tree (snippet):" && \
pstree -p | head -40 && \
echo "" && \
echo "⚡ Process States Legend:" && \
echo "  R = Running | S = Sleeping | U = Uninterruptible wait (STUCK)" && \
echo "  Z = Zombie  | T = Stopped   | I = Idle"
```

**What to look for:**
- State "U" (uninterruptible): Indicates kernel-level hang, often I/O related
- State "Z" (zombie): Dead process waiting for parent to collect exit status
- High CPU + old start time: Runaway process
- Many orphans: Parent crashed, children need cleanup

## Zombie Process Hunter

Specialized zombie detection and remediation. Zombies can't be killed directly; you must kill their parent.

```bash
echo "=== ZOMBIE PROCESS HUNTER 🧟 ===" && \
echo "" && \
zombies=$(ps aux | awk '$8=="Z" {print $2}') && \
if [ -z "$zombies" ]; then
  echo "✅ No zombies detected. System clean."
else
  echo "⚠️  Zombies detected! Details:" && \
  echo "" && \
  for zpid in $zombies; do
    echo "Zombie PID: $zpid" && \
    ps -o pid,ppid,comm,state,etime -p $zpid 2>/dev/null | tail -1 | \
      awk '{printf "  Parent PID: %s | Command: %s | Alive for: %s\n", $2, $3, $5}' && \
    ppid=$(ps -o ppid= -p $zpid 2>/dev/null | tr -d ' ') && \
    if [ -n "$ppid" ]; then
      ps -o pid,comm,state -p $ppid 2>/dev/null | tail -1 | \
        awk '{printf "  Parent details: PID=%s | Command=%s | State=%s\n", $1, $2, $3}'
    fi && \
    echo ""
  done && \
  echo "📋 Remediation:" && \
  echo "  1. Identify the parent process (PPID above)" && \
  echo "  2. Graceful kill: kill -TERM <parent_pid>" && \
  echo "  3. Force kill (if needed): kill -9 <parent_pid>" && \
  echo "  4. Parent will reap zombie on exit" && \
  echo "" && \
  echo "⚠️  WARNING: Killing parent process will terminate ALL its children!"
fi
```

**Zombie remediation flow:**
1. Note the parent PID (PPID)
2. Try graceful: `kill -TERM <ppid>` (give it 10s)
3. If still there: `kill -9 <ppid>` (force kill, last resort)
4. Verify with quick triage

## MCP Server Diagnostics

Specialized checks for Model Context Protocol servers, a common source of zombie processes and port conflicts.

```bash
echo "=== MCP SERVER DIAGNOSTICS 🤖 ===" && \
echo "" && \
echo "🔍 All MCP-related processes:" && \
ps aux | grep -i mcp | grep -v grep | \
  awk '{printf "%-30s CPU: %3s%% | MEM: %4s%% | PID: %-6s | %s\n", substr($11,1,30), $3, $4, $2, $10}' && \
echo "" && \
echo "🧟 Zombie MCP processes:" && \
ps aux | grep -i mcp | grep -v grep | awk '$8=="Z" {print "  ⚠️  Zombie MCP found: PID " $2}' && \
ps aux | grep -i mcp | grep -v grep | awk '$8=="Z"' | wc -l | \
  awk '{if ($1 == 0) print "  ✅ No zombie MCP processes"}' && \
echo "" && \
echo "🔌 Port bindings (MCP typically uses 3000-9000):" && \
lsof -iTCP:3000-9000 -sTCP:LISTEN 2>/dev/null | \
  awk 'NR==1 || /mcp/i {print}' && \
echo "" && \
echo "🌳 MCP Process Tree:" && \
ps aux | grep -i mcp | grep -v grep | awk '{print $2}' | \
  xargs -I {} pstree -p {} 2>/dev/null && \
echo "" && \
echo "📊 MCP Process States:" && \
ps aux | grep -i mcp | grep -v grep | awk '{states[$8]++} END {for (s in states) printf "  %s: %d process(es)\n", s, states[s]}'
```

**MCP-specific issues:**
- **Zombie MCP**: Parent MCP orchestrator likely crashed, so kill the parent PID
- **Port conflicts**: Multiple MCPs on same port, kill the older process
- **State "D" (disk wait)**: MCP stuck on I/O, check disk health
- **Multiple instances**: May indicate failed restarts, kill all and restart cleanly

**Safe MCP restart:**
```bash
# Kill all MCP processes gracefully
pkill -TERM -i mcp
sleep 5
# Force kill any remaining
pkill -9 -i mcp
# Verify clean
ps aux | grep -i mcp | grep -v grep
```

## WindowServer Deep Dive

macOS window manager, notorious for memory bloat, especially with multiple displays or long uptimes.

```bash
echo "=== WINDOWSERVER ANALYSIS 🪟 ===" && \
echo "" && \
echo "📊 WindowServer Stats:" && \
ps aux | grep -i windowserver | grep -v grep | \
  awk '{printf "CPU: %5s%% | Memory: %5s%% (%d MB) | PID: %s | Uptime: %s\n", $3, $4, int($6/1024), $2, $10}' && \
echo "" && \
echo "🖥️  Display Configuration:" && \
system_profiler SPDisplaysDataType 2>/dev/null | grep -E "Resolution:|Display Type:" | head -10 && \
echo "" && \
echo "🎨 Graphics Card Memory Pressure:" && \
ioreg -l -w0 | grep \"PerformanceStatistics\" | head -1 | sed 's/[^{]*//g' | \
  python3 -c "import sys, json; data=json.load(sys.stdin); print(f\"  VRAM Used: {data.get('vramUsedBytes', 0)/1048576:.0f} MB\")" 2>/dev/null || echo "  (Unable to read VRAM stats)" && \
echo "" && \
echo "🪟 WindowServer Open Files:" && \
lsof -p $(ps aux | grep -i windowserver | grep -v grep | awk '{print $2}') 2>/dev/null | wc -l | \
  awk '{printf "  %d open file handles\n", $1}' && \
echo "" && \
echo "⚠️  Known WindowServer Issues:" && \
echo "  - Memory grows with display count/resolution" && \
echo "  - Doesn't release memory after closing windows" && \
echo "  - Can leak with external displays hot-plugging" && \
echo "" && \
echo "💡 Remediation Severity:" && \
mem=$(ps aux | grep -i windowserver | grep -v grep | awk '{print $4}') && \
mem_int=$(echo $mem | cut -d'.' -f1) && \
if [ "$mem_int" -lt 5 ]; then
  echo "  ✅ <5% memory: Normal operation"
elif [ "$mem_int" -lt 10 ]; then
  echo "  ⚠️  5-10% memory: Monitor, consider restart if persistent"
elif [ "$mem_int" -lt 20 ]; then
  echo "  🔴 10-20% memory: Recommend logout/login to restart WindowServer"
else
  echo "  🚨 >20% memory: URGENT - Restart WindowServer immediately"
fi
```

**WindowServer restart options (increasing severity):**

```bash
# Option 1: Log out/in (safest, full cleanup)
# Save work first! Closes all apps.
osascript -e 'tell application "System Events" to log out'

# Option 2: Kill WindowServer (forces logout)
# ⚠️ DANGER: This force-logs-out immediately with NO save prompts.
# Any unsaved work in any open app is lost. Prefer Option 1 (log out/in),
# which does the same cleanup while letting apps prompt you to save.
# Only run this if the system is already unusable and Option 1 will not run.
sudo killall -9 WindowServer

# Option 3: Disable/re-enable displays (doesn't kill WindowServer)
# Experimental - may reduce memory without logout
# (No reliable command - use System Preferences → Displays)
```

**⚠️ SECURITY NOTE:** Option 2 requires sudo and immediately logs you out. Only use when >20% memory or system unusable.

## Secure Input Diagnostic (Caps Lock / Keyboard Issues)

macOS Secure Input mode can get stuck, blocking keyboard shortcuts and causing Caps Lock failures, especially with Logitech MX Keys and Microsoft Excel.

**Symptoms:**
- Caps Lock stops working
- Logitech Options+ warns: "Secure input for [App] may prevent your device from functioning properly"
- Keyboard shortcuts feel dead or inconsistent

**Quick Access Tools:**
- Standalone script: `caps-lock-fix.sh` (bash, portable, includes `--fix` auto-mode)
- Fish functions: `fish-caps-functions.fish` (add to config.fish for `caps-check` and `caps-fix` commands)
- Full docs: `CAPS_LOCK_FIX_SUMMARY.md`

These helper scripts implement the diagnostic workflow below for quick command-line access.

```bash
echo "=== SECURE INPUT DIAGNOSTIC 🔐 ===" && \
echo "" && \
echo "🔍 Checking Secure Input state..." && \
secure_check=$(ioreg -l -d 1 -w 0 | grep SecureInput) && \
if [ -z "$secure_check" ]; then
  echo "✅ Secure Input is OFF (normal state)"
  echo "   Issue likely elsewhere (Bluetooth, Logi app, keyboard firmware)"
else
  echo "⚠️  Secure Input is ENABLED (stuck ON)" && \
  echo "$secure_check" && \
  echo "" && \
  pid=$(echo "$secure_check" | grep -o 'kCGSSessionSecureInputPID"=[0-9]*' | cut -d'=' -f2) && \
  if [ -n "$pid" ]; then
    echo "🎯 Offending process:" && \
    ps -p $pid -o pid,comm,args | tail -1 && \
    echo "" && \
    echo "📋 Fix Process:" && \
    echo "  1. Save work in this app: $(ps -p $pid -o comm= | xargs basename)" && \
    echo "  2. Quit the app gracefully (Cmd+Q)" && \
    echo "  3. If it won't quit, run: kill $pid" && \
    echo "  4. Last resort: kill -9 $pid" && \
    echo "  5. Verify with: ioreg -l -d 1 -w 0 | grep SecureInput" && \
    echo "" && \
    echo "🔄 Common culprits: Microsoft Excel, 1Password, password managers, VPN apps"
  fi
fi
```

### Quick Fix Script

If you already know the PID from above diagnostic:

```bash
# Replace NNNNN with the PID from diagnostic
PID=NNNNN

# Graceful quit (try this first)
kill -TERM $PID
sleep 5

# Check if cleared
if ioreg -l -d 1 -w 0 | grep -q SecureInput; then
  echo "⚠️  Still stuck. Trying force kill..."
  kill -9 $PID
  sleep 2
  if ioreg -l -d 1 -w 0 | grep -q SecureInput; then
    echo "🚨 Still stuck! Try quitting app manually or reboot."
  else
    echo "✅ Secure Input cleared! Test Caps Lock now."
  fi
else
  echo "✅ Secure Input cleared! Test Caps Lock now."
fi
```

### App-Specific Quit Commands

For apps that won't respond to standard kill signals:

```bash
# Microsoft Excel (most common offender)
osascript -e 'tell application "Microsoft Excel" to quit'

# 1Password
osascript -e 'tell application "1Password 7" to quit'

# iTerm2 (if it gets stuck)
osascript -e 'tell application "iTerm" to quit'

# Generic approach for any app
# Replace "AppName" with exact app name from diagnostic
osascript -e 'tell application "AppName" to quit'
```

### Prevention & Recurrence Handling

If this keeps happening:

```bash
# Update the offending app (example: Excel)
# Go to Help → Check for Updates in the app

# Update Logitech Options+ (if using MX Keys)
# Check /Applications/Logi Options+.app → About

# Check for macOS updates
softwareupdate -l

# Monitor Secure Input in real-time (for debugging)
watch -n 2 'ioreg -l -d 1 -w 0 | grep SecureInput'
```

**Common triggers:**
- Password/authentication dialogs (Excel licensing, VBA macros)
- App crashes during password entry
- VPN connections/disconnections
- Screen sharing sessions (Zoom, Teams)
- Certain Excel add-ins (Power Query, Data Analysis)

**Quick recovery routine:**
1. Run Secure Input diagnostic (above)
2. Note the PID
3. Quit that app
4. Verify cleared
5. Test Caps Lock

## Safe Termination Guide

How to kill processes responsibly, minimizing data loss and corruption.

### Termination Hierarchy (Always follow this order)

```bash
# 1. GRACEFUL SHUTDOWN (SIGTERM = signal 15)
#    Process receives shutdown signal, cleans up, saves state
#    Wait 10-30 seconds for process to exit
kill -TERM <pid>
# Or by name:
pkill -TERM <process_name>

# 2. INTERRUPT (SIGINT = signal 2) 
#    Like Ctrl+C - interrupts but allows cleanup
#    Use if SIGTERM ignored after 30s
kill -INT <pid>

# 3. QUIT WITH CORE DUMP (SIGQUIT = signal 3)
#    Forces quit + generates core dump for debugging
#    Use if you need crash diagnostics
kill -QUIT <pid>

# 4. FORCE KILL (SIGKILL = signal 9) - LAST RESORT
#    Immediate termination, NO cleanup
#    ⚠️ Can cause data loss, corruption, zombie children
kill -9 <pid>
# Or:
pkill -9 <process_name>
```

### Before Force-Killing (SIGKILL), ask:

1. **Data loss?** Process may have unsaved state
2. **Child processes?** They may become orphans/zombies
3. **Shared resources?** Locks/files may not release cleanly
4. **System process?** May auto-restart or cause instability

### Recovery After Force Kill

```bash
echo "=== POST-FORCE-KILL CLEANUP ===" && \
echo "" && \
echo "🧟 New zombies created?" && \
ps aux | awk '$8=="Z"' && \
echo "" && \
echo "🔒 Stale locks (common in /tmp and /var):" && \
find /tmp -name "*.lock" -mmin +60 2>/dev/null | head -10 && \
echo "" && \
echo "🧹 Orphaned children?" && \
ps -eo pid,ppid,comm,state | awk '$2 == 1 && NR > 1' | head -10
```

## System Recovery Procedures

When things go sideways, here's your escalation path.

### Level 1: Process Restart
Try restart before killing:
```bash
# For launchd-managed services:
sudo launchctl kickstart -k system/<service_name>

# For user processes:
pkill -HUP <process_name>  # Asks process to reload config
```

### Level 2: User-Space Reset
Logout/login to restart WindowServer and user processes without full reboot:
```bash
osascript -e 'tell application "System Events" to log out'
```

### Level 3: Clear Caches

Stale caches can occasionally cause performance issues, but cache deletion is
rarely the right first step and a bad path can remove data you wanted to keep.
Try the safer options first.

**Safer alternatives (do these first):**
```bash
# Reboot first: macOS clears many volatile caches on restart, with no risk.
# Quit and reopen the specific misbehaving app before touching caches at all.

# Inspect which caches are large before deleting anything:
du -sh ~/Library/Caches/* 2>/dev/null | sort -h | tail -20

# Remove ONE named app cache (targeted, reversible on next app launch).
# Replace com.example.app with the bundle id you identified above.
rm -rf "$HOME/Library/Caches/com.example.app"
```

> **⚠️ DANGER: bulk cache deletion.** The commands below delete whole cache
> trees with `rm -rf`. There is no undo. A typo or an unexpected symlink in one
> of these paths can delete far more than intended.
>
> - Do NOT delete `/System/Library/Caches`. It is owned by the OS, and removing
>   it can leave the system in a broken state. There is no safe reason to do
>   this on a normal machine.
> - Only clear the user cache in bulk if a targeted removal did not help and you
>   understand you are discarding rebuildable app state.
> - Close your apps first, and quote `$HOME` so the path can never expand to `/`.
>
> ```bash
> # User caches only. Review the du -sh output above before running this.
> rm -rf "$HOME/Library/Caches/"*
> ```

### Level 4: Full Reboot
When nothing else works:
```bash
# Graceful reboot (allows save prompts)
sudo shutdown -r now

# Force reboot (emergency only)
sudo shutdown -r -f now
```

## Quick Reference: Command Snippets

Copy these standalone commands for rapid diagnosis:

```bash
# Show top 5 memory hogs
ps aux | sort -k4 -r | head -6 | awk '{printf "%-25s %s%%\n", substr($11,1,25), $4}'

# Count zombies
ps aux | awk '$8=="Z"' | wc -l

# Check Secure Input (Caps Lock issues)
ioreg -l -d 1 -w 0 | grep SecureInput

# Find process by name
ps aux | grep <name> | grep -v grep

# Show process tree for PID
pstree -p <pid>

# Memory pressure check
memory_pressure | grep "System-wide"

# Kill process by name (graceful)
pkill -TERM <name>

# List all listening ports
lsof -iTCP -sTCP:LISTEN -n -P

# Show process CPU history
top -pid <pid> -stats pid,cpu,mem,time

# Real-time system monitor
sudo fs_usage -f filesys | grep <process_name>
```

## Best Practices

1. **Always triage first** - Run "Quick Triage" before deep dives
2. **Graceful before forceful** - Try SIGTERM before SIGKILL
3. **Document PIDs** - Note PIDs before killing for post-mortem
4. **Check children** - Use `pstree -p <pid>` before killing parents
5. **Monitor after changes** - Re-run triage after terminations
6. **Restart over kill** - Prefer service restarts to force kills
7. **Security conscious** - Avoid `sudo kill -9` on system processes

## Troubleshooting

**"Operation not permitted"**: Process owned by root or system, needs `sudo`

**"No such process"**: Process exited between listing and kill command

**"Kill doesn't work"**: Process stuck in kernel (state "D"), usually I/O wait, must resolve the underlying issue (disk, network)

**"Zombies won't die"**: Zombies can't be killed directly, must kill parent

**"Process respawns immediately"**: Managed by launchd, use `launchctl` to stop service

---

**Remember:** Diagnosis before destruction. Understand before you terminate. Graceful before forceful.
