#!/usr/bin/env bash
# =============================================================================
# Repository Security Scanner
# =============================================================================
#
# Point-in-time security assessment for cloned repositories.
# Runs tiered scans from fast surface checks to deep analysis.
#
# Usage:
#   repo-security-scan.sh [OPTIONS] [TARGET_DIR]
#   repo-security-scan.sh --quarantine-clone <URL> [DEST_DIR]
#
# Options:
#   --tier 1|2|3       Scan depth (default: 1)
#   --quarantine-clone  Clone to quarantine, scan, promote if clean
#   --json             Output JSON summary to stdout
#   --quiet            Suppress non-critical terminal output
#   --no-report        Skip markdown report generation
#   --timeout SECS     Per-tool timeout in seconds (default: 60)
#
# Tiers:
#   1 (fast, <30s):    trivy, gitleaks, guarddog, suspicious file check
#   2 (standard, <3m): + scorecard, syft->grype, semgrep, trufflehog
#   3 (deep, 3+m):     + full git history scan, license audit
#
# Exit codes:
#   0 = Clean (score >= 80)
#   1 = Warnings (score 50-79)
#   2 = Critical (score < 50)
#
# Environment:
#   REPORT_DIR          Override report output directory (default: ./reports)
#   QUARANTINE_DIR      Override quarantine directory (default: ~/.quarantine/repos)
#   REPO_SCAN_TIMEOUT   Override per-tool timeout
#   REPO_SCAN_LIB       Optional path to a shell file that defines send_alert
#                       (desktop notifications). Notifications are skipped if unset.
#
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y-%m-%d-%H%M)

# Optional integration library. Point REPO_SCAN_LIB at a shell file that
# defines send_alert (for example desktop notifications) to enable alerts.
# Without it the scanner runs standalone and simply skips notifications.
if [[ -n "${REPO_SCAN_LIB:-}" && -f "$REPO_SCAN_LIB" ]]; then
    # shellcheck disable=SC1090
    source "$REPO_SCAN_LIB"
fi

# Report output directory (override with REPORT_DIR)
REPORT_DIR="${REPORT_DIR:-./reports}"
QUARANTINE_DIR="${QUARANTINE_DIR:-$HOME/.quarantine/repos}"
TOOL_TIMEOUT="${REPO_SCAN_TIMEOUT:-60}"

# CLI defaults
SCAN_TIER=1
TARGET_DIR=""
QUARANTINE_URL=""
QUARANTINE_DEST=""
JSON_OUTPUT=false
QUIET=false
GENERATE_REPORT=true

# Colors
if [ -t 2 ] && [ -n "${TERM:-}" ] && [ "${TERM}" != "dumb" ]; then
    RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'
    CYAN='\033[0;36m'
else
    RED=''; YELLOW=''; GREEN=''; BLUE=''; BOLD=''; DIM=''; NC=''; CYAN=''
fi

# Findings accumulators
FINDING_SEV=()
FINDING_TOOL=()
FINDING_MSG=()
CRITICAL_COUNT=0
HIGH_COUNT=0
MEDIUM_COUNT=0
LOW_COUNT=0
INFO_COUNT=0
SCAN_ERRORS=0

# Ecosystems and tools
ECOSYSTEMS=()
declare -A TOOLS=()
TOOLS_USED=()
TOOLS_MISSING=()
TOOL_TIMINGS=()

# Temp directory for intermediate output
TMPDIR_SCAN=$(mktemp -d)
trap 'rm -rf "$TMPDIR_SCAN"' EXIT

# ---------------------------------------------------------------------------
# CLI Parsing
# ---------------------------------------------------------------------------

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --tier)
                SCAN_TIER="$2"; shift 2
                if [[ ! "$SCAN_TIER" =~ ^[123]$ ]]; then
                    echo "Error: --tier must be 1, 2, or 3" >&2; exit 1
                fi ;;
            --quarantine-clone)
                QUARANTINE_URL="$2"; shift 2
                if [[ $# -gt 0 && ! "$1" =~ ^-- ]]; then
                    QUARANTINE_DEST="$1"; shift
                fi ;;
            --json)       JSON_OUTPUT=true; shift ;;
            --quiet)      QUIET=true; shift ;;
            --no-report)  GENERATE_REPORT=false; shift ;;
            --timeout)    TOOL_TIMEOUT="$2"; shift 2 ;;
            --help|-h)    head -35 "$0" | tail -30; exit 0 ;;
            -*)           echo "Unknown option: $1" >&2; exit 1 ;;
            *)            TARGET_DIR="$1"; shift ;;
        esac
    done
    TARGET_DIR="${TARGET_DIR:-.}"
    TARGET_DIR="$(cd "$TARGET_DIR" 2>/dev/null && pwd)" || {
        echo "Error: directory does not exist: $TARGET_DIR" >&2; exit 1
    }
}

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

log() { $QUIET || printf "%b\n" "$*" >&2; }
log_dim() { $QUIET || printf "%b%b%b\n" "$DIM" "$*" "$NC" >&2; }
log_err() { printf "%b[ERROR]%b %s\n" "$RED" "$NC" "$*" >&2; }

_now() { date +%s; }

add_finding() {
    local sev="$1" tool="$2" msg="$3"
    FINDING_SEV+=("$sev")
    FINDING_TOOL+=("$tool")
    FINDING_MSG+=("$msg")
    case "$sev" in
        CRITICAL) ((CRITICAL_COUNT++)) || true ;;
        HIGH)     ((HIGH_COUNT++)) || true ;;
        MEDIUM)   ((MEDIUM_COUNT++)) || true ;;
        LOW)      ((LOW_COUNT++)) || true ;;
        INFO)     ((INFO_COUNT++)) || true ;;
    esac
}

run_with_timeout() {
    local secs="$1"; shift
    if command -v timeout >/dev/null 2>&1; then
        timeout "$secs" "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout "$secs" "$@"
    else
        "$@"
    fi
}

# ---------------------------------------------------------------------------
# Tool Detection
# ---------------------------------------------------------------------------

