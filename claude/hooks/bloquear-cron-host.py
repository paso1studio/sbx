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
# Solo comandos que no pueden lanzar otro programa: nada de paginadores (less, man),
# ni rg (--pre), ni editores.
SOLO_LECTURA = {"cat", "head", "tail", "grep", "egrep", "fgrep", "ls", "echo", "printf",
                "wc", "file", "stat", "diff", "jq", "which", "type", "cd", "pwd", "true", "sbx"}
# git solo con subcomandos que no disparan hooks del repo (commit y push sí los disparan).
GIT_LECTURA = {"init", "status", "log", "diff", "show", "branch"}
GIT_OPCIONES_EXEC = re.compile(r"^(-c|--config-env|--exec-path|--ext-diff|--upload-pack|--receive-pack|-x|--exec)")
LAUNCHCTL_LECTURA = {"list", "print", "print-disabled", "print-cache", "blame", "version", "help"}
PALABRAS_CRON = re.compile(
    r"(?<![\w./-])crontab\b|\blaunchctl\b|Launch(Agents|Daemons)|\bbrew\s+services\b"
    r"|(?<![\w./-])(atq|atrm)\b|(?<![\w./-])at\s+(-\w+\s+)*(now|noon|midnight|teatime|\d)"
)


def entre_comillas(texto):
    # True si al final de `texto` quedó abierta una comilla simple o doble.
    simple = doble = False
    escapado = False
    for c in texto:
        if escapado:
            escapado = False
        elif c == "\\" and not simple:
            escapado = True
        elif c == "'" and not doble:
            simple = not simple
        elif c == '"' and not simple:
            doble = not doble
    return simple or doble


def sin_heredocs(cmd):
    # El cuerpo de un heredoc es texto (un README, un script), no comandos a ejecutar.
    # Ante la duda no se saca nada: un `<<` entre comillas, un `<<<` o un heredoc que
    # nunca cierra dejan el comando entero para que se revise línea por línea.
    lineas, salida, fin, cuerpo = cmd.split("\n"), [], None, []
    for linea in lineas:
        if fin is not None:
            cuerpo.append(linea)
            if linea.strip() == fin:
                fin, cuerpo = None, []
            continue
        salida.append(linea)
        for m in re.finditer(r"(?<!<)<<-?\s*(['\"]?)(\w+)\1(?!\w)", linea):
            antes = linea[:m.start()]
            # Solo se confía en líneas simples (palabras, rutas, redirecciones). Cualquier
            # otra cosa (#, \, $(( )), ${ }, ...) la vuelve ambigua: no se saca nada.
            if not re.fullmatch(r"[\w\s./~:=>'\"-]*", antes):
                break
            if not entre_comillas(antes):
                fin = m.group(2)
                break
    if fin is not None:  # no cerró: no era un heredoc de verdad
        salida.extend(cuerpo)
    return "\n".join(salida)


def segmentos(cmd):
    # Corta el comando en sus partes ejecutables: ; & | && || ( ) $( ` y saltos de línea.
    for seg in re.split(r"\|\||&&|[;&|()`\n]|\$\(", sin_heredocs(cmd)):
        palabras = seg.split()
        prefijado = False
        while palabras and (palabras[0] in PREFIJOS or re.match(r"^\w+=", palabras[0])):
            palabras.pop(0)
            prefijado = True
        if palabras:
            yield prefijado, [os.path.basename(palabras[0])] + palabras[1:]


def es_lectura(prefijado, p):
    # Con sudo, env o una variable delante (PAGER=, LESSOPEN=, GIT_*=) ya no es lectura.
    # Redirigir a un archivo sí se permite: escribir en las carpetas de cron lo frena
    # LAUNCHD_DIRS más abajo.
    if prefijado:
        return False
    if p[0] in SOLO_LECTURA:
        return True
    if p[0] == "git":
        return len(p) > 1 and p[1] in GIT_LECTURA and not any(GIT_OPCIONES_EXEC.match(a) for a in p[1:])
    if p[0] == "launchctl":
        return len(p) > 1 and p[1] in LAUNCHCTL_LECTURA
    if p[0] == "brew":
        return p[1:3] in (["services", "list"], ["services", "info"])
    return False


def bloquea_bash(cmd):
    partes = list(segmentos(cmd))
    # Se busca en todo el comando, cuerpo de heredocs incluido: si se lo pasan a un
    # shell (bash <<EOF), ese shell no es de solo lectura y se bloquea.
    if PALABRAS_CRON.search(cmd) and not all(es_lectura(pre, p) for pre, p in partes):
        return True
    for _, p in partes:
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
