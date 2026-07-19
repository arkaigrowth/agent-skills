#!/usr/bin/env bash
# Smoke tests for mac-sys-diagnostics.
# These do NOT run any diagnostic or fix: nothing is killed or deleted.
# They check that the shipped scripts parse and that SKILL.md has frontmatter.

set -u

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0
pass=0

check() {
    # check <description> <exit-status>
    if [ "$2" -eq 0 ]; then
        echo "ok   - $1"
        pass=$((pass + 1))
    else
        echo "FAIL - $1"
        fail=$((fail + 1))
    fi
}

# 1. bash script parses
bash -n "$here/helper-scripts/caps-lock-fix.sh"
check "caps-lock-fix.sh parses under bash -n" "$?"

# 2. fish functions parse (skip if fish is not installed)
if command -v fish >/dev/null 2>&1; then
    fish -n "$here/helper-scripts/fish-caps-functions.fish"
    check "fish-caps-functions.fish parses under fish -n" "$?"
else
    echo "skip - fish not installed, skipping fish -n check"
fi

# 3. SKILL.md frontmatter present with name and description
skill="$here/SKILL.md"
if [ -f "$skill" ] \
   && [ "$(head -1 "$skill")" = "---" ] \
   && grep -q '^name:' "$skill" \
   && grep -q '^description:' "$skill"; then
    check "SKILL.md has frontmatter with name and description" 0
else
    check "SKILL.md has frontmatter with name and description" 1
fi

echo ""
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