check_tools() {
    log "${BOLD}Checking tools...${NC}"
    local required_tier1=(trivy gitleaks guarddog jq)
    local required_tier2=(scorecard syft grype semgrep trufflehog)
    local all_tools=("${required_tier1[@]}")
    [[ $SCAN_TIER -ge 2 ]] && all_tools+=("${required_tier2[@]}")
    [[ $SCAN_TIER -ge 3 ]] && all_tools+=(trufflehog)  # already in tier2

    for tool in "${all_tools[@]}"; do
        if command -v "$tool" >/dev/null 2>&1; then
            TOOLS[$tool]="true"
            TOOLS_USED+=("$tool")
        else
            TOOLS[$tool]="false"
            TOOLS_MISSING+=("$tool")
        fi
    done

    local available=${#TOOLS_USED[@]}
    local missing=${#TOOLS_MISSING[@]}
    if [[ $missing -gt 0 ]]; then
        log_dim "  Available: $available | Missing: $missing (${TOOLS_MISSING[*]})"
    else
        log "  All $available tools available"
    fi
}

# ---------------------------------------------------------------------------
# Ecosystem Detection
# ---------------------------------------------------------------------------

detect_ecosystems() {
    log "${BOLD}Detecting ecosystems...${NC}"

    # Python
    if [[ -f "$TARGET_DIR/pyproject.toml" || -f "$TARGET_DIR/setup.py" || \
          -f "$TARGET_DIR/requirements.txt" || -f "$TARGET_DIR/Pipfile" || \
          -f "$TARGET_DIR/setup.cfg" ]]; then
        ECOSYSTEMS+=("python")
    fi

    # Node.js
    if [[ -f "$TARGET_DIR/package.json" ]]; then
        ECOSYSTEMS+=("node")
    fi

    # Rust
    if [[ -f "$TARGET_DIR/Cargo.toml" ]]; then
        ECOSYSTEMS+=("rust")
    fi

    # Go
    if [[ -f "$TARGET_DIR/go.mod" ]]; then
        ECOSYSTEMS+=("go")
    fi

    # Ruby
    if [[ -f "$TARGET_DIR/Gemfile" ]]; then
        ECOSYSTEMS+=("ruby")
    fi

    # Java/Kotlin
    if [[ -f "$TARGET_DIR/pom.xml" || -f "$TARGET_DIR/build.gradle" || \
          -f "$TARGET_DIR/build.gradle.kts" ]]; then
        ECOSYSTEMS+=("java")
    fi

    if [[ ${#ECOSYSTEMS[@]} -eq 0 ]]; then
        ECOSYSTEMS+=("unknown")
    fi

    log "  Detected: ${ECOSYSTEMS[*]}"
}

# =============================================================================
# TIER 1: Fast Scans (<30s)
# =============================================================================

scan_trivy_fs() {
    [[ "${TOOLS[trivy]:-false}" == "true" ]] || { log_dim "  - trivy not installed"; return 0; }
    log "  ${CYAN}[trivy]${NC} Filesystem scan (vuln + secret + misconfig)..."
    local start=$(_now)

    local outfile="$TMPDIR_SCAN/trivy.json"
    if ! run_with_timeout "$TOOL_TIMEOUT" trivy fs \
            --scanners vuln,secret,misconfig \
            --format json \
            --quiet \
            "$TARGET_DIR" > "$outfile" 2>/dev/null; then
        add_finding "INFO" "trivy" "Scan timed out or failed"
        ((SCAN_ERRORS++)) || true
        TOOL_TIMINGS+=("trivy:err")
        return 0
    fi

    if [[ "${TOOLS[jq]:-false}" == "true" && -s "$outfile" ]]; then
        local crit high med low secrets misconf
        crit=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="CRITICAL")] | length' "$outfile" 2>/dev/null || echo 0)
        high=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="HIGH")] | length' "$outfile" 2>/dev/null || echo 0)
        med=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="MEDIUM")] | length' "$outfile" 2>/dev/null || echo 0)
        low=$(jq '[.Results[]?.Vulnerabilities[]? | select(.Severity=="LOW")] | length' "$outfile" 2>/dev/null || echo 0)
        secrets=$(jq '[.Results[]?.Secrets[]?] | length' "$outfile" 2>/dev/null || echo 0)
        misconf=$(jq '[.Results[]?.Misconfigurations[]? | select(.Severity=="HIGH" or .Severity=="CRITICAL")] | length' "$outfile" 2>/dev/null || echo 0)

        [[ $crit -gt 0 ]] && add_finding "CRITICAL" "trivy" "$crit critical vulnerabilities"
        [[ $high -gt 0 ]] && add_finding "HIGH" "trivy" "$high high-severity vulnerabilities"
        [[ $med -gt 0 ]]  && add_finding "MEDIUM" "trivy" "$med medium-severity vulnerabilities"
        [[ $low -gt 0 ]]  && add_finding "LOW" "trivy" "$low low-severity vulnerabilities"
        [[ $secrets -gt 0 ]] && add_finding "CRITICAL" "trivy-secret" "$secrets secrets/credentials detected in files"
        [[ $misconf -gt 0 ]] && add_finding "HIGH" "trivy-misconfig" "$misconf high/critical misconfigurations"

        local total=$((crit + high + med + low))
        if [[ $total -eq 0 && $secrets -eq 0 && $misconf -eq 0 ]]; then
            log "    ${GREEN}No issues${NC}"
        else
            log "    ${YELLOW}${crit}C/${high}H/${med}M/${low}L vulns, ${secrets} secrets, ${misconf} misconfigs${NC}"
        fi
    else
        # Fallback: check if output indicates issues
        local lines
        lines=$(wc -l < "$outfile" 2>/dev/null || echo 0)
        log_dim "    (jq unavailable, raw output: $lines lines)"
    fi

    local elapsed=$(( $(_now) - start ))
    TOOL_TIMINGS+=("trivy:${elapsed}s")
}

