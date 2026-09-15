import json
import zipfile
from pathlib import Path

ROOT = Path(r"d:/_dev/fs_table/smart-table-spec/examples/plugins")
OUT = ROOT / "packages"
OUT.mkdir(exist_ok=True)

SKIP_DIRS = {"packages"}
JUNK_NAMES = {".DS_Store", "Thumbs.db"}


def is_junk(p: Path) -> bool:
    if p.name in JUNK_NAMES:
        return True
    if "__pycache__" in p.parts:
        return True
    if p.suffix == ".pyc":
        return True
    return False


plugins = sorted(
    d
    for d in ROOT.iterdir()
    if d.is_dir() and d.name not in SKIP_DIRS and (d / "manifest.json").exists()
)

for src in plugins:
    manifest = json.loads((src / "manifest.json").read_text(encoding="utf-8"))
    pid = manifest["id"]
    ver = manifest["version"]
    out_name = f"{pid}-{ver}.stplugin.zip"
    out_path = OUT / out_name

    files = sorted(
        (p for p in src.rglob("*") if p.is_file() and not is_junk(p)),
        key=lambda p: p.relative_to(src).as_posix(),
    )

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(src / "manifest.json", "manifest.json")  # manifest 必须位于包根
        for p in files:
            rel = p.relative_to(src).as_posix()
            if rel == "manifest.json":
                continue
            zf.write(p, rel)

    size = out_path.stat().st_size
    names = zipfile.ZipFile(out_path).namelist()
    has_root_manifest = "manifest.json" in names
    print(
        f"OK  {out_name:55s} bytes={size:8d} entries={len(names):3d} "
        f"root_manifest={has_root_manifest} type={manifest.get('type')}"
    )
