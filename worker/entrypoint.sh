#!/usr/bin/env bash
set -euo pipefail
# Heartbeat for the compose healthcheck: written every 5s while Celery is alive.
( while true; do date +%s > /tmp/churnmod-worker-heartbeat; sleep 5; done ) &
exec celery -A src.config.celery_app worker --loglevel=info --concurrency=2 --without-gossip --without-mingle
