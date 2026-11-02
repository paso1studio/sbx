# sbx

Un contenedor Docker por proyecto para los cron y scripts que se repiten, así la computadora queda limpia. Incluye dos hooks para que Claude Code programe tareas ahí adentro y se entere de cómo terminaron.

## Requisitos

bash, `jq`, `python3` (para el hook) y Docker con `docker compose`.

## Instalación

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
| `sbx cron ls` / `rm nombre` | lista o borra |
| `sbx run nombre comando...` | corre un job una vez ahora |
| `sbx inbox [--all\|--follow]` | jobs que terminaron |
| `sbx claude` | Claude Code dentro del contenedor (para hacer `/login`) |
| `sbx ps` | todos los sandbox de la máquina |

Los secretos de cada proyecto van en `~/.config/sbx/<carpeta-del-proyecto>.env` (permisos 600). Los `.env` del repo no se ven adentro del contenedor: `sbx` los tapa con `/dev/null`.

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
