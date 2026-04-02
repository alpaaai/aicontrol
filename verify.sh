#!/usr/bin/env bash
# AIControl Verification Script
# Run after install.sh: bash verify.sh
set -euo pipefail

PASS=0
FAIL=0
COMPOSE="-f docker-compose.yml -f docker-compose.app.yml"

check() {
  local label="$1"
  local cmd="$2"
  local expected="$3"
  result=$(eval "$cmd" 2>&1) || true
  if echo "$result" | grep -q "$expected"; then
    echo "  PASS  $label"
    PASS=$((PASS + 1))
  else
    echo "  FAIL  $label"
    echo "        Expected to find: '$expected'"
    echo "        Got: $result"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "=== AIControl Verification ==="
echo ""

check "Postgres accepting connections" \
  "docker compose $COMPOSE exec -T postgres pg_isready -U aicontrol -d aicontrol" \
  "accepting connections"

check "OPA reachable" \
  "curl -s --max-time 5 http://localhost:8181/health" \
  "{}"

check "API /health returns ok" \
  "curl -s --max-time 5 http://localhost:8000/health" \
  "ok"

check "API /debug database ok" \
  "curl -s --max-time 5 http://localhost:8000/debug" \
  "\"status\":\"ok\""

check "Migrations applied" \
  "docker compose $COMPOSE exec -T postgres psql -U aicontrol -d aicontrol -c '\dt'" \
  "alembic_version"

check "Dashboard reachable" \
  "curl -s --max-time 10 http://localhost:8501/_stcore/health" \
  "ok"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "Some checks failed. Run: bash diagnose.sh"
  echo "Paste the full output in your support request."
  exit 1
else
  echo "All checks passed. AIControl is ready."
  echo ""
  echo "  Dashboard: http://localhost:8501"
  echo "  API docs:  http://localhost:8000/docs"
  echo ""
fi
