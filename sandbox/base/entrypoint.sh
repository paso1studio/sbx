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
# Recarga al volver del sueño. La VM de Docker Desktop no cuenta el tiempo que la Mac está
# dormida, y supercronic agenda cada job como "dentro de X tiempo": después de dormir una hora,
# todo sale una hora tarde. Cada SBX_SUENO_CADA segundos se compara cuánto avanzó el reloj de
# pared contra el del sistema (/proc/uptime, que tampoco cuenta el sueño); si el de pared se
# adelantó más de SBX_SUENO_UMBRAL, se manda SIGUSR2 y supercronic reagenda contra la hora real.
# $$ es este proceso, que con el exec de abajo pasa a ser supercronic.
vigilar_sueno() {
  local pid=$1 cada=${SBX_SUENO_CADA:-60} umbral=${SBX_SUENO_UMBRAL:-60}
  local pared sistema pared_antes sistema_antes salto
  pared_antes=$(date +%s); sistema_antes=$(cut -d. -f1 /proc/uptime)
  while sleep "$cada"; do
    pared=$(date +%s); sistema=$(cut -d. -f1 /proc/uptime)
    salto=$(( (pared - pared_antes) - (sistema - sistema_antes) ))
    if [ "$salto" -gt "$umbral" ]; then
      echo "[sbx] el reloj saltó ${salto}s (la Mac estuvo dormida): recargo los horarios"
      kill -USR2 "$pid" 2>/dev/null || true
    fi
    pared_antes=$pared; sistema_antes=$sistema
  done
}
vigilar_sueno $$ &
# El crontab se recarga solo con SIGUSR2 (`sbx cron add`, `rm` y `reload`). Sin -inotify: con
# `sbx cron add` (>>) recargaba dos veces, y con `sbx cron rm` (sed -i, archivo nuevo) perdía la
# vigilancia del archivo y no se enteraba de ese cambio ni de los siguientes.
exec supercronic -passthrough-logs "$CRONTAB"
