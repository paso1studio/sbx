#!/usr/bin/env bash
# Arranca supercronic leyendo el crontab del proyecto (montado en solo lectura).
# Si el proyecto tiene .sandbox/servicio.sh (un proceso que tiene que estar siempre
# corriendo, como un listener), lo mantiene vivo en segundo plano: si se cae, deja un
# evento en el inbox y se vuelve a lanzar a los 30 segundos.
set -euo pipefail
CRONTAB=/workspace/.sandbox/crontab
SERVICIO=/workspace/.sandbox/servicio.sh
mkdir -p /out/runs
touch /out/events.jsonl
[ -f "$CRONTAB" ] || { echo "No existe $CRONTAB"; exit 1; }
if [ -f "$SERVICIO" ]; then
  ( while true; do sbx-run servicio bash "$SERVICIO" || true; sleep 30; done ) &
fi
# -inotify recarga solo cuando el archivo cambia; además `sbx cron reload` manda SIGUSR2.
exec supercronic -inotify -passthrough-logs "$CRONTAB"
