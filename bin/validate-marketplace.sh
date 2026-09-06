#!/usr/bin/env bash
# Validates the obsidian-organize marketplace + plugin manifests.
#
# Checks:
#   1. .claude-plugin/marketplace.json is valid JSON and has the required keys.
#   2. Each plugin entry's `source` path resolves to a real directory.
#   3. Each plugin entry's `name` / `version` matches the inner plugin.json.
#   4. Every skills[].path in the inner plugin.json resolves to a real SKILL.md.
#
# Run from the repo root:
#   bin/validate-marketplace.sh

set -euo pipefail

cd "$(dirname "$0")/.."

python3 - <<'PY'
import json, pathlib, sys
repo_root = pathlib.Path('.').resolve()
mp_path = repo_root / '.claude-plugin' / 'marketplace.json'
mp = json.loads(mp_path.read_text())

errs = []
for k in ('name', 'owner', 'plugins'):
    if k not in mp:
        errs.append(f"marketplace.json: missing key '{k}'")
for p in mp.get('plugins', []):
    for k in ('name', 'source', 'version'):
        if k not in p:
            errs.append(f"plugin '{p.get('name', '?')}': missing '{k}'")
    src = (repo_root / p['source']).resolve()
    if not src.is_dir():
        errs.append(f"plugin '{p['name']}': source '{p['source']}' not found at {src}")
        continue
    pj = src / '.claude-plugin' / 'plugin.json'
    if not pj.is_file():
        errs.append(f"plugin '{p['name']}': missing plugin.json at {pj}")
        continue
    pj_data = json.loads(pj.read_text())
    if pj_data.get('name') != p['name']:
        errs.append(f"plugin '{p['name']}': name mismatch (manifest={pj_data.get('name')})")
    if pj_data.get('version') != p['version']:
        errs.append(f"plugin '{p['name']}': version mismatch (manifest={pj_data.get('version')})")
    for sk in pj_data.get('skills', []):
        sk_path = (src / sk['path']).resolve()
        if not sk_path.is_file():
            errs.append(f"plugin '{p['name']}', skill '{sk.get('id', sk.get('path'))}': SKILL.md not found at {sk['path']}")

if errs:
    for e in errs: print("ERR:", e)
    sys.exit(1)
print("OK: marketplace.json + plugin.json + every skill path resolves.")
print(f"  marketplace: {mp['name']} v{mp.get('version', '?')}")
for p in mp['plugins']:
    print(f"  plugin: {p['name']} v{p['version']}  source={p['source']}  category={p.get('category', '-')}")
print("\nResolved skills:")
for sk in pj_data.get('skills', []):
    print(f"  - {sk['id']:42s} -> {sk['path']}")
PY