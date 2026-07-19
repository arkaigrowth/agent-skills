#!/usr/bin/env bash
# =============================================================================
# Smoke test for repo-security-scan
# =============================================================================
# Runs a Tier 1 JSON scan against the committed known-clean fixture and asserts:
#   1. exit code is 0 (CLEAN verdict)
#   2. the JSON output has the expected verdict shape
#
# The scan degrades gracefully: with zero scanners installed it still produces
# valid JSON and a CLEAN verdict for a clean directory, so this test does not
# depend on any optional scanner being present. It does require bash and
# python3 (used only to validate the JSON shape).
# =============================================================================

set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCANNER="$TEST_DIR/../scripts/repo-security-scan.sh"
FIXTURE="$TEST_DIR/fixtures/clean-sample"

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }

[[ -f "$SCANNER" ]] || fail "scanner not found at $SCANNER"
[[ -d "$FIXTURE" ]] || fail "fixture not found at $FIXTURE"
command -v python3 >/dev/null 2>&1 || fail "python3 is required to run this test"

echo "Running Tier 1 scan against clean-sample fixture..."

# Capture stdout (JSON) and the verdict exit code separately.
OUTPUT="$(bash "$SCANNER" --tier 1 --json --no-report --quiet "$FIXTURE" 2>/dev/null)"
CODE=$?

# Assertion 1: exit code 0 means CLEAN verdict.
if [[ $CODE -ne 0 ]]; then
    fail "expected exit code 0 (CLEAN), got $CODE"
fi
echo "  OK: exit code is 0"

# Assertion 2: JSON shape. python3 validates structure and key values.
printf '%s' "$OUTPUT" | python3 -c '
import json, sys

try:
    data = json.load(sys.stdin)
except Exception as exc:
    print(f"invalid JSON: {exc}", file=sys.stderr)
    sys.exit(1)

errors = []

verdict = data.get("verdict")
if verdict != "CLEAN":
    errors.append("verdict expected CLEAN, got {!r}".format(verdict))

score = data.get("score")
if not isinstance(score, int):
    errors.append("score is not an integer: {!r}".format(score))
elif score < 80:
    errors.append("score below CLEAN threshold: {}".format(score))

tier = data.get("tier")
if tier != 1:
    errors.append("tier expected 1, got {!r}".format(tier))

if not isinstance(data.get("findings"), list):
    errors.append("findings is not a list")

summary = data.get("summary")
if not isinstance(summary, dict):
    errors.append("summary is not an object")
else:
    for key in ("critical", "high", "medium", "low", "info", "errors"):
        if key not in summary:
            errors.append("summary missing key: " + key)

for key in ("version", "timestamp", "repo_name", "ecosystems", "tools_used"):
    if key not in data:
        errors.append("top-level key missing: " + key)

if errors:
    for e in errors:
        print("  assertion failed: " + e, file=sys.stderr)
    sys.exit(1)

print("  OK: JSON verdict shape valid (verdict=CLEAN, score={})".format(score))
' || fail "JSON shape assertions failed"

echo "PASS: smoke test succeeded"
