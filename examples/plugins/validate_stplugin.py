import json
import re
import zipfile
from pathlib import Path

OUT = Path(r"d:/_dev/fs_table/smart-table-spec/examples/plugins/packages")
errors = 0
for zp in sorted(OUT.glob("*.stplugin.zip")):
    problems = []
    with zipfile.ZipFile(zp) as zf:
        names = [n.replace("\\", "/") for n in zf.namelist()]
        # 路径安全
        for n in names:
            if n.startswith("/") or n.startswith("..") or re.match(r"^[A-Za-z]:", n):
                problems.append(f"unsafe path: {n}")
        # manifest 在根
        if "manifest.json" not in names and "./manifest.json" not in names:
            problems.append("manifest.json missing at root")
            manifest = {}
        else:
            with zf.open("manifest.json") as f:
                try:
                    manifest = json.loads(f.read().decode("utf-8"))
                except Exception as e:
                    problems.append(f"manifest parse error: {e}")
                    manifest = {}
        # entry
        entry = manifest.get("entry", "")
        if entry and entry not in names and f"./{entry}" not in names:
            problems.append(f"entry missing: {entry}")
        # assets
        for css in (manifest.get("assets") or {}).get("styles") or []:
            if css not in names:
                problems.append(f"assets.styles missing: {css}")
        for js in (manifest.get("assets") or {}).get("scripts") or []:
            if js not in names:
                problems.append(f"assets.scripts missing: {js}")
        # endpoints
        for ep in (manifest.get("endpoints") or []):
            ep_entry = ep.get("entry", "")
            if ep_entry and ep_entry not in names and f"./{ep_entry}" not in names:
                problems.append(f"endpoints entry missing: {ep_entry}")
        # 扩展点（UI 至少一个）
        if manifest.get("type") == "ui" and not (manifest.get("extensionPoints") or []):
            problems.append("ui plugin has no extensionPoints")
    status = "PASS" if not problems else "FAIL"
    if problems:
        errors += 1
    print(f"{status}  {zp.name}")
    for p in problems:
        print(f"        - {p}")

print("\nALL PASS" if errors == 0 else f"\n{errors} package(s) FAILED")
