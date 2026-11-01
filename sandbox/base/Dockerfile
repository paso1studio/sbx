# Imagen base de los sandbox. Se construye una vez por sistema operativo:
#   sbx base build alpine   -> sbx-base:alpine
#   sbx base build ubuntu   -> sbx-base:ubuntu
ARG BASE=alpine:3.22
FROM ${BASE}

ARG TARGETARCH
ARG SUPERCRONIC_VERSION=v0.2.33
ARG TZ=America/Argentina/Buenos_Aires

# Paquetes mínimos + supercronic (demonio de cron pensado para contenedores).
RUN set -eux; \
    if command -v apk >/dev/null; then \
        apk add --no-cache bash tzdata curl jq git python3 py3-pip supercronic tini libgcc libstdc++ ripgrep; \
    else \
        export DEBIAN_FRONTEND=noninteractive; \
        apt-get update; \
        apt-get install -y --no-install-recommends bash tzdata curl ca-certificates jq git python3 python3-venv python3-pip tini ripgrep; \
        rm -rf /var/lib/apt/lists/*; \
        curl -fsSL -o /usr/local/bin/supercronic \
            "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH}"; \
        chmod +x /usr/local/bin/supercronic; \
    fi; \
    ln -sf "/usr/share/zoneinfo/${TZ}" /etc/localtime; echo "${TZ}" > /etc/timezone; \
    python3 -m venv /opt/venv; \
    /opt/venv/bin/pip install --no-cache-dir uv

ENV TZ=${TZ} \
    PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY sbx-run entrypoint.sh osascript /usr/local/bin/
RUN chmod +x /usr/local/bin/sbx-run /usr/local/bin/entrypoint.sh /usr/local/bin/osascript; \
    if command -v adduser >/dev/null && ! command -v useradd >/dev/null; then adduser -D -u 10001 sbx; \
    else useradd -m -u 10001 sbx; fi

# Los jobs corren sin root.
USER sbx

# Claude Code, para los jobs que usan `claude -p`. La sesión (/login, hecho a mano con
# `sbx claude`) vive en ~/.claude, que compose monta como volumen propio de cada proyecto.
# uv guarda el entorno virtual y su caché en ~/.cache (otro volumen): el .venv del repo es de macOS.
ENV PATH=/home/sbx/.local/bin:$PATH \
    CLAUDE_CONFIG_DIR=/home/sbx/.claude \
    DISABLE_AUTOUPDATER=1 \
    USE_BUILTIN_RIPGREP=0 \
    UV_PROJECT_ENVIRONMENT=/home/sbx/.cache/venv \
    UV_CACHE_DIR=/home/sbx/.cache/uv \
    UV_PYTHON_INSTALL_DIR=/home/sbx/.cache/uv-python \
    UV_LINK_MODE=copy
RUN mkdir -p /home/sbx/.claude /home/sbx/.cache; \
    curl -fsSL https://claude.ai/install.sh | bash; \
    claude --version

# /workspace: código del proyecto, solo lectura.
# /out:       único lugar con escritura (logs, resultados, eventos para el host).
WORKDIR /workspace
ENTRYPOINT ["tini", "--", "entrypoint.sh"]
