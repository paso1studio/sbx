# macbook

Configuración de esta MacBook versionada, para poder formatear sin perder nada.

```bash
./install.sh
```

Enlaza `claude/CLAUDE.md` → `~/.claude/CLAUDE.md`, los hooks → `~/.claude/hooks/`, `bin/sbx` → `~/.local/bin/sbx`, registra los hooks en `~/.claude/settings.json` (respaldo en `settings.json.bak-macbook`) y construye la imagen base. Se puede correr las veces que haga falta.

## Sandbox por proyecto

Cada proyecto lleva un `.sandbox/` con su contenedor Docker. Los cron corren ahí adentro con [supercronic](https://github.com/aptible/supercronic), nunca en la Mac.

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
| `sbx ps` | todos los sandbox de la Mac |

## Cómo se entera Claude Code

`sbx-run` envuelve cada job: guarda el log en `out/runs/` y agrega una línea a `out/events.jsonl`. El hook `sandbox-inbox.sh` (SessionStart y UserPromptSubmit) le pasa a Claude los eventos que todavía no vio. Para esperar un job en vivo: Monitor con `sbx inbox --follow`.

## Bloqueo de cron en el host

`bloquear-cron-host.py` (PreToolUse) frena `crontab`, `at`, `launchctl load/bootstrap`, `brew services start` y escrituras en `~/Library/LaunchAgents`, y le indica a Claude que use `sbx`. Ignora el cuerpo de los heredocs, que es texto y no comandos.