scan_gitleaks_files() {
    [[ "${TOOLS[gitleaks]:-false}" == "true" ]] || { log_dim "  - gitleaks not installed"; return 0; }
    log "  ${CYAN}[gitleaks]${NC} Secret detection (current files)..."
    local start=$(_now)

    local outfile="$TMPDIR_SCAN/gitleaks.json"
    # gitleaks exits 1 when it finds leaks, 0 when clean
    run_with_timeout "$TOOL_TIMEOUT" gitleaks detect \
        --source "$TARGET_DIR" \
        --no-git \
        --report-format json \
        --report-path "$outfile" \
        --quiet 2>/dev/null || true

    if [[ -s "$outfile" && "${TOOLS[jq]:-false}" == "true" ]]; then
        local count
        count=$(jq 'length' "$outfile" 2>/dev/null || echo 0)
        if [[ $count -gt 0 ]]; then
            add_finding "CRITICAL" "gitleaks" "$count secrets/credentials detected in files"
            # Extract top findings for detail
            jq -r '.[0:5][] | "    - \(.RuleID): \(.File):\(.StartLine)"' "$outfile" 2>/dev/null >> "$TMPDIR_SCAN/details.txt" || true
            log "    ${RED}$count secrets found${NC}"
        else
            log "    ${GREEN}No secrets${NC}"
        fi
    elif [[ ! -s "$outfile" ]]; then
        log "    ${GREEN}No secrets${NC}"
    fi

    local elapsed=$(( $(_now) - start ))
    TOOL_TIMINGS+=("gitleaks:${elapsed}s")
}

scan_guarddog_deps() {
    [[ "${TOOLS[guarddog]:-false}" == "true" ]] || { log_dim "  - guarddog not installed"; return 0; }
    log "  ${CYAN}[guarddog]${NC} Malicious package detection..."
    local start=$(_now)
    local found=0

    # Python dependency files
    for req in "$TARGET_DIR"/requirements*.txt; do
        [[ -f "$req" ]] || continue
        local output
        if output=$(run_with_timeout "$TOOL_TIMEOUT" guarddog pypi verify "$req" 2>&1); then
            local issues
            issues=$(echo "$output" | grep -cE "Found [1-9]" || echo 0)
            if [[ $issues -gt 0 ]]; then
                add_finding "CRITICAL" "guarddog" "Suspicious packages in $(basename "$req")"
                ((found++))
            fi
        fi
    done

    # pyproject.toml (extract deps if possible)
    if [[ -f "$TARGET_DIR/pyproject.toml" && "${TOOLS[jq]:-false}" == "true" ]]; then
        # Try python-based extraction as guarddog may not parse toml directly
        if command -v python3 >/dev/null 2>&1; then
            python3 -c "
import sys
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        sys.exit(0)
with open('$TARGET_DIR/pyproject.toml', 'rb') as f:
    d = tomllib.load(f)
deps = d.get('project', {}).get('dependencies', [])
for dep in deps:
    name = dep.split('>')[0].split('<')[0].split('=')[0].split('[')[0].split('!')[0].strip()
    if name:
        print(name)
" > "$TMPDIR_SCAN/pyproject_deps.txt" 2>/dev/null || true
            if [[ -s "$TMPDIR_SCAN/pyproject_deps.txt" ]]; then
                local output
                if output=$(run_with_timeout "$TOOL_TIMEOUT" guarddog pypi verify "$TMPDIR_SCAN/pyproject_deps.txt" 2>&1); then
                    local issues
                    issues=$(echo "$output" | grep -cE "Found [1-9]" || echo 0)
                    if [[ $issues -gt 0 ]]; then
                        add_finding "CRITICAL" "guarddog" "Suspicious packages in pyproject.toml deps"
                        ((found++))
                    fi
                fi
            fi
        fi
    fi

    # npm package.json
    if [[ -f "$TARGET_DIR/package.json" ]]; then
        local output
        if output=$(run_with_timeout "$TOOL_TIMEOUT" guarddog npm verify "$TARGET_DIR/package.json" 2>&1); then
            local issues
            issues=$(echo "$output" | grep -cE "Found [1-9]" || echo 0)
            if [[ $issues -gt 0 ]]; then
                add_finding "CRITICAL" "guarddog" "Suspicious npm packages detected"
                ((found++))
            fi
        fi
    fi

    if [[ $found -eq 0 ]]; then
        log "    ${GREEN}No malicious packages${NC}"
    else
        log "    ${RED}$found suspicious dependency source(s)${NC}"
    fi

    local elapsed=$(( $(_now) - start ))
    TOOL_TIMINGS+=("guarddog:${elapsed}s")
}

