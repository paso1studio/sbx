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
# El crontab se recarga solo con SIGUSR2 (`sbx cron add`, `rm` y `reload`). Sin -inotify: con
# `sbx cron add` (>>) recargaba dos veces, y con `sbx cron rm` (sed -i, archivo nuevo) perdía la
# vigilancia del archivo y no se enteraba de ese cambio ni de los siguientes.
exec supercronic -passthrough-logs "$CRONTAB"
