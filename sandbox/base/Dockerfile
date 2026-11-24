# Imagen base de los sandbox. Se construye una vez por sistema operativo:
#   sbx base build alpine   -> sbx-base:alpine
#   sbx base build ubuntu   -> sbx-base:ubuntu
#
# Tiene dos etapas:
#   base    sin Claude Code: es la que se publica en el registry (ghcr.io/paso1studio/sbx-base).
#   claude  base + Claude Code: es la que arma `sbx base build` en cada máquina (la última etapa
#           es la que se construye por defecto). Claude Code es software propietario de
#           Anthropic: se descarga en la máquina de quien construye, no se redistribuye.
ARG BASE=alpine:3.22
FROM ${BASE} AS base
LABEL org.opencontainers.image.source="https://github.com/paso1studio/sbx" \
      org.opencontainers.image.description="Base de los sandbox de sbx: supercronic, uv y sbx-run, sin Claude Code" \
      org.opencontainers.image.licenses="MIT"

ARG TARGETARCH
ARG SUPERCRONIC_VERSION=v0.2.33
ARG UV_VERSION=0.13.9
# `sbx base build` pasa la zona horaria de la máquina; UTC solo si se construye a mano sin --build-arg TZ.
ARG TZ=UTC

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
    /opt/venv/bin/pip install --no-cache-dir "uv==${UV_VERSION}"

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

# uv guarda el entorno virtual y su caché en ~/.cache (otro volumen): el .venv del repo es de macOS.
# ~/.claude y ~/.cache existen en la imagen para que los volúmenes de compose nazcan con dueño sbx.
ENV PATH=/home/sbx/.local/bin:$PATH \
    UV_PROJECT_ENVIRONMENT=/home/sbx/.cache/venv \
    UV_CACHE_DIR=/home/sbx/.cache/uv \
    UV_PYTHON_INSTALL_DIR=/home/sbx/.cache/uv-python \
    UV_LINK_MODE=copy
RUN mkdir -p /home/sbx/.claude /home/sbx/.cache

# /workspace: código del proyecto, solo lectura.
# /out:       único lugar con escritura (logs, resultados, eventos para el host).
WORKDIR /workspace
ENTRYPOINT ["tini", "--", "entrypoint.sh"]

# Claude Code, para los jobs que usan `claude -p`. La sesión (/login, hecho a mano con
# `sbx claude`) vive en ~/.claude, que compose monta como volumen propio de cada proyecto.
FROM base AS claude
ENV CLAUDE_CONFIG_DIR=/home/sbx/.claude \
    DISABLE_AUTOUPDATER=1 \
    USE_BUILTIN_RIPGREP=0
RUN curl -fsSL https://claude.ai/install.sh | bash; \
    claude --version