scan_suspicious_files() {
    log "  ${CYAN}[heuristic]${NC} Suspicious file analysis..."
    local start=$(_now)
    local found=0

    # .pth files (Python persistence mechanism)
    local pth_count
    pth_count=$(find "$TARGET_DIR" -name "*.pth" -type f -not -path "*/.git/*" -not -path "*/node_modules/*" 2>/dev/null | wc -l | tr -d ' ')
    if [[ $pth_count -gt 0 ]]; then
        add_finding "HIGH" "heuristic" "$pth_count .pth files found (Python persistence mechanism)"
        ((found++))
    fi

    # setup.py with dangerous patterns
    if [[ -f "$TARGET_DIR/setup.py" ]]; then
        local dangerous
        dangerous=$(grep -cE '(os\.system|subprocess\.(call|run|Popen)|__import__|eval\(|exec\(|urllib\.request\.urlopen|requests\.(get|post))' "$TARGET_DIR/setup.py" 2>/dev/null || echo 0)
        if [[ $dangerous -gt 0 ]]; then
            add_finding "HIGH" "heuristic" "setup.py contains $dangerous potentially dangerous calls (os.system, subprocess, eval, exec)"
            ((found++))
        fi
    fi

    # npm install scripts (preinstall/postinstall running shell commands)
    if [[ -f "$TARGET_DIR/package.json" && "${TOOLS[jq]:-false}" == "true" ]]; then
        local install_scripts
        install_scripts=$(jq -r '.scripts // {} | to_entries[] | select(.key | test("^(pre|post)?(install|uninstall|prepare)$")) | "\(.key): \(.value)"' "$TARGET_DIR/package.json" 2>/dev/null || true)
        if [[ -n "$install_scripts" ]]; then
            add_finding "MEDIUM" "heuristic" "npm install scripts found: $(echo "$install_scripts" | head -3 | tr '\n' '; ')"
            ((found++))
        fi
    fi

    # Shell dotfiles in repo root (potential shell hijacking)
    local shell_dotfiles=0
    for f in .bashrc .zshrc .profile .bash_profile .zprofile; do
        [[ -f "$TARGET_DIR/$f" ]] && ((shell_dotfiles++))
    done
    if [[ $shell_dotfiles -gt 0 ]]; then
        add_finding "HIGH" "heuristic" "$shell_dotfiles shell dotfiles in repo root (potential shell hijacking)"
        ((found++))
    fi

    # Symlinks pointing outside repo
    local bad_links=0
    local repo_real
    repo_real=$(cd "$TARGET_DIR" && pwd -P)
    while IFS= read -r link; do
        local target
        target=$(readlink -f "$link" 2>/dev/null || true)
        if [[ -n "$target" && "$target" != "$repo_real"* ]]; then
            ((bad_links++))
        fi
    done < <(find "$TARGET_DIR" -type l -not -path "*/.git/*" -not -path "*/node_modules/*" 2>/dev/null)
    if [[ $bad_links -gt 0 ]]; then
        add_finding "MEDIUM" "heuristic" "$bad_links symlinks pointing outside repository"
        ((found++))
    fi

    # .env files (may contain secrets)
    local env_count
    env_count=$(find "$TARGET_DIR" -maxdepth 3 \( -name ".env" -o -name ".env.local" -o -name ".env.production" -o -name ".env.secret" \) -not -path "*/node_modules/*" 2>/dev/null | wc -l | tr -d ' ')
    if [[ $env_count -gt 0 ]]; then
        add_finding "MEDIUM" "heuristic" "$env_count environment files found (may contain secrets)"
        ((found++))
    fi

    # Binary/executable files (unexpected)
    local exe_count
    exe_count=$(find "$TARGET_DIR" -type f -perm +111 \
        -not -path "*/.git/*" -not -path "*/node_modules/*" \
        -not -path "*/__pycache__/*" -not -path "*/.venv/*" \
        -not -name "*.sh" -not -name "*.py" -not -name "*.rb" \
        -not -name "*.pl" -not -name "gradlew" -not -name "mvnw" \
        2>/dev/null | wc -l | tr -d ' ')
    if [[ $exe_count -gt 5 ]]; then
        add_finding "LOW" "heuristic" "$exe_count non-standard executable files"
        ((found++))
    fi

    if [[ $found -eq 0 ]]; then
        log "    ${GREEN}No suspicious files${NC}"
    else
        log "    ${YELLOW}$found suspicious patterns${NC}"
    fi

    local elapsed=$(( $(_now) - start ))
    TOOL_TIMINGS+=("heuristic:${elapsed}s")
}

