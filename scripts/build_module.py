#!/usr/bin/env python3
"""Create a reversible Magisk/KernelSU-style overlay from an explicit APK allowlist."""
import argparse
import hashlib
import shutil
import sys
from pathlib import Path

PARTITIONS = {"system", "product", "system_ext", "vendor", "odm"}

def mapped_destination(rel):
    parts = Path(rel).parts
    if not parts:
        raise ValueError("empty path")
    partition = parts[0]
    if partition not in PARTITIONS:
        raise ValueError(f"unsupported/unknown top-level partition '{partition}'")
    tail = parts[1:]
    if not tail:
        raise ValueError("APK path must be inside a partition directory")
    # Magisk-style module overlay: system partition paths live directly under system/,
    # while other Android partitions are commonly represented below system/<partition>/.
    if partition == "system":
        dest = Path("system").joinpath(*tail)
    else:
        dest = Path("system", partition).joinpath(*tail)
    return dest

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--allowlist", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    source, allowlist, out = Path(args.source).resolve(), Path(args.allowlist), Path(args.out)
    if not source.is_dir():
        print(f"ERROR: source does not exist: {source}", file=sys.stderr)
        return 2
    if not allowlist.is_file():
        print(f"ERROR: allowlist not found: {allowlist}", file=sys.stderr)
        return 2

    approved = []
    for raw in allowlist.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rel = Path(line)
        if rel.is_absolute() or ".." in rel.parts:
            print(f"ERROR: unsafe allowlist path: {line}", file=sys.stderr)
            return 2
        if rel.suffix.lower() != ".apk":
            print(f"ERROR: only APK paths are accepted by this starter script: {line}", file=sys.stderr)
            return 2
        approved.append(rel)

    if not approved:
        print("ERROR: allowlist is empty. Review the inventory, then add exact source-relative APK paths.", file=sys.stderr)
        return 4

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "META-INF").mkdir()
    (out / "module.prop").write_text(
        "id=motorola_ui_test\n"
        "name=Motorola UI Test Overlay (experimental)\n"
        "version=0.1\n"
        "versionCode=1\n"
        "author=local-porting-project\n"
        "description=Experimental APK overlay for Infinity-X Android 17; use only on a backed-up test device.\n",
        encoding="utf-8"
    )
    install = r