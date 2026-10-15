#!/usr/bin/env python3
"""Inventory an extracted Android dump and inspect APK metadata with aapt."""
import argparse
import csv
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

CATEGORIES = [
    ("launcher", re.compile(r"launcher|quickstep|launcher3|moto.?home|smartspace", re.I)),
    ("widgets", re.compile(r"widget|weather|clock|calendar", re.I)),
    ("wallpaper", re.compile(r"wallpaper|live.?wallpaper|depth.?effect", re.I)),
    ("lockscreen_candidate", re.compile(r"keyguard|lock.?screen|moto.?display|peek.?display|attentive|ambient.?display", re.I)),
]

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def run_aapt(aapt, args, apk):
    try:
        p = subprocess.run([aapt, "dump", *args, str(apk)], text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
        return p.stdout, p.stderr, p.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        return "", str(exc), 1

def parse_badging(text):
    result = {"package": "", "version_code": "", "version_name": "",
              "min_sdk": "", "target_sdk": "", "application_label": ""}
    patterns = {
        "package": r"^package: name='([^']*)'",
        "version_code": r"\bversionCode='([^']*)'",
        "version_name": r"\bversionName='([^']*)'",
        "min_sdk": r"^sdkVersion:'([^']*)'",
        "target_sdk": r"^targetSdkVersion:'([^']*)'",
        "application_label": r"^application-label:'([^']*)'",
    }
    for key, pat in patterns.items():
        m = re.search(pat, text, re.M)
        if m:
            result[key] = m.group(1)
    return result

def classify(relpath, package, label):
    haystack = f"{relpath} {package} {label}"
    for category, pattern in CATEGORIES:
        if pattern.search(haystack):
            return category
    return "unclassified"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--aapt", default="aapt")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not source.is_dir():
        print(f"ERROR: source directory does not exist: {source}", file=sys.stderr)
        return 2

    apk_paths = sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() == ".apk")
    rows = []
    permission_lines = []
    errors = []
    if not apk_paths:
        print(f"ERROR: no APKs found under {source}", file=sys.stderr)
        return 3

    for apk in apk_paths:
        rel = apk.relative_to(source).as_posix()
        badging, err, rc = run_aapt(args.aapt, ["badging"], apk)
        meta = parse_badging(badging)
        permissions, perr, prc = run_aapt(args.aapt, ["permissions"], apk)
        if rc != 0:
            errors.append(f"{rel}: aapt badging failed: {err.strip()}")
        if prc != 0:
            errors.append(f"{rel}: aapt permissions failed: {perr.strip()}")
        category = classify(rel, meta["package"], meta["application_label"])
        rows.append({
            "relative_path": rel,
            "partition_guess": rel.split("/", 1)[0] if "/" in rel else "unknown",
            **meta,
            "category_guess": category,
            "size_bytes": apk.stat().st_size,
            "sha256": sha256(apk),
            "aapt_status": "ok" if rc == 0 else "error",
        })
        permission_lines.append(f"### {rel}\npackage={meta['package']}\n{permissions}\n")
    columns = ["relative_path", "partition_guess", "package", "version_code",
               "version_name", "application_label", "min_sdk", "target_sdk",
               "category_guess", "size_bytes", "sha256", "aapt_status"]
    with (out / "apk-inventory.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    (out / "apk-permissions.txt").write_text("\n".join(permission_lines), encoding="utf-8")
    (out / "analysis-errors.txt").write_text("\n".join(errors) + ("\n" if errors else ""), encoding="utf-8")

    summary = {}
    for row in rows:
        summary[row["category_guess"]] = summary.get(row["category_guess"], 0) + 1
    with (out / "summary.txt").open("w", encoding="utf-8") as f:
        f.write(f"Source: {source}\nAPK count: {len(rows)}\n")
        for category, count in sorted(summary.items()):
            f.write(f"{category}: {count}\n")
        f.write("\nClassification is filename/package-name heuristic only; verify manually.\n")
        f.write("SDK values are metadata, not proof that an APK works on Android 17.\n")
        f.write("aapt cannot resolve runtime framework dependencies or signature permissions.\n")
    print(f"Inventoried {len(rows)} APK(s); reports: {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
