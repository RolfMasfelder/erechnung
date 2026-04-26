#!/bin/bash
# =============================================================================
# Security Audit Script for eRechnung Django App
# =============================================================================
# Führt umfassende Security-Checks durch:
# 1. Python Dependency Vulnerabilities (pip-audit)
# 2. Frontend Dependency Vulnerabilities (npm audit)
# 3. Django Security Settings (manage.py check --deploy)
# 4. Static Code Analysis (bandit)
# 5. Container Security (trivy, wenn verfügbar)
# 6. Secrets Detection (grundlegend)
#
# Usage:
#   ./scripts/security_audit.sh           # Vollständiger Audit
#   ./scripts/security_audit.sh --quick   # Nur schnelle Checks
#   ./scripts/security_audit.sh --ci      # CI-Modus (exit code bei Fehlern)
#
# =============================================================================

set -o pipefail

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Konfiguration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
REPORT_DIR="$PROJECT_ROOT/security-reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="$REPORT_DIR/security_audit_$TIMESTAMP.txt"

# Tracking
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNINGS=0

# Flags
QUICK_MODE=false
CI_MODE=false

# Parse Arguments
for arg in "$@"; do
    case $arg in
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --ci)
            CI_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--quick] [--ci] [--help]"
            echo ""
            echo "Options:"
            echo "  --quick    Run only fast checks (skip container scan)"
            echo "  --ci       CI mode - exit with code 1 on any failure"
            echo "  --help     Show this help message"
            exit 0
            ;;
    esac
done

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${YELLOW}━━━ $1 ━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED_CHECKS++))
}

