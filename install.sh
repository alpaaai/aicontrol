#!/usr/bin/env bash
# AIControl Install Script
# Run from the repo root: bash install.sh
set -euo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${BOLD}=== AIControl Installer ===${NC}"
echo ""

# Check dependencies
for cmd in docker curl python3; do
  if ! command -v "$cmd" &>/dev/null; then
    echo -e "${RED}ERROR: $cmd is required but not installed.${NC}"
    exit 1
  fi
done
if ! docker compose version &>/dev/null; then
  echo -e "${RED}ERROR: docker compose v2 is required.${NC}"
  exit 1
fi

# Generate or load .env
if [ -f .env ]; then
  echo -e "${YELLOW}[skip]${NC} .env already exists — using existing configuration."
  echo "       Delete .env to reconfigure from scratch."
else
  echo -e "${BOLD}Let's configure AIControl.${NC}"
  echo ""

  read -rp "PostgreSQL password (default: auto-generated): " DB_PASS
  DB_PASS=${DB_PASS:-$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")}

  read -rp "Secret key for JWT signing (default: auto-generated): " SECRET_KEY
  SECRET_KEY=${SECRET_KEY:-$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")}

  read -rp "Slack bot token (xoxb-..., or press Enter to skip): " SLACK_TOKEN
  SLACK_TOKEN=${SLACK_TOKEN:-xoxb-placeholder}

  read -rp "Slack signing secret (or press Enter to skip): " SLACK_SECRET
  SLACK_SECRET=${SLACK_SECRET:-placeholder}

  read -rp "Slack review channel (default: #aicontrol-reviews): " SLACK_CHANNEL
  SLACK_CHANNEL=${SLACK_CHANNEL:-#aicontrol-reviews}

  cat > .env << ENVEOF
# PostgreSQL
POSTGRES_USER=aicontrol
POSTGRES_PASSWORD=${DB_PASS}
POSTGRES_DB=aicontrol
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# SQLAlchemy
DATABASE_URL=postgresql+asyncpg://aicontrol:${DB_PASS}@postgres:5432/aicontrol

# OPA
OPA_URL=http://opa:8181

# App
APP_ENV=production
SECRET_KEY=${SECRET_KEY}

# Slack HITL
SLACK_BOT_TOKEN=${SLACK_TOKEN}
SLACK_SIGNING_SECRET=${SLACK_SECRET}
SLACK_REVIEW_CHANNEL=${SLACK_CHANNEL}
ENVEOF

  echo ""
  echo -e "${GREEN}[done]${NC} .env created."
fi

# Pull images
echo ""
echo "[1/4] Pulling Docker images..."
docker compose -f docker-compose.yml -f docker-compose.app.yml pull --quiet
echo -e "${GREEN}[done]${NC} Images pulled."

# Start infra first
echo "[2/4] Starting infrastructure (postgres + opa)..."
docker compose -f docker-compose.yml up -d
echo -e "      Waiting for postgres..."
for i in $(seq 1 30); do
  if docker compose -f docker-compose.yml exec -T postgres \
     pg_isready -U aicontrol -d aicontrol &>/dev/null; then
    break
  fi
  sleep 2
  [ "$i" -eq 30 ] && { echo -e "${RED}ERROR: Postgres not ready.${NC}"; exit 1; }
done
echo -e "${GREEN}[done]${NC} Infrastructure ready."

# Run migrations
echo "[3/4] Running database migrations..."
docker compose -f docker-compose.yml -f docker-compose.app.yml \
  run --rm api alembic upgrade head
echo -e "${GREEN}[done]${NC} Migrations applied."

# Start app services
docker compose -f docker-compose.yml -f docker-compose.app.yml up -d
echo -e "${GREEN}[done]${NC} All services started."

# Issue first admin token
echo ""
echo "[4/4] Issuing initial admin token..."
echo ""
docker compose -f docker-compose.yml -f docker-compose.app.yml \
  exec api python scripts/issue_token.py \
  --role admin --desc "Initial admin token"

echo ""
echo -e "${BOLD}${GREEN}=== Installation complete ===${NC}"
echo ""
echo "  API:       http://localhost:8000"
echo "  Dashboard: http://localhost:8501"
echo "  Health:    http://localhost:8000/health"
echo "  Debug:     http://localhost:8000/debug"
echo ""
echo -e "${YELLOW}Save the admin token above — it will not be shown again.${NC}"
echo ""
echo "Next: bash verify.sh"
echo ""
