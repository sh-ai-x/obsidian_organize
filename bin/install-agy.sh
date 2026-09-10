#!/usr/bin/env bash
# bin/install-agy.sh — Install obsidian-organize for Google Antigravity (agy).
#
# Supports:
#   1. Global install (all workspaces / vaults on this machine):
#      bin/install-agy.sh --global
#      Links plugins/obsidian-organize into ~/.gemini/config/plugins/obsidian-organize
#      and registers commands/skills in ~/.gemini/config/import_manifest.json.
#
#   2. Vault-local install (one specific Obsidian vault):
#      bin/install-agy.sh /path/to/obsidian/vault
#      Creates .agents/ configuration in the target vault pointing to this plugin.
#
#   3. Local workspace self-check:
#      bin/install-agy.sh --check
#
# Usage:
#   bin/install-agy.sh --help
#   bin/install-agy.sh --global [--dry-run]
#   bin/install-agy.sh <vault-path> [--dry-run]
#   bin/install-agy.sh --check

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_SRC="${REPO_ROOT}/plugins/obsidian-organize"
GLOBAL_PLUGIN_DIR="${HOME}/.gemini/config/plugins/obsidian-organize"
CLI_PLUGIN_DIR="${HOME}/.gemini/antigravity-cli/plugins/obsidian-organize"
IMPORT_MANIFEST="${HOME}/.gemini/config/import_manifest.json"

die() { echo "error: $*" >&2; exit 1; }

show_help() {
  sed -n "2,/^$/p" "$0" | sed "s/^# \?//"
}

DRY_RUN=0
CHECK_ONLY=0
GLOBAL=0
TARGET_VAULT=""

while [ $# -gt 0 ]; do
  case "$1" in
    -h|--help) show_help; exit 0 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --check) CHECK_ONLY=1; shift ;;
    --global) GLOBAL=1; shift ;;
    -*) die "unknown option: $1 (try --help)" ;;
    *)
      if [ -z "$TARGET_VAULT" ]; then
        TARGET_VAULT="$1"
      else
        die "unexpected argument: $1"
      fi
      shift
      ;;
  esac
done

if [ "$CHECK_ONLY" = "1" ]; then
  echo "Checking agy setup in ${REPO_ROOT}..."
  [ -f "${PLUGIN_SRC}/plugin.json" ] || die "missing ${PLUGIN_SRC}/plugin.json"
  [ -d "${PLUGIN_SRC}/commands" ] || die "missing ${PLUGIN_SRC}/commands"
  [ -f "${REPO_ROOT}/.agents/plugins.json" ] || die "missing .agents/plugins.json"
  [ -f "${REPO_ROOT}/.agents/skills.json" ] || die "missing .agents/skills.json"
  echo "OK: Workspace is configured for Antigravity (agy)."
  if [ -L "$GLOBAL_PLUGIN_DIR" ] || [ -d "$GLOBAL_PLUGIN_DIR" ]; then
    echo "Global plugin installed at: ${GLOBAL_PLUGIN_DIR}"
  else
    echo "Global plugin: not installed in ~/.gemini/config/plugins/ (run bin/install-agy.sh --global to install)"
  fi
  exit 0
fi

if [ "$GLOBAL" = "1" ]; then
  echo "Installing obsidian-organize globally for agy..."
  TARGET_DIR="${HOME}/.gemini/config/plugins"
  TARGET_CLI_DIR="${HOME}/.gemini/antigravity-cli/plugins"
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] would mkdir -p ${TARGET_DIR} and ${TARGET_CLI_DIR}"
    echo "[dry-run] would ln -sfn ${PLUGIN_SRC} ${GLOBAL_PLUGIN_DIR}"
    echo "[dry-run] would register commands and skills in ${IMPORT_MANIFEST}"
    exit 0
  fi
  mkdir -p "${TARGET_DIR}" "${TARGET_CLI_DIR}"
  ln -sfn "${PLUGIN_SRC}" "${GLOBAL_PLUGIN_DIR}"
  ln -sfn "${PLUGIN_SRC}" "${CLI_PLUGIN_DIR}"
  
  # Register in import_manifest.json so slash commands show up in UI
  python3 -c "
import json
from pathlib import Path

p = Path(\"${IMPORT_MANIFEST}\")
data = json.loads(p.read_text(encoding=\"utf-8\")) if p.exists() else {\"imports\": []}
imports = data.setdefault(\"imports\", [])
names = [entry.get(\"name\") for entry in imports]
if \"obsidian-organize\" not in names:
    imports.append({
        \"name\": \"obsidian-organize\",
        \"source\": \"claude-code\",
        \"importedAt\": \"2026-09-10T07:56:00Z\",
        \"components\": [\"commands\", \"skills\"]
    })
else:
    for entry in imports:
        if entry.get(\"name\") == \"obsidian-organize\":
            entry[\"components\"] = [\"commands\", \"skills\"]
p.write_text(json.dumps(data, indent=2), encoding=\"utf-8\")
"
  echo "Successfully linked plugin and registered slash commands in agy!"
  echo "Antigravity (agy) slash commands are now active:"
  echo "  /obsidian-organize:bootstrap"
  echo "  /obsidian-organize:research"
  echo "  /obsidian-organize:add_wiki"
  echo "  /obsidian-organize:process_clippings"
  echo "  /obsidian-organize:remove_wiki"
  exit 0
fi

if [ -n "$TARGET_VAULT" ]; then
  TARGET_VAULT="$(cd "$TARGET_VAULT" && pwd)"
  echo "Configuring Obsidian vault at ${TARGET_VAULT} for agy..."
  AGENTS_DIR="${TARGET_VAULT}/.agents"
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] would mkdir -p ${AGENTS_DIR}"
    echo "[dry-run] would write ${AGENTS_DIR}/plugins.json pointing to ${PLUGIN_SRC}"
    echo "[dry-run] would write ${AGENTS_DIR}/skills.json pointing to ${PLUGIN_SRC}/skills"
    exit 0
  fi
  mkdir -p "${AGENTS_DIR}"
  printf "{\n  \"entries\": [\n    {\n      \"path\": \"%s\"\n    }\n  ]\n}\n" "${PLUGIN_SRC}" > "${AGENTS_DIR}/plugins.json"
  printf "{\n  \"entries\": [\n    {\n      \"path\": \"%s/skills\"\n    }\n  ]\n}\n" "${PLUGIN_SRC}" > "${AGENTS_DIR}/skills.json"
  echo "Successfully configured ${TARGET_VAULT}/.agents"
  echo "Now when you run agy in ${TARGET_VAULT}, all obsidian-organize skills are active!"
  exit 0
fi

show_help
exit 1
