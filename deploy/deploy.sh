#!/usr/bin/env bash
# Usage: deploy.sh <commit-sha>
# Runs on EC2 as the ubuntu user, triggered by GitHub Actions via SSM.
set -euo pipefail

SHA="$1"
REPO="wdotgonzales/exin-lab-search-prototype-demo"
OWNER="wdotgonzales"
REGION="ap-southeast-1"
APP_DIR="/opt/exin"
DC="docker compose -f docker-compose.prod.yml"

cd "$APP_DIR"
echo "==> Deploying ${SHA}"

echo "==> Fetching compose file"
curl -fsSL "https://raw.githubusercontent.com/${REPO}/${SHA}/docker-compose.prod.yml" \
  -o docker-compose.prod.yml

echo "==> Writing .env.prod from SSM"
aws ssm get-parameters-by-path \
  --path /exin/prod/ \
  --with-decryption \
  --region "$REGION" \
  --query "Parameters[].[Name,Value]" \
  --output text \
  | sed -E 's#^/exin/prod/([^\t]+)\t#\1=#' > .env.prod.new
echo "APP_ENV=production" >> .env.prod.new
chmod 600 .env.prod.new
mv .env.prod.new .env.prod

echo "==> Pinning images to ${SHA}"
cat > .env <<EOF
API_IMAGE=ghcr.io/${OWNER}/exin-api:sha-${SHA}
WEB_IMAGE=ghcr.io/${OWNER}/exin-web:sha-${SHA}
EOF

echo "==> Pulling images"
$DC pull

echo "==> Running migrations"
$DC run --rm --no-deps api alembic upgrade head

echo "==> Starting containers"
$DC up -d --no-build --remove-orphans --wait --wait-timeout 120

echo "==> Health check"
curl -fsSk https://localhost/api/health
echo

echo "==> Cleaning old images"
docker image prune -f > /dev/null

echo "==> Deployed ${SHA}"