scan_security_posture() {
    log "  ${CYAN}[posture]${NC} Security practices check..."

    # Positive signals
    [[ -f "$TARGET_DIR/.github/dependabot.yml" || -f "$TARGET_DIR/.github/dependabot.yaml" ]] \
        && add_finding "INFO" "posture" "Dependabot enabled"
    [[ -f "$TARGET_DIR/SECURITY.md" || -f "$TARGET_DIR/.github/SECURITY.md" ]] \
        && add_finding "INFO" "posture" "SECURITY.md present"
    [[ -f "$TARGET_DIR/.pre-commit-config.yaml" ]] \
        && add_finding "INFO" "posture" "Pre-commit hooks configured"

    # CI security scanning
    local ci_security=false
    if find "$TARGET_DIR/.github/workflows" -name "*.yml" -exec grep -ql -E "(codeql|trivy|snyk|semgrep|scorecard)" {} + 2>/dev/null; then
        add_finding "INFO" "posture" "CI security scanning detected"
        ci_security=true
    fi

    # Lockfile presence (pinned dependencies are safer)
    local has_lockfile=false
    for lf in uv.lock package-lock.json yarn.lock pnpm-lock.yaml Cargo.lock poetry.lock Pipfile.lock Gemfile.lock go.sum; do
        if [[ -f "$TARGET_DIR/$lf" ]]; then
            has_lockfile=true
            break
        fi
    done
    if ! $has_lockfile && [[ ${#ECOSYSTEMS[@]} -gt 0 && "${ECOSYSTEMS[0]}" != "unknown" ]]; then
        add_finding "MEDIUM" "posture" "No lockfile found, dependencies are not pinned"
    fi

    # Signed commits (check last 5)
    if git -C "$TARGET_DIR" log --format='%G?' -5 2>/dev/null | grep -q 'G'; then
        add_finding "INFO" "posture" "Signed commits detected"
    fi

    local posture_info=0
    for i in "${!FINDING_SEV[@]}"; do
        [[ "${FINDING_SEV[$i]}" == "INFO" && "${FINDING_TOOL[$i]}" == "posture" ]] && ((posture_info++)) || true
    done
    log "    $posture_info positive security signals"
}

# =============================================================================
# TIER 2: Standard Scans (1-3 min)
# =============================================================================

scan_scorecard() {
    [[ "${TOOLS[scorecard]:-false}" == "true" ]] || { log_dim "  - scorecard not installed"; return 0; }

    # Scorecard requires GITHUB_TOKEN to avoid rate limiting
    if [[ -z "${GITHUB_TOKEN:-}" && -z "${GITHUB_AUTH_TOKEN:-}" ]]; then
        log_dim "  - scorecard skipped (no GITHUB_TOKEN set, export it to enable)"
        add_finding "INFO" "scorecard" "Skipped: set GITHUB_TOKEN to enable OSSF Scorecard"
        TOOL_TIMINGS+=("scorecard:skip")
        return 0
    fi

    # Scorecard needs a git remote to check
    local remote
    remote=$(git -C "$TARGET_DIR" remote get-url origin 2>/dev/null || true)
    if [[ -z "$remote" ]]; then
        log_dim "  - scorecard skipped (no git remote)"
        return 0
    fi

    # Convert SSH URL to HTTPS repo path for scorecard
    local repo_slug
    if [[ "$remote" =~ github\.com[:/](.+)\.git$ ]]; then
        repo_slug="${BASH_REMATCH[1]}"
    elif [[ "$remote" =~ github\.com[:/](.+)$ ]]; then
        repo_slug="${BASH_REMATCH[1]%.git}"
    else
        log_dim "  - scorecard skipped (non-GitHub remote)"
        return 0
    fi

    log "  ${CYAN}[scorecard]${NC} OSSF supply chain health..."
    local start=$(_now)

    local outfile="$TMPDIR_SCAN/scorecard.json"
    local errfile="$TMPDIR_SCAN/scorecard.err"
    if ! run_with_timeout 30 scorecard \
            --repo="github.com/$repo_slug" \
            --format json > "$outfile" 2>"$errfile"; then
        if grep -q "Rate limit" "$errfile" 2>/dev/null; then
            log_dim "    Rate-limited, try again later or check GITHUB_TOKEN"
        else
            add_finding "INFO" "scorecard" "Scorecard scan failed"
        fi
        TOOL_TIMINGS+=("scorecard:err")
        return 0
    fi

    if [[ -s "$outfile" && "${TOOLS[jq]:-false}" == "true" ]]; then
        local score
        score=$(jq '.score // -1' "$outfile" 2>/dev/null || echo -1)
        if [[ "$score" != "-1" ]]; then
            local score_int=${score%.*}
            if [[ $score_int -lt 4 ]]; then
                add_finding "HIGH" "scorecard" "OSSF Scorecard score: $score/10 (poor supply chain health)"
            elif [[ $score_int -lt 7 ]]; then
                add_finding "MEDIUM" "scorecard" "OSSF Scorecard score: $score/10 (moderate supply chain health)"
            else
                add_finding "INFO" "scorecard" "OSSF Scorecard score: $score/10 (good supply chain health)"
            fi
            log "    Score: $score/10"
        fi
    fi

    local elapsed=$(( $(_now) - start ))
    TOOL_TIMINGS+=("scorecard:${elapsed}s")
}

scan_sbom_grype() {
    [[ "${TOOLS[syft]:-false}" == "true" && "${TOOLS[grype]:-false}" == "true" ]] || {
        log_dim "  - syft/grype not installed"; return 0
    }
    log "  ${CYAN}[syft+grype]${NC} SBOM generation + vulnerability scan..."
    local start=$(_now)

    # Generate SBOM
    local sbom_file="$TMPDIR_SCAN/sbom.json"
    if ! run_with_timeout "$TOOL_TIMEOUT" syft "$TARGET_DIR" \
            -o json --quiet > "$sbom_file" 2>/dev/null; then
        add_finding "INFO" "syft" "SBOM generation failed or timed out"
        TOOL_TIMINGS+=("syft+grype:err")
        return 0
    fi

    # Scan SBOM for vulnerabilities
    local grype_file="$TMPDIR_SCAN/grype.json"
    if ! run_with_timeout "$TOOL_TIMEOUT" grype \
            "sbom:$sbom_file" \
            --output json > "$grype_file" 2>/dev/null; then
        add_finding "INFO" "grype" "Vulnerability scan failed or timed out"
        TOOL_TIMINGS+=("syft+grype:err")
        return 0
    fi

    if [[ -s "$grype_file" && "${TOOLS[jq]:-false}" == "true" ]]; then
        local crit high med low
        crit=$(jq '[.matches[]? | select(.vulnerability.severity=="Critical")] | length' "$grype_file" 2>/dev/null || echo 0)
        high=$(jq '[.matches[]? | select(.vulnerability.severity=="High")] | length' "$grype_file" 2>/dev/null || echo 0)
        med=$(jq '[.matches[]? | select(.vulnerability.severity=="Medium")] | length' "$grype_file" 2>/dev/null || echo 0)
        low=$(jq '[.matches[]? | select(.vulnerability.severity=="Low")] | length' "$grype_file" 2>/dev/null || echo 0)

        [[ $crit -gt 0 ]] && add_finding "CRITICAL" "grype" "$crit critical vulnerabilities (SBOM scan)"
        [[ $high -gt 0 ]] && add_finding "HIGH" "grype" "$high high-severity vulnerabilities (SBOM scan)"
        [[ $med -gt 0 ]]  && add_finding "MEDIUM" "grype" "$med medium-severity vulnerabilities (SBOM scan)"
        [[ $low -gt 0 ]]  && add_finding "LOW" "grype" "$low low-severity vulnerabilities (SBOM scan)"

        local total=$((crit + high + med + low))
        if [[ $total -eq 0 ]]; then
            log "    ${GREEN}No vulnerabilities in SBOM${NC}"
        else
            log "    ${YELLOW}${crit}C/${high}H/${med}M/${low}L vulnerabilities${NC}"
        fi

        # Count packages in SBOM for report
        local pkg_count
        pkg_count=$(jq '.artifacts | length' "$sbom_file" 2>/dev/null || echo "?")
        log_dim "    ($pkg_count packages in SBOM)"
    fi

    local elapsed=$(( $(_now) - start ))
    TOOL_TIMINGS+=("syft+grype:${elapsed}s")
}

scan_semgrep() {
    [[ "${TOOLS[semgrep]:-false}" == "true" ]] || { log_dim "  - semgrep not installed"; return 0; }
    log "  ${CYAN}[semgrep]${NC} Static analysis (security rules)..."
    local start=$(_now)

    local outfile="$TMPDIR_SCAN/semgrep.json"
    if ! run_with_timeout "$((TOOL_TIMEOUT * 2))" semgrep scan \
            --config "p/security-audit" \
            --config "p/secrets" \
            --json \
            --quiet \
            "$TARGET_DIR" > "$outfile" 2>/dev/null; then
        # Semgrep exits 1 when findings exist, check if output is valid
        if [[ ! -s "$outfile" ]]; then
            add_finding "INFO" "semgrep" "Scan failed or timed out"
            TOOL_TIMINGS+=("semgrep:err")
            return 0
        fi
    fi

    if [[ -s "$outfile" && "${TOOLS[jq]:-false}" == "true" ]]; then
        local errors warnings infos
        errors=$(jq '[.results[]? | select(.extra.severity == "ERROR")] | length' "$outfile" 2>/dev/null || echo 0)
        warnings=$(jq '[.results[]? | select(.extra.severity == "WARNING")] | length' "$outfile" 2>/dev/null || echo 0)
        infos=$(jq '[.results[]? | select(.extra.severity == "INFO")] | length' "$outfile" 2>/dev/null || echo 0)

        [[ $errors -gt 0 ]]   && add_finding "HIGH" "semgrep" "$errors security errors (static analysis)"
        [[ $warnings -gt 0 ]] && add_finding "MEDIUM" "semgrep" "$warnings security warnings (static analysis)"
        [[ $infos -gt 0 ]]    && add_finding "LOW" "semgrep" "$infos security notes (static analysis)"

        local total=$((errors + warnings + infos))
        if [[ $total -eq 0 ]]; then
            log "    ${GREEN}No security issues${NC}"
        else
            log "    ${YELLOW}${errors} errors, ${warnings} warnings, ${infos} info${NC}"
        fi
    fi

    local elapsed=$(( $(_now) - start ))
    TOOL_TIMINGS+=("semgrep:${elapsed}s")
}

scan_trufflehog_fs() {
    [[ "${TOOLS[trufflehog]:-false}" == "true" ]] || { log_dim "  - trufflehog not installed"; return 0; }
    log "  ${CYAN}[trufflehog]${NC} Deep secret scan (filesystem, with verification)..."
    local start=$(_now)

    local outfile="$TMPDIR_SCAN/trufflehog_fs.json"
    if ! run_with_timeout "$TOOL_TIMEOUT" trufflehog filesystem \
            "$TARGET_DIR" \
            --json \
            --only-verified 2>/dev/null > "$outfile"; then
        # trufflehog may exit non-zero on findings
        true
    fi

    if [[ -s "$outfile" ]]; then
        local count
        count=$(wc -l < "$outfile" | tr -d ' ')  # One JSON object per line
        if [[ $count -gt 0 ]]; then
            add_finding "CRITICAL" "trufflehog" "$count VERIFIED live credentials detected"
            log "    ${RED}$count verified secrets${NC}"
        else
            log "    ${GREEN}No verified secrets${NC}"
        fi
    else
        log "    ${GREEN}No verified secrets${NC}"
    fi

    local elapsed=$(( $(_now) - start ))
    TOOL_TIMINGS+=("trufflehog:${elapsed}s")
}

# =============================================================================
# TIER 3: Deep Scans (3+ min)
# =============================================================================

scan_trufflehog_git() {
    [[ "${TOOLS[trufflehog]:-false}" == "true" ]] || { log_dim "  - trufflehog not installed"; return 0; }
    [[ -d "$TARGET_DIR/.git" ]] || { log_dim "  - not a git repo, skipping history scan"; return 0; }
    log "  ${CYAN}[trufflehog]${NC} Full git history scan..."
    local start=$(_now)

    local outfile="$TMPDIR_SCAN/trufflehog_git.json"
    run_with_timeout "$((TOOL_TIMEOUT * 3))" trufflehog git \
        "file://$TARGET_DIR" \
        --json 2>/dev/null > "$outfile" || true

    if [[ -s "$outfile" ]]; then
        local total verified
        total=$(wc -l < "$outfile" | tr -d ' ')
        verified=$(grep -c '"Verified":true' "$outfile" 2>/dev/null || true)
        verified=${verified:-0}

        if [[ $verified -gt 0 ]]; then
            add_finding "CRITICAL" "trufflehog-git" "$verified VERIFIED credentials in git history"
        fi
        if [[ $((total - verified)) -gt 0 ]]; then
            add_finding "MEDIUM" "trufflehog-git" "$((total - verified)) unverified potential secrets in git history"
        fi

        if [[ $total -gt 0 ]]; then
            log "    ${YELLOW}$total findings ($verified verified)${NC}"
        else
            log "    ${GREEN}Clean history${NC}"
        fi
    else
        log "    ${GREEN}Clean history${NC}"
    fi

    local elapsed=$(( $(_now) - start ))
    TOOL_TIMINGS+=("trufflehog-git:${elapsed}s")
}

scan_licenses() {
    [[ "${TOOLS[trivy]:-false}" == "true" ]] || { log_dim "  - trivy not installed"; return 0; }
    log "  ${CYAN}[trivy]${NC} License compliance scan..."
    local start=$(_now)

    local outfile="$TMPDIR_SCAN/licenses.json"
    if ! run_with_timeout "$TOOL_TIMEOUT" trivy fs \
            --scanners license \
            --format json \
            --quiet \
            "$TARGET_DIR" > "$outfile" 2>/dev/null; then
        TOOL_TIMINGS+=("licenses:err")
        return 0
    fi

    if [[ -s "$outfile" && "${TOOLS[jq]:-false}" == "true" ]]; then
        local restricted
        restricted=$(jq '[.Results[]?.Licenses[]? | select(.Severity=="CRITICAL" or .Severity=="HIGH")] | length' "$outfile" 2>/dev/null || echo 0)
        if [[ $restricted -gt 0 ]]; then
            add_finding "MEDIUM" "license" "$restricted restrictive/problematic licenses found"
            log "    ${YELLOW}$restricted restrictive licenses${NC}"
        else
            log "    ${GREEN}No license issues${NC}"
        fi
    fi

    local elapsed=$(( $(_now) - start ))
    TOOL_TIMINGS+=("licenses:${elapsed}s")
}

# =============================================================================
# Scoring & Verdict
# =============================================================================

calculate_score() {
    local score=100
    score=$((score - CRITICAL_COUNT * 25))
    score=$((score - HIGH_COUNT * 10))
    score=$((score - MEDIUM_COUNT * 3))
    score=$((score - LOW_COUNT * 1))
    [[ $score -lt 0 ]] && score=0
    echo "$score"
}

determine_verdict() {
    local score
    score=$(calculate_score)
    if [[ $score -ge 80 ]]; then
        echo "CLEAN"
    elif [[ $score -ge 50 ]]; then
        echo "WARN"
    else
        echo "CRITICAL"
    fi
}

# =============================================================================
# Output
# =============================================================================

print_summary() {
    local score verdict repo_name
    score=$(calculate_score)
    verdict=$(determine_verdict)
    repo_name=$(basename "$TARGET_DIR")
    local total_findings=${#FINDING_SEV[@]}
    local tier_label
    case $SCAN_TIER in
        1) tier_label="fast" ;;
        2) tier_label="standard" ;;
        3) tier_label="deep" ;;
    esac

    local verdict_color verdict_icon
    case "$verdict" in
        CLEAN)    verdict_color="$GREEN"; verdict_icon="OK" ;;
        WARN)     verdict_color="$YELLOW"; verdict_icon="WARN" ;;
        CRITICAL) verdict_color="$RED"; verdict_icon="CRIT" ;;
    esac

    cat >&2 <<EOF

