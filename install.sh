#!/usr/bin/env bash
#
# Installer for the Claude Code usage status line.
# Non-destructive: merges only the `statusLine` block into your existing
# ~/.claude/settings.json (backing it up first) and never touches anything else.
#
# Usage:
#   ./install.sh              install / update
#   ./install.sh --uninstall  remove and restore the settings backup
#
set -euo pipefail

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
SETTINGS="$CLAUDE_DIR/settings.json"
SCRIPT_DEST="$CLAUDE_DIR/statusline-usage.py"
CSCONFIG_DEST="$CLAUDE_DIR/claude-statusbar.json"

info()  { printf '\033[38;5;244m▸ %s\033[0m\n' "$1"; }
ok()    { printf '\033[38;5;114m✅ %s\033[0m\n' "$1"; }
die()   { printf '\033[38;5;203m✗ %s\033[0m\n' "$1" >&2; exit 1; }

# --- locate a python3 -------------------------------------------------------
PY="$(command -v python3 || true)"
[ -n "$PY" ] || die "python3 not found. Install Python 3 and re-run."

# --- uninstall --------------------------------------------------------------
if [ "${1:-}" = "--uninstall" ]; then
  info "Removing status line files…"
  rm -f "$SCRIPT_DEST" "$CSCONFIG_DEST"
  if [ -f "$SETTINGS.bak" ]; then
    info "Restoring settings.json from backup…"
    mv "$SETTINGS.bak" "$SETTINGS"
  else
    info "No backup found — removing the statusLine block from settings.json…"
    [ -f "$SETTINGS" ] && "$PY" - "$SETTINGS" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
d.pop("statusLine", None)
json.dump(d, open(p, "w"), indent=2)
open(p, "a").write("\n")
PY
  fi
  ok "Uninstalled. Restart Claude Code."
  exit 0
fi

# --- prerequisites ----------------------------------------------------------
info "Checking prerequisites… python3 ✓"

# --- install claude-statusbar (provides the `cs` binary) --------------------
if command -v cs >/dev/null 2>&1; then
  info "claude-statusbar already installed (cs on PATH) ✓"
else
  info "Installing claude-statusbar (provides \`cs\`)…"
  "$PY" -m pip install --user --quiet claude-statusbar \
    || die "pip install failed. Install manually: python3 -m pip install --user claude-statusbar"
  command -v cs >/dev/null 2>&1 || cat <<EOF

  Note: \`cs\` was installed but isn't on your PATH yet. Add its bin dir:
    macOS:  export PATH="\$HOME/Library/Python/3.9/bin:\$PATH"
    Linux:  export PATH="\$HOME/.local/bin:\$PATH"
  (statusline-usage.py also falls back to the macOS pip path automatically.)

EOF
fi

# --- copy the files ---------------------------------------------------------
mkdir -p "$CLAUDE_DIR"
info "Copying statusline-usage.py → $SCRIPT_DEST"
cp "$SRC_DIR/statusline-usage.py" "$SCRIPT_DEST"
info "Copying claude-statusbar.json → $CSCONFIG_DEST"
cp "$SRC_DIR/claude-statusbar.json" "$CSCONFIG_DEST"

# --- merge the statusLine block into settings.json (Python, no jq) ----------
if [ -f "$SETTINGS" ]; then
  info "Backing up settings.json → settings.json.bak"
  cp "$SETTINGS" "$SETTINGS.bak"
fi
info "Merging statusLine block into settings.json…"
"$PY" - "$SETTINGS" <<'PY'
import json, os, sys
path = sys.argv[1]
try:
    data = json.load(open(path))
except (FileNotFoundError, ValueError):
    data = {}
data["statusLine"] = {
    "type": "command",
    "command": 'python3 "$HOME/.claude/statusline-usage.py"',
    "refreshInterval": 1,
}
os.makedirs(os.path.dirname(path), exist_ok=True)
json.dump(data, open(path, "w"), indent=2)
open(path, "a").write("\n")
PY

ok "Installed. Restart (or open a new) Claude Code session to see the bar."
