# sbx

**English** · [Español](README.es.md)

One Docker container per project for the cron jobs and scripts that run on repeat, so your computer stays clean. It also ships two hooks so Claude Code can schedule work inside that container and find out how each job ended.

## What it solves

- **Your machine fills up with schedulers.** Cron entries, launchd plists and `brew services` pile up across projects, and nobody remembers which one belongs to what. With `sbx`, every project's jobs live in its own `.sandbox/` folder, versioned with the project. Remove the project and nothing is left behind on the host.
- **Jobs written by an AI agent run with your full permissions.** The container mounts your code **read-only** at `/workspace` and gives jobs a single writable folder, `/out`. It runs with `no-new-privileges` and CPU and memory limits.
- **Claude Code can't see what happened after it schedules something.** Every job is wrapped by `sbx-run`, which saves its log and appends an event to `out/events.jsonl`. A hook hands Claude the jobs that finished since it last looked, so it can react without polling.
- **Agents reach for the host scheduler by habit.** A `PreToolUse` hook blocks `crontab`, `at`, `launchctl` and `brew services`, and tells Claude to use `sbx` instead.
- **Secrets leak into the container.** Each project's secrets live outside the repo, in `~/.config/sbx/<project>.env` (mode 600). Any `.env` inside the repo is masked with `/dev/null`, so jobs can't read it.
- **Docker Desktop leaves some containers stopped after a reboot, and their cron silently stops.** `sbx levantar` and `sbx vigia` bring them back.

## Requirements

bash, `jq`, `python3` (for the hook) and Docker with `docker compose`. Built and tested on macOS with Docker Desktop. Linux hasn't been tested.

## Installation

> **Before you install:** `install.sh` changes your Claude Code configuration. It adds three hooks (PreToolUse, SessionStart and UserPromptSubmit) to `~/.claude/settings.json`, links two scripts into `~/.claude/hooks/` and creates `~/.local/bin/sbx`. Before touching `settings.json` it saves a copy to `settings.json.bak-sbx`, and any file already at a destination is renamed to `.antes-de-sbx`. To undo it, restore that copy and delete the links.
>
> The hook `bloquear-cron-host.py` blocks `crontab`, `at`, `launchctl` and `brew services` on that machine, for every project.

```bash
git clone https://github.com/paso1studio/sbx.git ~/sbx
~/sbx/install.sh
```

It links `bin/sbx` → `~/.local/bin/sbx` and the hooks → `~/.claude/hooks/`, registers the hooks in `~/.claude/settings.json` and builds the base image. You can run it as many times as you like.

## Per-project sandbox

Each project gets a `.sandbox/` folder with its own Docker container. Cron jobs run inside it with [supercronic](https://github.com/aptible/supercronic), never on the host.

```
project/
└── .sandbox/
    ├── Dockerfile        FROM sbx-base:alpine | sbx-base:ubuntu
    ├── compose.yaml      project → /workspace (read-only), .sandbox/out → /out
    ├── crontab           the cron jobs, versioned with the project
    ├── packages.txt      apk/apt packages
    ├── requirements.txt  pip dependencies
    └── out/              logs, results and events.jsonl (git-ignored)
```

Quick start:

```bash
cd my-project
sbx init                                  # or: sbx init ubuntu (if you need glibc)
sbx up
sbx run hello python3 scripts/hello.py    # try a job once, right now
sbx cron add "*/15 * * * *" hello python3 scripts/hello.py
sbx inbox                                 # jobs that finished
```

| Command | What it does |
|---|---|
| `sbx init [alpine\|ubuntu]` | creates `.sandbox/` |
| `sbx up` / `down` / `sh` / `logs` | manages the container |
| `sbx cron add "*/15 * * * *" name python3 scripts/x.py` | adds a cron job and reloads it |
| `sbx cron ls` / `rm name` | lists or removes jobs (and reloads) |
| `sbx cron reload` | re-reads the crontab after editing it by hand: the container doesn't notice on its own |
| `sbx run name command...` | runs a job once, now |
| `sbx inbox [--all\|--follow]` | jobs that finished |
| `sbx claude` | Claude Code inside the container (to run `/login`) |
| `sbx ps` | every sandbox on the machine |
| `sbx levantar` | starts every stopped sandbox on the machine |
| `sbx vigia up` / `down` / `logs` | a container that restarts them when Docker starts |

Cron times use the host's time zone. `sbx base build` passes it to the image; a hand-built image defaults to UTC.

Inside the container the code is read-only at `/workspace`. Everything a job writes goes to `/out` (`.sandbox/out/` on the host).

## Sandboxes that are down after a restart

Sandboxes use `restart: unless-stopped`, but Docker Desktop doesn't always bring all of them back when it starts: one may end up `Exited`, and which one changes from boot to boot. While it's down, its cron jobs don't run.

- `sbx levantar` starts every stopped `sbx-*` container as it was (it doesn't rebuild the image or recompute the `.env` masks). It skips those whose project folder no longer exists, so Docker doesn't create empty folders when mounting.
- `sbx vigia up` leaves a container running (`sandbox/vigia/`) that starts with Docker and, 30 seconds later, restarts the sandboxes that boot left down; it retries once a minute, up to 10 times. It doesn't touch a sandbox you stopped by hand later, or one that was already down before: `sbx levantar` is for those. You install it once for the whole machine.

The watchdog mounts the Docker socket, so it can control all of Docker. That's why it runs with no network, a read-only filesystem, no capabilities and its script baked into the image. It only helps if Docker itself starts: turn on "Start Docker Desktop when you sign in" in Docker Desktop.

## How Claude Code finds out

`sbx-run` wraps every job: it saves the log in `out/runs/` and appends a line to `out/events.jsonl`. The `sandbox-inbox.sh` hook (SessionStart and UserPromptSubmit) passes Claude the events it hasn't seen yet. To wait for a job live: Monitor with `sbx inbox --follow`.

## Blocking cron on the host

`bloquear-cron-host.py` (PreToolUse) blocks `crontab`, `at`, `launchctl load/bootstrap`, `brew services start` and writes to `~/Library/LaunchAgents`, and tells Claude to use `sbx`. It ignores the body of heredocs, which is text and not commands.

## Suggested rule for your CLAUDE.md

The hook enforces the rule; this explains to Claude how to work with it from the start.

```markdown
## Cron jobs run in the project's sandbox

- Every cron job or repeating process runs inside the project's container, never on the host. No `crontab`, `launchctl`, `brew services` or `at`.
- The sandbox is the project's `.sandbox/` folder, managed with `sbx`: `sbx init` (or `sbx init ubuntu`) → `sbx up`, then `sbx cron add "<expr>" <name> <command...>`. `sbx run <name> <command...>` tries it once.
- Inside the container the code is at `/workspace`, read-only. Anything a job generates goes to `/out` (`.sandbox/out/` on the host).
- Each finished job leaves an event in `.sandbox/out/events.jsonl`; a hook passes you the new ones. To wait for one, use Monitor with `sbx inbox --follow`.
```

## License

[MIT](LICENSE)