print_failure() {
    echo -e "${RED}✗ $1${NC}"
    ((FAILED_CHECKS++))
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
    ((WARNINGS++))
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_command() {
    command -v "$1" &> /dev/null
}

is_docker_running() {
    docker info &> /dev/null
}

is_container_running() {
    docker compose ps --services --filter "status=running" 2>/dev/null | grep -q "web"
}

# =============================================================================
# Security Checks
# =============================================================================

check_python_dependencies() {
    print_section "Python Dependency Security (pip-audit)"
    ((TOTAL_CHECKS++))

    local result

    if is_container_running; then
        print_info "Running pip-audit in Docker container..."

        # pip-audit ist in requirements.txt enthalten
        result=$(docker compose exec -T web pip-audit 2>&1)
        local exit_code=$?

        if [ $exit_code -eq 0 ]; then
            print_success "No known vulnerabilities found in Python dependencies"
            echo "$result" | head -20
        else
            print_failure "Vulnerabilities found in Python dependencies"
            echo "$result"
        fi
    else
        print_warning "Docker container not running - checking local environment"

        if check_command pip-audit; then
            result=$(pip-audit -r "$PROJECT_ROOT/requirements.txt" 2>&1)
            local exit_code=$?

            if [ $exit_code -eq 0 ]; then
                print_success "No known vulnerabilities found"
            else
                print_failure "Vulnerabilities found"
                echo "$result"
            fi
        else
            print_warning "pip-audit not installed. Install with: pip install pip-audit"
        fi
    fi
}

check_npm_dependencies() {
    print_section "Frontend Dependency Security (npm audit)"
    ((TOTAL_CHECKS++))

    local frontend_dir="$PROJECT_ROOT/frontend"

    if [ ! -d "$frontend_dir" ]; then
        print_warning "Frontend directory not found"
        return
    fi

    cd "$frontend_dir" || return

    if [ ! -f "package-lock.json" ]; then
        print_warning "package-lock.json not found - run 'npm install' first"
        cd "$PROJECT_ROOT" || return
        return
    fi

    print_info "Running npm audit..."
    local result
    result=$(docker compose exec -T frontend-e2e npm audit --json 2>/dev/null || npm audit --json 2>/dev/null)
    local exit_code=$?

    # Parse JSON for summary
    local vulnerabilities
    vulnerabilities=$(echo "$result" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    meta = data.get('metadata', {}).get('vulnerabilities', {})
    total = sum(meta.values()) if meta else 0
    critical = meta.get('critical', 0)
    high = meta.get('high', 0)
    print(f'Total: {total}, Critical: {critical}, High: {high}')
except:
    print('Unable to parse')
" 2>/dev/null)

    if [ $exit_code -eq 0 ]; then
        print_success "No vulnerabilities found in npm dependencies"
    else
        if echo "$vulnerabilities" | grep -q "Critical: 0" && echo "$vulnerabilities" | grep -q "High: 0"; then
            print_warning "Low/moderate vulnerabilities found: $vulnerabilities"
        else
            print_failure "Security vulnerabilities found: $vulnerabilities"
            npm audit --audit-level=high 2>/dev/null | head -30
        fi
    fi

    cd "$PROJECT_ROOT" || return
}

check_django_security() {
    print_section "Django Security Settings (--deploy check)"
    ((TOTAL_CHECKS++))

    local result

    if is_container_running; then
        print_info "Running Django security check in container..."
        result=$(docker compose exec -T web bash -lc 'cd /app && set -a; [ -f ./.env ] && . ./.env; set +a; python project_root/manage.py check --deploy' 2>&1)
        local exit_code=$?

        if [ $exit_code -eq 0 ]; then
            print_success "Django security check passed"
        else
            # Django check --deploy gibt Warnungen aus, nicht unbedingt Fehler
            if echo "$result" | grep -q "ERRORS"; then
                print_failure "Django security errors found"
            else
                print_warning "Django security warnings (review recommended)"
            fi
            echo "$result" | grep -E "(WARNINGS|ERRORS|security\.|W0[0-9]{2}|E[0-9]{3})" | head -20
        fi
    else
        print_warning "Docker container not running - skipping Django check"
    fi
}

check_bandit_analysis() {
    print_section "Static Security Analysis (Bandit)"
    ((TOTAL_CHECKS++))

    local target_dir="$PROJECT_ROOT/project_root/invoice_app"

    if is_container_running; then
        print_info "Running Bandit in Docker container..."

        # bandit ist in requirements.txt enthalten
        local result
        result=$(docker compose exec -T web bash -lc 'bandit -r /app/project_root/invoice_app \
            --exclude /app/project_root/invoice_app/tests,/app/project_root/invoice_app/migrations \
            -f txt --severity-level medium --confidence-level medium -q' 2>&1)
        local exit_code=$?

        if [ $exit_code -eq 0 ] || [ -z "$result" ]; then
            print_success "No medium/high severity issues found"
        else
            local issue_count
            issue_count=$(echo "$result" | grep -c "Issue:" || echo "0")
            print_warning "Found $issue_count potential security issues"
            echo "$result" | head -40
        fi
    else
        if check_command bandit; then
            print_info "Running Bandit locally..."
            local result
            result=$(bandit -r "$target_dir" -f txt --severity-level medium -q 2>&1)
            local exit_code=$?

            if [ $exit_code -eq 0 ]; then
                print_success "No medium/high severity issues found"
            else
                print_warning "Potential security issues found"
                echo "$result" | head -40
            fi
        else
            print_warning "Bandit not installed. Install with: pip install bandit"
        fi
    fi
}

check_secrets_detection() {
    print_section "Secrets Detection (Basic Patterns)"
    ((TOTAL_CHECKS++))

    print_info "Scanning for potential hardcoded secrets..."

    # Patterns für potentielle Secrets
    local patterns=(
        "password\s*=\s*['\"][^'\"]+['\"]"
        "secret\s*=\s*['\"][^'\"]+['\"]"
        "api_key\s*=\s*['\"][^'\"]+['\"]"
        "token\s*=\s*['\"][^'\"]+['\"]"
        "AWS_SECRET"
        "PRIVATE_KEY"
    )

    local found_secrets=false
    local exclude_dirs="--exclude-dir=.git --exclude-dir=node_modules --exclude-dir=__pycache__ --exclude-dir=htmlcov --exclude-dir=.venv --exclude-dir=venv"
    local exclude_files="--exclude=*.pyc --exclude=*.log --exclude=security_audit.sh"

    for pattern in "${patterns[@]}"; do
        local matches
        matches=$(grep -rniE "$pattern" "$PROJECT_ROOT" $exclude_dirs $exclude_files 2>/dev/null | \
            grep -v "\.env\.example" | \
            grep -v "test" | \
            grep -v "fixture" | \
            grep -v "settings\.py.*environ" | \
            grep -v "os\.environ" | \
            head -5)

        if [ -n "$matches" ]; then
            found_secrets=true
            echo -e "${YELLOW}Pattern: $pattern${NC}"
            echo "$matches"
            echo ""
        fi
    done

    if [ "$found_secrets" = true ]; then
        print_warning "Potential hardcoded secrets found (review manually)"
    else
        print_success "No obvious hardcoded secrets detected"
    fi
}

check_env_file() {
    print_section ".env File Security"
    ((TOTAL_CHECKS++))

    local env_file="$PROJECT_ROOT/.env"

    if [ -f "$env_file" ]; then
        # Prüfe ob .env von git ignoriert wird (unterstützt auch Wildcards wie .env*)
        if git check-ignore -q "$env_file" 2>/dev/null; then
            print_success ".env is ignored by git"
        elif grep -qE "^\.env(\*|$)" "$PROJECT_ROOT/.gitignore" 2>/dev/null; then
            print_success ".env is in .gitignore (via pattern)"
        else
            print_failure ".env is NOT in .gitignore - SECURITY RISK!"
        fi

        # Prüfe DEBUG Setting
        if grep -qE "^DEBUG\s*=\s*(True|true|1)" "$env_file" 2>/dev/null; then
            print_warning "DEBUG=True detected (ensure this is not production)"
        fi

        # Prüfe SECRET_KEY
        if grep -qE "^DJANGO_SECRET_KEY\s*=\s*your-secret-key" "$env_file" 2>/dev/null || \
           grep -qE "^DJANGO_SECRET_KEY\s*=\s*changeme" "$env_file" 2>/dev/null; then
            print_failure "Default/weak SECRET_KEY detected!"
        else
            print_success "SECRET_KEY appears to be customized"
        fi
    else
        print_info ".env file not found (using environment variables or defaults)"
    fi
}

check_container_security() {
    print_section "Container Security Scan (Trivy)"
    ((TOTAL_CHECKS++))

    if [ "$QUICK_MODE" = true ]; then
        print_info "Skipped in quick mode"
        return
    fi

    if ! check_command trivy; then
        print_warning "Trivy not installed. Install from: https://trivy.dev"
        print_info "  brew install trivy (macOS)"
        print_info "  sudo apt-get install trivy (Debian/Ubuntu)"
        return
    fi

    if ! is_docker_running; then
        print_warning "Docker not running - skipping container scan"
        return
    fi

    # Finde das Image
    local image_name
    image_name=$(docker compose images -q web 2>/dev/null | head -1)

    if [ -z "$image_name" ]; then
        print_warning "No web container image found"
        return
    fi

    print_info "Scanning container image..."
    local result
    result=$(trivy image --severity HIGH,CRITICAL --quiet "$image_name" 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        if echo "$result" | grep -q "Total: 0"; then
            print_success "No high/critical vulnerabilities in container"
        else
            print_warning "Container vulnerabilities found:"
            echo "$result" | head -30
        fi
    else
        print_warning "Container scan failed or found issues"
        echo "$result" | head -20
    fi
}

check_dockerfile_security() {
    print_section "Dockerfile Security Best Practices"
    ((TOTAL_CHECKS++))

    local dockerfile="$PROJECT_ROOT/Dockerfile"
    local issues=0

    if [ ! -f "$dockerfile" ]; then
        print_warning "Dockerfile not found"
        return
    fi

    # Check: Running as root
    if ! grep -q "^USER" "$dockerfile"; then
        print_warning "No USER directive - container may run as root"
        ((issues++))
    else
        print_success "USER directive found"
    fi

    # Check: Latest tag
    if grep -qE "^FROM.*:latest" "$dockerfile"; then
        print_warning "Using ':latest' tag - use specific versions"
        ((issues++))
    else
        print_success "Specific image versions used"
    fi

    # Check: k8s manifests for :latest
    local k8s_latest_count
    k8s_latest_count=$(grep -rl ':latest' infra/k8s/k3s/manifests/ 2>/dev/null | wc -l)
    if [ "$k8s_latest_count" -gt 0 ]; then
        print_warning "$k8s_latest_count k8s manifest(s) use ':latest' tag — use versioned tags via kustomize"
        ((issues++))
    else
        print_success "No ':latest' in k8s manifests"
    fi

    # Check: HEALTHCHECK
    if grep -q "^HEALTHCHECK" "$dockerfile"; then
        print_success "HEALTHCHECK defined"
    else
        print_info "No HEALTHCHECK in Dockerfile (optional)"
    fi

    if [ $issues -eq 0 ]; then
        print_success "Dockerfile follows security best practices"
    fi
}

check_security_headers() {
    print_section "API Gateway Security Headers"
    ((TOTAL_CHECKS++))

    local nginx_conf="$PROJECT_ROOT/infra/api-gateway/api-gateway-https.conf"

    if [ ! -f "$nginx_conf" ]; then
        print_warning "API Gateway config not found"
        return
    fi

    local headers_found=0
    local expected_headers=("X-Frame-Options" "X-Content-Type-Options" "X-XSS-Protection" "Strict-Transport-Security")

    for header in "${expected_headers[@]}"; do
        if grep -q "$header" "$nginx_conf"; then
            ((headers_found++))
        else
            print_warning "Missing header: $header"
        fi
    done

    if [ $headers_found -eq ${#expected_headers[@]} ]; then
        print_success "All recommended security headers configured"
    else
        print_warning "$headers_found/${#expected_headers[@]} security headers found"
    fi
}

# =============================================================================
# Report Generation
# =============================================================================

generate_report() {
    mkdir -p "$REPORT_DIR"

    {
        echo "=============================================="
        echo "  SECURITY AUDIT REPORT"
        echo "  Project: eRechnung Django App"
        echo "  Date: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "=============================================="
        echo ""
        echo "SUMMARY"
        echo "-------"
        echo "Total Checks:  $TOTAL_CHECKS"
        echo "Passed:        $PASSED_CHECKS"
        echo "Failed:        $FAILED_CHECKS"
        echo "Warnings:      $WARNINGS"
        echo ""
        echo "Score: $PASSED_CHECKS / $TOTAL_CHECKS"
        echo ""

        if [ $FAILED_CHECKS -gt 0 ]; then
            echo "⚠️  ATTENTION: $FAILED_CHECKS critical issues require immediate action!"
        fi

        echo ""
        echo "=============================================="
        echo "Run './scripts/security_audit.sh' for details"
        echo "=============================================="
    } > "$REPORT_FILE"

    print_info "Report saved to: $REPORT_FILE"
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    print_header "🔐 Security Audit - eRechnung Django App"

    echo "Project: $PROJECT_ROOT"
    echo "Mode: $([ "$QUICK_MODE" = true ] && echo "Quick" || echo "Full")"
    echo "CI Mode: $([ "$CI_MODE" = true ] && echo "Yes" || echo "No")"
    echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"

    # Run all checks
    check_python_dependencies
    check_npm_dependencies
    check_django_security
    check_bandit_analysis
    check_secrets_detection
    check_env_file
    check_dockerfile_security
    check_security_headers
    check_container_security

    # Summary
    print_header "📊 Audit Summary"

    echo "Total Checks:  $TOTAL_CHECKS"
    echo -e "Passed:        ${GREEN}$PASSED_CHECKS${NC}"
    echo -e "Failed:        ${RED}$FAILED_CHECKS${NC}"
    echo -e "Warnings:      ${YELLOW}$WARNINGS${NC}"
    echo ""

    local score=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    echo "Security Score: $score%"

    if [ $score -ge 90 ]; then
        echo -e "${GREEN}Rating: A - Excellent${NC}"
    elif [ $score -ge 80 ]; then
        echo -e "${GREEN}Rating: B - Good${NC}"
    elif [ $score -ge 70 ]; then
        echo -e "${YELLOW}Rating: C - Needs Improvement${NC}"
    else
        echo -e "${RED}Rating: D - Critical Issues${NC}"
    fi

    # Generate report
    generate_report

    echo ""
    echo "Completed: $(date '+%Y-%m-%d %H:%M:%S')"

    # Exit code for CI
    if [ "$CI_MODE" = true ] && [ $FAILED_CHECKS -gt 0 ]; then
        echo ""
        echo -e "${RED}CI Mode: Exiting with error due to $FAILED_CHECKS failures${NC}"
        exit 1
    fi

    exit 0
}

# Run main
main
