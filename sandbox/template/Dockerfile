# Imagen del proyecto. Cambiá la base a sbx-base:ubuntu si necesitás glibc.
FROM sbx-base:alpine

# La imagen base corre como el usuario sbx; para instalar hace falta root.
USER root

# Paquetes del sistema operativo (uno por línea en packages.txt).
COPY packages.txt requirements.txt /tmp/sbx/
RUN set -eux; pkgs=$(grep -vE '^\s*(#|$)' /tmp/sbx/packages.txt || true); \
    if [ -n "$pkgs" ]; then \
        if command -v apk >/dev/null; then apk add --no-cache $pkgs; \
        else apt-get update && apt-get install -y --no-install-recommends $pkgs && rm -rf /var/lib/apt/lists/*; fi; \
    fi; \
    pip install --no-cache-dir -r /tmp/sbx/requirements.txt

USER sbx
