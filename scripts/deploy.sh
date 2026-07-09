#!/usr/bin/env bash
# One-command production deploy for iSoyle. Run it ON the server:
#
#     cd /opt/isoyle && ./scripts/deploy.sh [branch]     # branch defaults to main
#
# Or from a dev machine in a single shot:
#
#     ssh isoyle 'cd /opt/isoyle && ./scripts/deploy.sh'
#
# Steps: pull latest code (re-execing itself so an updated deploy.sh takes
# effect), rebuild images, restart the stack, wait for the backend healthcheck,
# then smoke-test the public /api/health. On failure it exits non-zero, prints
# recent backend logs, and shows the rollback command. Docker layer caching
# makes a no-change rebuild fast.
set -euo pipefail

cd "$(cd "$(dirname "$0")/.." && pwd)" # repo root
BRANCH="${1:-main}"

# --- Pull first, then re-exec the freshly pulled script exactly once, so that
#     changes to this very script are applied on the same run. ---
if [ "${ISOYLE_DEPLOY_REEXEC:-}" != "1" ]; then
	PREV="$(git rev-parse --short HEAD)"
	echo "==> Deploy iSoyle (branch: $BRANCH), current: $PREV"
	git fetch --quiet origin "$BRANCH"
	git checkout --quiet "$BRANCH"
	git pull --ff-only origin "$BRANCH"
	NEW="$(git rev-parse --short HEAD)"
	if [ "$PREV" = "$NEW" ]; then
		echo "==> Already at latest ($NEW) — redeploying anyway"
	else
		echo "==> Updated $PREV -> $NEW"
	fi
	exec env ISOYLE_DEPLOY_REEXEC=1 ISOYLE_DEPLOY_ROLLBACK="$PREV" bash "$0" "$BRANCH"
fi

ROLLBACK="${ISOYLE_DEPLOY_ROLLBACK:-<previous>}"

echo "==> Building images"
docker compose build

echo "==> Starting stack"
docker compose up -d --remove-orphans

echo "==> Waiting for backend healthcheck"
for i in $(seq 1 40); do
	status="$(docker inspect -f '{{.State.Health.Status}}' isoyle-backend-1 2>/dev/null || echo none)"
	if [ "$status" = "healthy" ]; then
		echo "    backend healthy"
		break
	fi
	if [ "$i" -eq 40 ]; then
		echo "!! backend did not become healthy in time" >&2
		docker compose logs --tail=60 backend >&2
		echo "!! Roll back with: git checkout $ROLLBACK && ./scripts/deploy.sh" >&2
		exit 1
	fi
	sleep 3
done

# --- Smoke-test the health endpoint. Prefer the public URL derived from the
#     first host in SITE_ADDRESS; if it is a bare port (e.g. :80), check the
#     backend from inside its container instead. ---
site="$(grep -E '^SITE_ADDRESS=' .env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr ',' ' ' | awk '{print $1}')"
if [ -n "$site" ] && [ "${site#:}" = "$site" ]; then
	url="https://${site}/api/health"
	echo "==> Smoke test: $url"
	curl -fsS -m 15 "$url" >/dev/null
else
	echo "==> Smoke test: backend /api/health (in-container)"
	docker compose exec -T backend python -c \
		"import urllib.request,sys; r=urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=10); sys.exit(0 if r.status==200 else 1)"
fi
echo "    health OK"

echo "==> Deploy complete: $(git rev-parse --short HEAD)"
docker compose ps
