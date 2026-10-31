#!/usr/bin/env python3
"""PreToolUse: bloquea cualquier cron o tarea programada en la Mac.

Los cron van al contenedor del proyecto (sbx cron add ...), nunca al host.
Sale con código 2 para que Claude Code cancele la herramienta y lea el motivo.
"""
import json
import os
import re
import sys

MOTIVO = (
    "Bloqueado: en esta Mac no se programan cron ni tareas en el host. "
    "Los cron van al sandbox Docker del proyecto: buscá .sandbox/ subiendo desde el "
    "directorio actual; si no existe, creala con `sbx init` (alpine) o `sbx init ubuntu` "
    "y levantala con `sbx up`. Después: `sbx cron add \"<expr>\" <nombre> <comando...>` "
    "(el comando corre en /workspace, de solo lectura; lo que escriba va a /out)."
)

LAUNCHD_DIRS = re.compile(r"Library/Launch(Agents|Daemons)/|/etc/(crontab|periodic)|/usr/lib/cron|/var/at/")
PREFIJOS = {"sudo", "env", "command", "exec", "nohup", "time", "nice", "xargs"}
# Si el comando menciona algo de cron, se bloquea salvo que cada parte sea de solo
# lectura. Así cualquier envoltorio (bash -c, eval, python -c, awk, find -exec,
# sudo -u ...) queda bloqueado sin tener que enumerarlos.
SOLO_LECTURA = {"cat", "less", "more", "head", "tail", "grep", "egrep", "fgrep", "rg",
                "ls", "echo", "printf", "wc", "file", "stat", "diff", "jq", "man",
                "which", "type", "whatis", "apropos", "cd", "pwd", "true", "sbx"}
LAUNCHCTL_LECTURA = {"list", "print", "print-disabled", "print-cache", "blame", "version", "help"}
PALABRAS_CRON = re.compile(
    r"(?<![\w./-])crontab\b|\blaunchctl\b|Launch(Agents|Daemons)|\bbrew\s+services\b"
    r"|(?<![\w./-])(atq|atrm)\b|(?<![\w./-])at\s+(-\w+\s+)*(now|noon|midnight|teatime|\d)"
)


def sin_heredocs(cmd):
    # El cuerpo de un heredoc es texto (un README, un script), no comandos a ejecutar.
    lineas, salida, fin = cmd.split("\n"), [], None
    for linea in lineas:
        if fin is not None:
            if linea.strip() == fin:
                fin = None
            continue
        salida.append(linea)
        m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", linea)
        if m:
            fin = m.group(1)
    return "\n".join(salida)


def segmentos(cmd):
    # Corta el comando en sus partes ejecutables: ; & | && || ( ) $( ` y saltos de línea.
    for seg in re.split(r"\|\||&&|[;&|()`\n]|\$\(", sin_heredocs(cmd)):
        palabras = seg.split()
        while palabras and (palabras[0] in PREFIJOS or re.match(r"^\w+=", palabras[0])):
            palabras.pop(0)
        if palabras:
            yield [os.path.basename(palabras[0])] + palabras[1:]


def es_lectura(p):
    if p[0] in SOLO_LECTURA:
        return True
    if p[0] == "git":
        return "-c" not in p  # git -c alias.x='!crontab' ejecuta comandos
    if p[0] == "launchctl":
        return len(p) > 1 and p[1] in LAUNCHCTL_LECTURA
    if p[0] == "brew":
        return p[1:3] in (["services", "list"], ["services", "info"])
    return False


def bloquea_bash(cmd):
    partes = list(segmentos(cmd))
    # Se busca en todo el comando, cuerpo de heredocs incluido: si se lo pasan a un
    # shell (bash <<EOF), ese shell no es de solo lectura y se bloquea.
    if PALABRAS_CRON.search(cmd) and not all(es_lectura(p) for p in partes):
        return True
    for p in partes:
        if p[0] in {"crontab", "at", "batch", "atq", "atrm"}:
            return True
        if p[0] == "launchctl" and len(p) > 1 and p[1] in {"load", "bootstrap", "submit", "enable", "kickstart"}:
            return True
        if p[0] == "brew" and len(p) > 2 and p[1] == "services" and p[2] in {"start", "restart", "run"}:
            return True
    # Escribir un plist o crontab a mano (cat >, tee, cp, mv, ln) también cuenta.
    return bool(LAUNCHD_DIRS.search(cmd) and re.search(r">|\btee\b|\bcp\b|\bmv\b|\bln\b|\binstall\b", cmd))


def main():
    datos = json.load(sys.stdin)
    herramienta = datos.get("tool_name", "")
    entrada = datos.get("tool_input", {}) or {}

    if herramienta == "Bash":
        bloquear = bloquea_bash(entrada.get("command", ""))
    elif herramienta in {"Write", "Edit", "MultiEdit"}:
        bloquear = bool(LAUNCHD_DIRS.search(entrada.get("file_path", "")))
    else:
        bloquear = False

    if bloquear:
        print(MOTIVO, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
