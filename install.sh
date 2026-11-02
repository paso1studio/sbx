#!/usr/bin/env bash
# Instala sbx y su integración con Claude Code. Se puede correr las veces que haga falta.
#   ./install.sh
set -euo pipefail
REPO="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SETTINGS="$CLAUDE_DIR/settings.json"

enlazar() {  # enlazar <destino-en-el-repo> <enlace>
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then
    mv "$dst" "$dst.antes-de-sbx"
    echo "respaldado: $dst -> $dst.antes-de-sbx"
  fi
  ln -sfn "$src" "$dst"
  echo "enlace: $dst -> $src"
}

enlazar "$REPO/bin/sbx" "$HOME/.local/bin/sbx"
enlazar "$REPO/claude/hooks/bloquear-cron-host.py" "$CLAUDE_DIR/hooks/bloquear-cron-host.py"
enlazar "$REPO/claude/hooks/sandbox-inbox.sh" "$CLAUDE_DIR/hooks/sandbox-inbox.sh"

# Registra los hooks en settings.json sin tocar el resto ni duplicarlos.
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"
cp "$SETTINGS" "$SETTINGS.bak-sbx"
jq '
  def agregar(evento; entrada):
    .hooks[evento] = ((.hooks[evento] // [])
      | if any(.[]; .hooks[]?.command == entrada.hooks[0].command) then . else . + [entrada] end);
  agregar("PreToolUse"; {matcher: "Bash|Write|Edit|MultiEdit",
    hooks: [{type: "command", command: "\"$HOME/.claude/hooks/bloquear-cron-host.py\"", timeout: 10}]})
  | agregar("SessionStart"; {hooks: [{type: "command", command: "\"$HOME/.claude/hooks/sandbox-inbox.sh\"", timeout: 10}]})
  | agregar("UserPromptSubmit"; {hooks: [{type: "command", command: "\"$HOME/.claude/hooks/sandbox-inbox.sh\"", timeout: 10}]})
' "$SETTINGS.bak-sbx" > "$SETTINGS"
echo "hooks registrados en $SETTINGS (respaldo: $SETTINGS.bak-sbx)"

if docker info >/dev/null 2>&1; then
  "$REPO/bin/sbx" base build alpine
else
  echo "Docker no está corriendo: abrilo y corré 'sbx base build alpine'"
fi
