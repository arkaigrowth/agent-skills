#!/bin/bash
# Caps Lock / Secure Input Quick Diagnostic & Fix
# Usage: ./caps-lock-fix.sh [--fix PID]

set -e

echo "🔐 Checking Secure Input state..."
echo ""

secure_check=$(ioreg -l -d 1 -w 0 | grep SecureInput 2>/dev/null || echo "")

if [ -z "$secure_check" ]; then
    echo "✅ Secure Input is OFF (normal state)"
    echo ""
    echo "Caps Lock issue likely elsewhere:"
    echo "  • Check Bluetooth connection (Settings → Bluetooth)"
    echo "  • Restart Logitech Options+ if using MX Keys"
    echo "  • Try different USB port (if wired keyboard)"
    echo "  • Check keyboard battery"
    exit 0
fi

echo "⚠️  Secure Input is STUCK ON!"
echo ""
echo "Raw output:"
echo "$secure_check"
echo ""

pid=$(echo "$secure_check" | grep -o 'kCGSSessionSecureInputPID"=[0-9]*' | cut -d'=' -f2)

if [ -z "$pid" ]; then
    echo "❌ Could not extract PID from Secure Input check"
    exit 1
fi

echo "🎯 Offending process (PID: $pid):"
ps -p "$pid" -o pid,comm,args 2>/dev/null | tail -1
echo ""

app_name=$(ps -p "$pid" -o comm= 2>/dev/null | xargs basename)

# Auto-fix mode
if [ "$1" = "--fix" ]; then
    echo "🔧 AUTO-FIX MODE"
    echo ""
    echo "Attempting graceful quit of $app_name..."
    
    # Try AppleScript quit first
    if [[ "$app_name" == *"Excel"* ]]; then
        osascript -e 'tell application "Microsoft Excel" to quit' 2>/dev/null || true
    elif [[ "$app_name" == *"1Password"* ]]; then
        osascript -e 'tell application "1Password 7" to quit' 2>/dev/null || true
    else
        # Try generic kill
        kill -TERM "$pid" 2>/dev/null || true
    fi
    
    echo "Waiting 5 seconds..."
    sleep 5
    
    # Check if cleared
    if ioreg -l -d 1 -w 0 | grep -q SecureInput 2>/dev/null; then
        echo "⚠️  Still stuck. Trying force kill..."
        kill -9 "$pid" 2>/dev/null || true
        sleep 2
        
        if ioreg -l -d 1 -w 0 | grep -q SecureInput 2>/dev/null; then
            echo "🚨 Still stuck! Manual intervention needed:"
            echo "  1. Force quit the app from Activity Monitor"
            echo "  2. Or reboot your Mac"
        else
            echo "✅ Secure Input cleared! Test Caps Lock now."
        fi
    else
        echo "✅ Secure Input cleared! Test Caps Lock now."
    fi
    
    exit 0
fi

# Manual mode - just show instructions
echo "📋 Fix Process:"
echo ""
echo "  1. Save your work in: $app_name"
echo "  2. Quit the app (Cmd+Q)"
echo ""
echo "  OR run this script with --fix to auto-kill:"
echo "     ./caps-lock-fix.sh --fix"
echo ""
echo "  Manual kill commands:"
echo "     kill -TERM $pid    # Graceful"
echo "     kill -9 $pid       # Force (last resort)"
echo ""
echo "  Verify fix worked:"
echo "     ioreg -l -d 1 -w 0 | grep SecureInput"
echo "     (No output = success)"
echo ""
echo "🔄 Common culprits:"
echo "   • Microsoft Excel (password/licensing dialogs)"
echo "   • 1Password (vault unlock)"
echo "   • VPN apps (auth prompts)"
echo "   • Terminal apps with password entry"