${BOLD}$(printf '%.0s=' {1..54})
  REPO SECURITY SCAN -- $repo_name
$(printf '%.0s=' {1..54})${NC}
  Target:      $TARGET_DIR
  Ecosystems:  ${ECOSYSTEMS[*]}
  Tier:        $SCAN_TIER ($tier_label)
  Tools:       ${TOOLS_USED[*]:-none}
$(printf '%.0s-' {1..54})

  Findings:    ${CRITICAL_COUNT} critical, ${HIGH_COUNT} high, ${MEDIUM_COUNT} medium, ${LOW_COUNT} low
  Errors:      ${SCAN_ERRORS}
  Timings:     ${TOOL_TIMINGS[*]:-n/a}

$(printf '%.0s-' {1..54})
  ${verdict_color}VERDICT: [$verdict_icon] $verdict     Score: ${score}/100${NC}
EOF

    if $GENERATE_REPORT; then
        echo "  Report:  $REPORT_DIR/repo-scan-${repo_name}-${TIMESTAMP}.md" >&2
    fi
    echo "${BOLD}$(printf '%.0s=' {1..54})${NC}" >&2

    # Print findings detail
    if [[ $total_findings -gt 0 ]]; then
        echo "" >&2
        local prev_sev=""
        for i in "${!FINDING_SEV[@]}"; do
            local sev="${FINDING_SEV[$i]}"
            if [[ "$sev" == "INFO" ]]; then continue; fi
            if [[ "$sev" != "$prev_sev" ]]; then
                local sev_color
                case "$sev" in
                    CRITICAL) sev_color="$RED" ;;
                    HIGH)     sev_color="$RED" ;;
                    MEDIUM)   sev_color="$YELLOW" ;;
                    LOW)      sev_color="$GREEN" ;;
                esac
                echo "  ${sev_color}${BOLD}${sev}:${NC}" >&2
                prev_sev="$sev"
            fi
            echo "    - [${FINDING_TOOL[$i]}] ${FINDING_MSG[$i]}" >&2
        done
    fi

    # macOS notification for critical findings
    if [[ $CRITICAL_COUNT -gt 0 ]] && type send_alert &>/dev/null; then
        send_alert "critical" "Repo Scan: $repo_name" "$CRITICAL_COUNT critical issues found (score: $score/100)"
    elif [[ $HIGH_COUNT -gt 0 ]] && type send_alert &>/dev/null; then
        send_alert "warning" "Repo Scan: $repo_name" "$HIGH_COUNT high-severity issues (score: $score/100)"
    fi
}

