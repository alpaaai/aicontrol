#!/usr/bin/env bash
# AIControl Diagnostic Script
# Run from the repo root: bash diagnose.sh
# Paste the FULL output when filing a support request.
set -euo pipefail

COMPOSE="-f docker-compose.yml -f docker-compose.app.yml"
DIV="========================================"

echo "$DIV"
echo "AIControl Diagnostics — $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "$DIV"

echo ""
echo "--- Service Status ---"
docker compose $COMPOSE ps 2>&1 || echo "ERROR: docker compose ps failed"

echo ""
echo "--- Postgres Health ---"
docker compose $COMPOSE exec -T postgres \
  pg_isready -U aicontrol -d aicontrol 2>&1 \
  || echo "ERROR: postgres not ready"

echo ""
echo "--- Table Row Counts ---"
docker compose $COMPOSE exec -T postgres psql -U aicontrol -d aicontrol -c "
  SELECT 'agents' AS tbl, COUNT(*) FROM agents
  UNION ALL SELECT 'sessions', COUNT(*) FROM sessions
  UNION ALL SELECT 'policies', COUNT(*) FROM policies
  UNION ALL SELECT 'audit_events', COUNT(*) FROM audit_events
  UNION ALL SELECT 'hitl_reviews', COUNT(*) FROM hitl_reviews
  UNION ALL SELECT 'api_tokens', COUNT(*) FROM api_tokens;
" 2>&1 || echo "ERROR: could not query tables"

echo ""
echo "--- OPA Health ---"
curl -s --max-time 5 http://localhost:8181/health 2>&1 \
  || echo "ERROR: OPA not reachable"

echo ""
echo "--- API /health ---"
curl -s --max-time 5 http://localhost:8000/health 2>&1 \
  || echo "ERROR: API not reachable"

echo ""
echo "--- API /debug ---"
curl -s --max-time 5 http://localhost:8000/debug 2>&1 | python3 -m json.tool \
  || echo "ERROR: /debug failed"

echo ""
echo "--- API Logs (last 50 lines) ---"
docker compose $COMPOSE logs --tail=50 api 2>&1 \
  || echo "ERROR: could not fetch api logs"

echo ""
echo "--- Dashboard Logs (last 20 lines) ---"
docker compose $COMPOSE logs --tail=20 dashboard 2>&1 \
  || echo "ERROR: could not fetch dashboard logs"

echo ""
echo "--- OPA Logs (last 20 lines) ---"
docker compose $COMPOSE logs --tail=20 opa 2>&1 \
  || echo "ERROR: could not fetch opa logs"

echo ""
echo "--- Docker Version ---"
docker --version 2>&1

echo ""
echo "$DIV"
echo "Diagnostics complete. Paste this entire output in your support request."
echo "$DIV"
