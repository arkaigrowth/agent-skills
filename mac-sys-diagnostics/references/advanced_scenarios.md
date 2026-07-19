# Advanced macOS Diagnostics Scenarios

Reference material for complex or edge-case system issues. Load this when basic diagnostics aren't sufficient.

## Table of Contents
1. Kernel Panics and System Crashes
2. Disk I/O Bottlenecks
3. Network-Related Process Hangs
4. launchd and System Service Issues
5. Code Signing and Security Framework Problems
6. Memory Pressure Crisis Management

---

## 1. Kernel Panics and System Crashes

### Post-Panic Analysis
```bash
# View recent kernel panic logs
log show --predicate 'eventMessage contains "panic"' --last 24h

# Detailed panic report (if system rebooted)
ls -lt /Library/Logs/DiagnosticReports/ | grep "Kernel" | head -5

# View specific panic report
cat /Library/Logs/DiagnosticReports/<panic_report_name>
```

### Common Panic Causes
- **3rd-party kernel extensions**: Check `kextstat | grep -v com.apple`
- **RAM issues**: Run Apple Diagnostics (hold D on boot)
- **Disk corruption**: `diskutil verifyVolume /`
- **Overheating**: Check `sudo powermetrics --samplers smc -n 1` for thermal state

---

## 2. Disk I/O Bottlenecks

Processes stuck in "D" state (uninterruptible sleep) often indicate disk I/O problems.

### I/O Performance Check
```bash
# Real-time I/O monitoring (requires sudo)
sudo fs_usage -w | head -100

# Identify processes causing I/O wait
iostat -w 5 -c 10

# Show disk utilization
iostat -d -x 5 3

# Detailed disk I/O per process
sudo iotop -P 5
```

### APFS-Specific Issues
```bash
# Check APFS snapshots (can consume space, cause slowness)
tmutil listlocalsnapshots /

# Delete a specific snapshot if needed (pass an exact date from the list above;
# these are Time Machine local snapshots, so only delete ones you can spare)
sudo tmutil deletelocalsnapshots <snapshot_date>

# Check APFS container status
diskutil apfs list

# Verify APFS volume
diskutil verifyVolume /
```

---

## 3. Network-Related Process Hangs

Processes stuck waiting on network I/O often show state "D" or high TIME without CPU activity.

### Network Diagnostics
```bash
# Show all network connections
lsof -i -n -P

# Connections in TIME_WAIT or CLOSE_WAIT (leak indicators)
netstat -an | grep -E "TIME_WAIT|CLOSE_WAIT" | wc -l

# Find process with most open connections
lsof -i -n | awk '{print $1}' | sort | uniq -c | sort -rn | head -10

# DNS resolution issues (check latency)
time nslookup google.com

# Network interface statistics
netstat -I en0 -b -w 5
```

### Stuck Network Process Recovery
```bash
# Flush DNS cache (often helps stuck DNS lookups)
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder

# Reset network stack (drastic, drops connectivity briefly)
sudo ifconfig en0 down && sudo ifconfig en0 up

# Check if mDNSResponder is hung (common issue)
ps aux | grep mDNSResponder | grep -v grep
# If CPU or memory high, restart:
sudo killall -HUP mDNSResponder
```

---

## 4. launchd and System Service Issues

launchd manages all macOS services. If a service respawns immediately after kill, launchd is restarting it.

### Service Management
```bash
# List all loaded services (system)
sudo launchctl list | grep -v "^-"

# List user services
launchctl list

# Show specific service status
launchctl list | grep <service_name>

# Unload service (stops auto-restart)
sudo launchctl unload /Library/LaunchDaemons/<service.plist>
# Or for user services:
launchctl unload ~/Library/LaunchAgents/<service.plist>

# Reload service
sudo launchctl load /Library/LaunchDaemons/<service.plist>

# View service logs
log show --predicate 'process == "<service_name>"' --last 1h
```

### Finding Service Plist Files
```bash
# System daemons (root-level)
ls /Library/LaunchDaemons/

# System agents (per-user)
ls /Library/LaunchAgents/

# User-specific agents
ls ~/Library/LaunchAgents/

# Apple system services
ls /System/Library/LaunchDaemons/
```

---

## 5. Code Signing and Security Framework Problems

macOS Gatekeeper and code signing can cause processes to hang during signature verification.

### Code Signing Checks
```bash
# Check if process has valid signature
codesign -vv /path/to/app

# View process security attributes
codesign -d --entitlements - /path/to/app

# Check Gatekeeper status
spctl --status

# Remove quarantine attribute (if safe to do so)
xattr -dr com.apple.quarantine /path/to/app

# View all extended attributes
xattr -l /path/to/app
```

### Security Framework Issues
```bash
# Check security daemon (securityd) status
ps aux | grep securityd | grep -v grep

# View security logs
log show --predicate 'subsystem == "com.apple.securityd"' --last 1h

# Keychain access issues (can cause hangs)
security list-keychains
security unlock-keychain ~/Library/Keychains/login.keychain-db
```