generate_report() {
    mkdir -p "$REPORT_DIR"
    local repo_name
    repo_name=$(basename "$TARGET_DIR")
    local report="$REPORT_DIR/repo-scan-${repo_name}-${TIMESTAMP}.md"
    local score verdict
    score=$(calculate_score)
    verdict=$(determine_verdict)
    local tier_label
    case $SCAN_TIER in 1) tier_label="fast" ;; 2) tier_label="standard" ;; 3) tier_label="deep" ;; esac

    cat > "$report" <<REPORT_EOF
# Repository Security Scan: $repo_name

**Date:** $(date '+%Y-%m-%d %H:%M')
**Target:** $TARGET_DIR
**Tier:** $SCAN_TIER ($tier_label)
**Ecosystems:** ${ECOSYSTEMS[*]}
**Score:** $score/100
**Verdict:** $verdict

## Summary

| Severity | Count |
|----------|-------|
| Critical | $CRITICAL_COUNT |
| High | $HIGH_COUNT |
| Medium | $MEDIUM_COUNT |
| Low | $LOW_COUNT |
| Info | $INFO_COUNT |
| Scan Errors | $SCAN_ERRORS |

## Findings
REPORT_EOF

    # Group findings by severity
    for severity in CRITICAL HIGH MEDIUM LOW INFO; do
        local has_findings=false
        for i in "${!FINDING_SEV[@]}"; do
            if [[ "${FINDING_SEV[$i]}" == "$severity" ]]; then
                if ! $has_findings; then
                    echo -e "\n### $severity" >> "$report"
                    has_findings=true
                fi
                echo "- **[${FINDING_TOOL[$i]}]** ${FINDING_MSG[$i]}" >> "$report"
            fi
        done
    done

    cat >> "$report" <<REPORT_EOF

## Tools

### Used
$(for t in "${TOOLS_USED[@]:-}"; do echo "- $t"; done)

