#!/bin/sh
# Runs on the Yandex Cloud VM (/opt/domovoy): pulls prebuilt images from
# Container Registry and restarts the prod stack. Called by GitHub Actions
# (.github/workflows/deploy.yml) after it copies compose.yaml, infra/ and
# ml/models here. Manual rollback: ./infra/yc/deploy.sh <older commit sha>.
#
# /opt/domovoy/.env (root, not in git): DOMAIN, IMAGE_REPO, IMAGE_TAG,
# POSTGRES_PASSWORD, SEED_DEMO. /opt/domovoy/backend/.env: bot settings.
set -eu
cd "$(dirname "$0")/../.."

TAG="${1:?usage: deploy.sh <image tag>}"

# The VM service account may pull from the registry; its IAM token lives
# 12 h, so log in on every deploy.
curl -sf -H "Metadata-Flavor: Google" \
    http://169.254.169.254/computeMetadata/v1/instance/service-accounts/default/token \
    | jq -r .access_token \
    | docker login --username iam --password-stdin cr.yandex >/dev/null

sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=${TAG}/" .env

docker compose --profile prod pull --quiet
docker compose --profile prod up -d --no-build --remove-orphans

# Migrations run in the bot entrypoint; /ready answers once the app is up.
for _ in $(seq 1 30); do
    if curl -sf http://127.0.0.1:8080/ready >/dev/null; then
        echo "deployed ${TAG}"
        docker image prune -f >/dev/null
        exit 0
    fi
    sleep 3
done
echo "bot is not ready after 90 s" >&2
docker compose logs --tail 80 bot >&2
exit 1
