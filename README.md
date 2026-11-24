# sbx

Un contenedor Docker por proyecto para los cron y scripts que se repiten, así la computadora queda limpia. Incluye dos hooks para que Claude Code programe tareas ahí adentro y se entere de cómo terminaron.

## Requisitos

bash, `jq`, `python3` (para el hook) y Docker con `docker compose`.

## Instalación

> **Antes de instalar:** `install.sh` modifica tu configuración de Claude Code. Agrega tres hooks (PreToolUse, SessionStart y UserPromptSubmit) a `~/.claude/settings.json`, enlaza dos scripts en `~/.claude/hooks/` y crea `~/.local/bin/sbx`. Antes de tocar `settings.json` guarda una copia en `settings.json.bak-sbx`, y un archivo que ya exista en el destino se renombra a `.antes-de-sbx`. Para deshacerlo, restaurá esa copia y borrá los enlaces.
>
> El hook `bloquear-cron-host.py` frena `crontab`, `at`, `launchctl` y `brew services` en esa máquina, para todos los proyectos. Está pensado para macOS con Docker Desktop.

```bash
git clone <url-de-este-repo> ~/workspace/personal/sbx
~/workspace/personal/sbx/install.sh
```

Enlaza `bin/sbx` → `~/.local/bin/sbx` y los hooks → `~/.claude/hooks/`, registra los hooks en `~/.claude/settings.json` (respaldo en `settings.json.bak-sbx`) y construye la imagen base. Se puede correr las veces que haga falta.

## Sandbox por proyecto

Cada proyecto lleva un `.sandbox/` con su contenedor Docker. Los cron corren ahí adentro con [supercronic](https://github.com/aptible/supercronic), nunca en el host.

```
proyecto/
└── .sandbox/
    ├── Dockerfile        FROM sbx-base:alpine | sbx-base:ubuntu
    ├── compose.yaml      proyecto → /workspace (solo lectura), .sandbox/out → /out
    ├── crontab           los cron, versionados con el proyecto
    ├── packages.txt      paquetes apk/apt
    ├── requirements.txt  dependencias pip
    └── out/              logs, resultados y events.jsonl (fuera de git)
```

| Comando | Qué hace |
|---|---|
| `sbx init [alpine\|ubuntu]` | crea `.sandbox/` |
| `sbx up` / `down` / `sh` / `logs` | maneja el contenedor |
| `sbx cron add "*/15 * * * *" nombre python3 scripts/x.py` | agrega un cron y lo recarga |
| `sbx cron ls` / `rm nombre` | lista o borra (y recarga) |
| `sbx cron reload` | relee el crontab después de editarlo a mano: el contenedor no se entera solo |
| `sbx run nombre comando...` | corre un job una vez ahora |
| `sbx inbox [--all\|--follow]` | jobs que terminaron |
| `sbx claude` | Claude Code dentro del contenedor (para hacer `/login`) |
| `sbx ps` | todos los sandbox de la máquina |
| `sbx levantar` | arranca todos los sandbox caídos de la máquina |
| `sbx vigia up` / `down` / `logs` | contenedor que los relevanta solo cuando arranca Docker |

Los secretos de cada proyecto van en `~/.config/sbx/<carpeta-del-proyecto>.env` (permisos 600). Los `.env` del repo no se ven adentro del contenedor: `sbx` los tapa con `/dev/null`.

## Sandbox caídos tras un reinicio

Los sandbox llevan `restart: unless-stopped`, pero Docker Desktop no siempre los relevanta a todos cuando arranca: alguno puede quedar en `Exited`, y cuál varía de un arranque a otro. Mientras está caído, sus cron no corren.

- `sbx levantar` arranca todos los contenedores `sbx-*` caídos, tal como estaban (no reconstruye la imagen ni recalcula las máscaras de los `.env`). Saltea los que ya no tienen la carpeta del proyecto, para que Docker no cree carpetas vacías al montarla.
- `sbx vigia up` deja corriendo un contenedor (`sandbox/vigia/`) que arranca con Docker y, a los 30 segundos, levanta los sandbox que ese arranque dejó caídos; reintenta una vez por minuto, hasta 10 veces. No toca un sandbox frenado a mano más tarde ni uno caído de antes: para esos está `sbx levantar`. Se instala una sola vez para toda la máquina.

El vigía monta el socket de Docker, así que puede manejar todo Docker. Por eso corre sin red, con el sistema de archivos en solo lectura, sin capacidades y con el script dentro de la imagen. Solo sirve si Docker arranca: conviene activar en Docker Desktop el inicio al abrir sesión.

## Cómo se entera Claude Code

`sbx-run` envuelve cada job: guarda el log en `out/runs/` y agrega una línea a `out/events.jsonl`. El hook `sandbox-inbox.sh` (SessionStart y UserPromptSubmit) le pasa a Claude los eventos que todavía no vio. Para esperar un job en vivo: Monitor con `sbx inbox --follow`.

## Bloqueo de cron en el host

`bloquear-cron-host.py` (PreToolUse) frena `crontab`, `at`, `launchctl load/bootstrap`, `brew services start` y escrituras en `~/Library/LaunchAgents`, y le indica a Claude que use `sbx`. Ignora el cuerpo de los heredocs, que es texto y no comandos.

## Regla sugerida para tu CLAUDE.md

El hook hace cumplir la regla; esto le explica a Claude cómo trabajar con ella desde el principio.

```markdown
## Los cron corren en el sandbox del proyecto

- Todo cron o proceso que se repite corre dentro del contenedor del proyecto, nunca en el host. Nada de `crontab`, `launchctl`, `brew services` ni `at`.
- El sandbox es la carpeta `.sandbox/` del proyecto. Se maneja con `sbx`: `sbx init` (o `sbx init ubuntu`) → `sbx up`, después `sbx cron add "<expr>" <nombre> <comando...>`. `sbx run <nombre> <comando...>` lo prueba una vez.
- Dentro del contenedor el código está en `/workspace` en solo lectura. Todo lo que un job genere va a `/out` (`.sandbox/out/` en el host).
- Cada job que termina deja un evento en `.sandbox/out/events.jsonl`; un hook te pasa los nuevos. Para esperar uno, usá Monitor con `sbx inbox --follow`.
```