### Missing
$(if [[ ${#TOOLS_MISSING[@]} -gt 0 ]]; then for t in "${TOOLS_MISSING[@]}"; do echo "- $t (not installed)"; done; else echo "- None"; fi)

## Timing

| Tool | Duration |
|------|----------|
$(for t in "${TOOL_TIMINGS[@]:-}"; do echo "| ${t%%:*} | ${t#*:} |"; done)

---
*Generated by repo-security-scan v1.0*
*Scan tier $SCAN_TIER ($tier_label) | $(date '+%Y-%m-%d %H:%M:%S')*
REPORT_EOF

    log_dim "  Report written: $report"
}

output_json() {
    local score verdict repo_name
    score=$(calculate_score)
    verdict=$(determine_verdict)
    repo_name=$(basename "$TARGET_DIR")

    # Build findings JSON array
    local findings_json="["
    for i in "${!FINDING_SEV[@]}"; do
        [[ $i -gt 0 ]] && findings_json+=","
        # Escape message for JSON
        local msg="${FINDING_MSG[$i]}"
        msg="${msg//\\/\\\\}"
        msg="${msg//\"/\\\"}"
        findings_json+="{\"severity\":\"${FINDING_SEV[$i]}\",\"tool\":\"${FINDING_TOOL[$i]}\",\"message\":\"$msg\"}"
    done
    findings_json+="]"

    cat <<JSON_EOF
{
  "version": "1.0",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "target": "$TARGET_DIR",
  "repo_name": "$repo_name",
  "tier": $SCAN_TIER,
  "ecosystems": [$(printf '"%s",' "${ECOSYSTEMS[@]}" | sed 's/,$//')]  ,
  "verdict": "$verdict",
  "score": $score,
  "summary": {
    "critical": $CRITICAL_COUNT,
    "high": $HIGH_COUNT,
    "medium": $MEDIUM_COUNT,
    "low": $LOW_COUNT,
    "info": $INFO_COUNT,
    "errors": $SCAN_ERRORS
  },
  "findings": $findings_json,
  "tools_used": [$(printf '"%s",' "${TOOLS_USED[@]:-}" | sed 's/,$//')]  ,
  "tools_missing": [$(printf '"%s",' "${TOOLS_MISSING[@]:-}" | sed 's/,$//')]  ,
  "timings": [$(printf '"%s",' "${TOOL_TIMINGS[@]:-}" | sed 's/,$//')]
}
JSON_EOF
}

# =============================================================================
# Quarantine Workflow
# =============================================================================

quarantine_clone() {
    local url="$1"
    local repo_name
    repo_name=$(basename "$url" .git)
    local quarantine_path="$QUARANTINE_DIR/${repo_name}-${TIMESTAMP}"

    log "${BOLD}Quarantine clone: $url${NC}"
    log "  Cloning to: $quarantine_path"

    mkdir -p "$QUARANTINE_DIR"

    # Shallow clone to minimize exposure
    if ! git clone --depth 1 "$url" "$quarantine_path" 2>&1 | while IFS= read -r line; do
        log_dim "    $line"
    done; then
        log_err "Clone failed"
        rm -rf "$quarantine_path"
        exit 1
    fi

    # Override target for scanning
    TARGET_DIR="$quarantine_path"
    log "  Clone complete. Scanning before promotion..."
}

promote_repo() {
    local dest="$1"
    local repo_name
    repo_name=$(basename "$TARGET_DIR")

    if [[ -e "$dest" ]]; then
        log_err "Destination already exists: $dest"
        log "  Quarantined repo remains at: $TARGET_DIR"
        return 1
    fi

    mv "$TARGET_DIR" "$dest"
    log "${GREEN}Promoted to: $dest${NC}"

    # Unshallow if needed for full development
    if git -C "$dest" rev-parse --is-shallow-repository 2>/dev/null | grep -q true; then
        log_dim "  Note: repo is shallow (--depth 1). Run 'git fetch --unshallow' for full history."
    fi
}

# =============================================================================
# Main
# =============================================================================

main() {
    parse_args "$@"

    local total_start=$(_now)

    # Handle quarantine clone
    if [[ -n "$QUARANTINE_URL" ]]; then
        quarantine_clone "$QUARANTINE_URL"
    fi

    local repo_name
    repo_name=$(basename "$TARGET_DIR")
    local tier_label
    case $SCAN_TIER in 1) tier_label="fast" ;; 2) tier_label="standard" ;; 3) tier_label="deep" ;; esac

    log ""
    log "${BOLD}Repository Security Scan${NC}, $repo_name (tier $SCAN_TIER/$tier_label)"
    log "$(printf '%.0s-' {1..54})"

    check_tools
    detect_ecosystems

    # --- Tier 1: Fast ---
    log ""
    log "${BOLD}Tier 1: Fast scan${NC}"
    scan_trivy_fs
    scan_gitleaks_files
    scan_guarddog_deps
    scan_suspicious_files
    scan_security_posture

    # --- Tier 2: Standard ---
    if [[ $SCAN_TIER -ge 2 ]]; then
        log ""
        log "${BOLD}Tier 2: Standard scan${NC}"
        scan_scorecard
        scan_sbom_grype
        scan_semgrep
        scan_trufflehog_fs
    fi

    # --- Tier 3: Deep ---
    if [[ $SCAN_TIER -ge 3 ]]; then
        log ""
        log "${BOLD}Tier 3: Deep scan${NC}"
        scan_trufflehog_git
        scan_licenses
    fi

    # --- Results ---
    local total_elapsed=$(( $(_now) - total_start ))
    TOOL_TIMINGS+=("TOTAL:${total_elapsed}s")

    log ""
    print_summary

    if $GENERATE_REPORT; then
        generate_report
    fi

    if $JSON_OUTPUT; then
        output_json
    fi

    # --- Quarantine promotion ---
    local verdict
    verdict=$(determine_verdict)
    if [[ -n "$QUARANTINE_URL" ]]; then
        local dest="${QUARANTINE_DEST:-$(pwd)/$(basename "$QUARANTINE_URL" .git)}"
        echo "" >&2
        case "$verdict" in
            CLEAN)
                log "${GREEN}Scan clean, promoting to $dest${NC}"
                promote_repo "$dest"
                ;;
            WARN)
                log "${YELLOW}Warnings found, promoting with caution${NC}"
                promote_repo "$dest"
                ;;
            CRITICAL)
                log "${RED}Critical issues found, NOT promoting${NC}"
                log "  Quarantined repo at: $TARGET_DIR"
                log "  Review findings and decide manually."
                log "  To promote anyway: mv '$TARGET_DIR' '$dest'"
                ;;
        esac
    fi

    # Exit code based on verdict
    case "$verdict" in
        CLEAN)    exit 0 ;;
        WARN)     exit 1 ;;
        CRITICAL) exit 2 ;;
    esac
}

main "$@"
