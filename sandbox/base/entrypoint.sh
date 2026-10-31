#!/usr/bin/env bash
# Arranca supercronic leyendo el crontab del proyecto (montado en solo lectura).
set -euo pipefail
CRONTAB=/workspace/.sandbox/crontab
mkdir -p /out/runs
touch /out/events.jsonl
[ -f "$CRONTAB" ] || { echo "No existe $CRONTAB"; exit 1; }
# -inotify recarga solo cuando el archivo cambia; además `sbx cron reload` manda SIGUSR2.
exec supercronic -inotify -passthrough-logs "$CRONTAB"
