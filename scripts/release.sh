#!/usr/bin/env bash
# Manual release script — build and push both images to ghcr.io
# Usage: bash scripts/release.sh v0.1.0
set -euo pipefail

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
  echo "Usage: bash scripts/release.sh v0.1.0"
  exit 1
fi

OWNER=$(git remote get-url origin | sed 's/.*github.com[:/]\([^/]*\).*/\1/' | tr '[:upper:]' '[:lower:]')
REGISTRY="ghcr.io"

echo "Building and pushing AIControl $VERSION"
echo "Registry: $REGISTRY/$OWNER"
echo ""

# Login check
if ! docker info 2>/dev/null | grep -q "Username"; then
  echo "Log in to ghcr.io first:"
  echo "  echo \$GITHUB_TOKEN | docker login ghcr.io -u <username> --password-stdin"
  exit 1
fi

# Build API
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag "$REGISTRY/$OWNER/aicontrol-api:$VERSION" \
  --tag "$REGISTRY/$OWNER/aicontrol-api:latest" \
  --push \
  .

# Build Dashboard
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --file Dockerfile.dashboard \
  --tag "$REGISTRY/$OWNER/aicontrol-dashboard:$VERSION" \
  --tag "$REGISTRY/$OWNER/aicontrol-dashboard:latest" \
  --push \
  .

echo ""
echo "Released $VERSION to ghcr.io/$OWNER"
echo ""
echo "Update docker-compose.app.yml to use:"
echo "  image: $REGISTRY/$OWNER/aicontrol-api:$VERSION"
echo "  image: $REGISTRY/$OWNER/aicontrol-dashboard:$VERSION"
