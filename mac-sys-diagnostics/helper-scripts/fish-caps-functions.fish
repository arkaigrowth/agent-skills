# Add this to your ~/.config/fish/config.fish

# Quick Caps Lock / Secure Input diagnostic
function caps-check
    echo "🔐 Checking Secure Input..."
    set secure_check (ioreg -l -d 1 -w 0 | grep SecureInput)
    
    if test -z "$secure_check"
        echo "✅ Secure Input OFF (normal)"
        return 0
    end
    
    echo "⚠️  Secure Input STUCK ON"
    echo $secure_check
    
    set pid (echo $secure_check | grep -o 'kCGSSessionSecureInputPID"=[0-9]*' | cut -d'=' -f2)
    
    if test -n "$pid"
        echo ""
        echo "🎯 Offending process:"
        ps -p $pid -o pid,comm,args | tail -1
        echo ""
        echo "Quick fix: kill $pid"
    end
end

# Auto-fix Caps Lock (kills the offending process)
function caps-fix
    set secure_check (ioreg -l -d 1 -w 0 | grep SecureInput)
    
    if test -z "$secure_check"
        echo "✅ Secure Input already off!"
        return 0
    end
    
    set pid (echo $secure_check | grep -o 'kCGSSessionSecureInputPID"=[0-9]*' | cut -d'=' -f2)
    
    if test -z "$pid"
        echo "❌ Could not find PID"
        return 1
    end
    
    set app_name (ps -p $pid -o comm= | xargs basename)
    echo "🔧 Killing $app_name (PID: $pid)..."
    
    # Try graceful first
    kill -TERM $pid 2>/dev/null
    sleep 3
    
    # Check if cleared
    if ioreg -l -d 1 -w 0 | grep -q SecureInput
        echo "⚠️  Still stuck, force killing..."
        kill -9 $pid 2>/dev/null
        sleep 1
    end
    
    # Final check
    if ioreg -l -d 1 -w 0 | grep -q SecureInput
        echo "🚨 Still stuck! Reboot needed."
        return 1
    else
        echo "✅ Fixed! Test Caps Lock now."
        return 0
    end
end

# One-liner that checks and fixes in one go
alias capsnow="caps-check && read -P '🔧 Auto-fix? [y/n]: ' -n 1 response; and if test \$response = y; caps-fix; end"