---

## 6. Memory Pressure Crisis Management

When memory pressure reaches critical levels, the system becomes unusable. Emergency procedures:

### Immediate Triage (When System Barely Responsive)
```bash
# STEP 1: See the top consumers and their PIDs. Always look before you kill.
ps aux | sort -k4 -r | head -5

# STEP 2: Decide which PID is safe to kill, then kill that specific PID.
# Do NOT blind-kill "whatever is on top": the top process may be a system
# process (WindowServer, kernel_task) or an app with unsaved work.
# Replace <pid> with a value you chose from STEP 1.
kill -TERM <pid>     # graceful first
# kill -9 <pid>      # force only if it ignores TERM

# Force memory purge (may help but causes an I/O spike)
sudo purge

# View swap usage (if high, memory is truly exhausted)
sysctl vm.swapusage
```

> **⚠️ Avoid the "kill the top process automatically" shortcut.** A one-liner
> that pipes `ps ... | awk '{print $2}'` straight into `kill -9` will happily
> terminate a critical system process or an app with unsaved work. Pick the PID
> by hand from STEP 1 instead.

### Preventing Cascading Failures
When one process consumes all memory, others start failing. Act quickly:

```bash
# 1. Kill largest non-essential process
# 2. Clear memory pressure:
sudo purge

# 3. Check if pressure subsides:
memory_pressure

# 4. If still critical, escalate to logout:
osascript -e 'tell application "System Events" to log out'
```

### Identifying Memory Leak Patterns
```bash
# Sample process memory over time (10 samples, 60s apart)
for i in {1..10}; do 
  echo "$(date): $(ps aux | grep <pid> | grep -v grep | awk '{print $6}')" >> mem_log.txt
  sleep 60
done
cat mem_log.txt

# Analyze heap allocations (requires Xcode tools)
leaks <pid>

# Sample process for heap growth
sample <pid> -file sample_output.txt
```

---

## Advanced Command Reference

### Watching Process State Changes
```bash
# Watch specific process continuously
watch -n 2 "ps aux | grep <process_name> | grep -v grep"

# Monitor multiple PIDs
watch -n 2 "ps -p <pid1>,<pid2>,<pid3> -o pid,ppid,state,pcpu,pmem,comm"
```

### Kernel Extension Issues
```bash
# List loaded kernel extensions
kextstat

# Find non-Apple kexts (3rd party, often problematic)
kextstat | grep -v com.apple

# Unload problematic kext (requires sudo, dangerous!)
sudo kextunload -b <bundle_id>

# View kext logs
log show --predicate 'subsystem == "com.apple.xpc.launchd.domain.system"' --last 1h | grep kext
```

### Activity Monitor Alternative (Terminal)
```bash
# Interactive top (press 'o' for options, 'q' to quit)
top -o mem

# Sort by CPU
top -o cpu

# Show only specific user processes
top -U <username>

# One-shot sorted output
top -l 1 -o mem -n 10
```

---

## Emergency Recovery Procedures

### When System is Frozen

1. **SSH from another machine** (if remote login enabled)
   ```bash
   ssh user@mac-hostname
   # Then run diagnostics remotely
   ```

2. **Single User Mode** (if no SSH):
   - Reboot holding Cmd+S
   - Run `fsck -fy` to repair disk
   - Run `mount -uw /` to enable write access
   - Manually kill processes: `kill -9 <pid>`

3. **Safe Mode** (if persistent issues):
   - Reboot holding Shift
   - Disables 3rd-party kernel extensions
   - Clears system caches
   - Runs fsck automatically

4. **Recovery Mode** (last resort):
   - Reboot holding Cmd+R
   - Use Disk Utility to repair disk
   - Can reinstall macOS if corrupted

---

## Performance Tuning Tips

### Reduce WindowServer Memory Bloat
```bash
# Disable transparency (reduces GPU load)
defaults write com.apple.universalaccess reduceTransparency -bool true

# Disable animations (reduces WindowServer work)
defaults write com.apple.dock launchanim -bool false

# Reduce Motion
defaults write com.apple.Accessibility ReduceMotionEnabled -int 1

# Restart Dock to apply
killall Dock
```

### Periodic Maintenance
```bash
# Run maintenance scripts manually (usually automated)
sudo periodic daily weekly monthly

# Rebuild Spotlight index (if searching slow)
sudo mdutil -E /
```

> **⚠️ Deleting system logs with `rm -rf` is risky and usually unnecessary.**
> macOS rotates `/var/log` on its own, and a mistyped glob here runs as root.
> If disk space in `/var/log` is genuinely the problem, first find the large
> files, then remove specific ones rather than globbing:
>
> ```bash
> # See what is actually large before deleting anything
> sudo du -sh /var/log/* 2>/dev/null | sort -h | tail -20
>
> # Prefer the built-in log store trim over rm -rf:
> sudo log erase --all        # clears the unified log store
> ```

---

**Use these advanced techniques only when standard diagnostics don't reveal the issue or when dealing with critical system states.**
