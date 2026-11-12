#!/bin/sh
# Vigía de sbx: cuando Docker arranca, a veces no relevanta todos los sandbox aunque tengan
# restart: unless-stopped. Este contenedor arranca con Docker (restart: always) y levanta
# los sandbox que ese arranque dejó caídos.
#
# Solo toca contenedores sbx-* que cayeron en este mismo arranque (FinishedAt cercano a la
# hora en que arrancó el vigía) y solo durante los primeros minutos. Así no revive uno que
# alguien frenó a mano más tarde, ni uno viejo cuyo proyecto quizá ya no existe: para esos
# está `sbx levantar`, que corre en la Mac y puede mirar si la carpeta sigue ahí.
set -u

ESPERA="${VIGIA_ESPERA:-30}"        # segundos hasta el primer intento (carpetas compartidas listas)
INTENTOS="${VIGIA_INTENTOS:-10}"    # un intento por minuto
VENTANA="${VIGIA_VENTANA:-300}"     # cuánto antes del arranque del vigía puede haber caído

inicio=$(date +%s)
log() { echo "$(date '+%Y-%m-%dT%H:%M:%S%z') vigia: $*"; }

# Nombres de los sbx-* caídos en este arranque de Docker y con política de reinicio.
caidos() {
  docker ps -a --filter "name=^sbx-" --filter status=exited --format '{{.Names}}' |
  while IFS= read -r nombre; do
    datos=$(docker inspect -f '{{.HostConfig.RestartPolicy.Name}} {{.State.FinishedAt}}' "$nombre" 2>/dev/null) || continue
    politica=${datos%% *}
    fin=${datos#* }
    case "$politica" in unless-stopped|always) ;; *) continue ;; esac
    fin_s=$(date -u -D '%Y-%m-%dT%H:%M:%S' -d "${fin%%.*}" +%s 2>/dev/null) || continue
    [ "$fin_s" -ge $((inicio - VENTANA)) ] && [ "$fin_s" -le $((inicio + 60)) ] && echo "$nombre"
  done
}

log "arrancó; primer intento en ${ESPERA}s"
sleep "$ESPERA"
n=1
while [ "$n" -le "$INTENTOS" ]; do
  pendientes=$(caidos)
  if [ -z "$pendientes" ]; then
    log "no quedan sandbox caídos de este arranque"
    break
  fi
  for nombre in $pendientes; do
    if docker start "$nombre" >/dev/null 2>&1; then
      log "levantado: $nombre"
    else
      log "intento $n: no se pudo levantar $nombre"
    fi
  done
  n=$((n + 1))
  sleep 60
done
[ "$n" -gt "$INTENTOS" ] && log "se agotaron los intentos; quedó caído: $(caidos | tr '\n' ' ')"

# Queda vivo sin hacer nada: si saliera, restart: always lo relanzaría en bucle.
log "en espera hasta el próximo arranque de Docker"
exec tail -f /dev/null
