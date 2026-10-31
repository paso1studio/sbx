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
        apk add --no-cache bash tzdata curl jq python3 py3-pip supercronic tini; \
    else \
        export DEBIAN_FRONTEND=noninteractive; \
        apt-get update; \
        apt-get install -y --no-install-recommends bash tzdata curl ca-certificates jq python3 python3-venv python3-pip tini; \
        rm -rf /var/lib/apt/lists/*; \
        curl -fsSL -o /usr/local/bin/supercronic \
            "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH}"; \
        chmod +x /usr/local/bin/supercronic; \
    fi; \
    ln -sf "/usr/share/zoneinfo/${TZ}" /etc/localtime; echo "${TZ}" > /etc/timezone; \
    python3 -m venv /opt/venv

ENV TZ=${TZ} \
    PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY sbx-run entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/sbx-run /usr/local/bin/entrypoint.sh

# /workspace: código del proyecto, solo lectura.
# /out:       único lugar con escritura (logs, resultados, eventos para el host).
WORKDIR /workspace
ENTRYPOINT ["tini", "--", "entrypoint.sh"]
