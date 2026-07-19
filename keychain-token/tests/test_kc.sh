#!/usr/bin/env bash
#
# Test the kc-store / kc-get exit-code contract and a real round trip.
#
# The round-trip tests use a throwaway keychain (KC_KEYCHAIN) so they never
# touch your login keychain. Requires macOS `security`.
set -u

ROOT=$(cd "$(dirname "$0")/.." && pwd)
KC_STORE="$ROOT/scripts/kc-store"
KC_GET="$ROOT/scripts/kc-get"

pass=0
fail=0
check() { # description expected actual
  if [ "$2" = "$3" ]; then
    pass=$((pass + 1))
    echo "ok   - $1"
  else
    fail=$((fail + 1))
    echo "FAIL - $1 (expected '$2', got '$3')"
  fi
}

# --- Contract tests that need no keychain -----------------------------------

printf 'x' | "$KC_STORE" >/dev/null 2>&1
check "kc-store with no args -> 2" 2 $?

printf '' | "$KC_STORE" nm acct kind >/dev/null 2>&1
check "kc-store with empty secret -> 2" 2 $?

"$KC_GET" >/dev/null 2>&1
check "kc-get with no args -> 2" 2 $?

# --- Round trip against a throwaway keychain --------------------------------

if ! command -v security >/dev/null 2>&1; then
  echo "skip - round trip (no 'security'; not macOS)"
  echo "----"
  echo "$pass passed, $fail failed"
  [ "$fail" -eq 0 ]
  exit $?
fi

TMPKC="${TMPDIR:-/tmp}/kc-test-$$.keychain"
security create-keychain -p "" "$TMPKC" >/dev/null 2>&1
security unlock-keychain -p "" "$TMPKC" >/dev/null 2>&1
export KC_KEYCHAIN="$TMPKC"

cleanup() {
  security delete-keychain "$TMPKC" >/dev/null 2>&1 || true
  rm -f "$TMPKC" "$TMPKC-db" 2>/dev/null || true
}
trap cleanup EXIT

printf '%s' 'acme-secret-abc' | "$KC_STORE" acme-prod-deploy acme "Test token" >/dev/null 2>&1
check "kc-store round trip -> 0" 0 $?

GOT=$("$KC_GET" acme-prod-deploy 2>/dev/null)
check "kc-get round trip -> 0" 0 $?
check "kc-get returns the stored secret" "acme-secret-abc" "$GOT"

"$KC_GET" no-such-token >/dev/null 2>&1
check "kc-get missing entry -> 3" 3 $?

# Rotation: same command, new value, -U updates in place.
printf '%s' 'acme-secret-xyz' | "$KC_STORE" acme-prod-deploy acme "Test token" >/dev/null 2>&1
ROT=$("$KC_GET" acme-prod-deploy 2>/dev/null)
check "kc-store rotation updates the value" "acme-secret-xyz" "$ROT"

echo "----"
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
