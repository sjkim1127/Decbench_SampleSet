#!/usr/bin/env python3
"""Audit DWARF procedure/name evidence in DecBench qualification outputs.

Works with both ELF and MinGW PE images by using the platform binutils textual
DWARF dump rather than assuming an ELF container.  The report intentionally
keeps short DW_AT_name and linkage/demangled identity separate: DecBench's
current experimental C++ path keys by the short name, so collisions here are a
useful estimate of how much a target stresses that limitation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

TAG = "DW_TAG_subprogram"
ATTR_RE = re.compile(r"DW_AT_(name|linkage_name|MIPS_linkage_name)\s*:\s*(.*)$")


def image_kind(path: Path) -> str | None:
    try:
        with path.open("rb") as f:
            magic = f.read(4)
            if magic == b"\x7fELF":
                return "elf"
            if magic[:2] != b"MZ":
                return None
            f.seek(0x3C)
            peoff = int.from_bytes(f.read(4), "little")
            f.seek(peoff)
            return "pe" if f.read(4) == b"PE\0\0" else None
    except OSError:
        return None


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def choose_dump_tool(kind: str) -> list[str] | None:
    candidates: list[list[str]]
    if kind == "elf":
        candidates = [["readelf", "--debug-dump=info", "--wide"]]
    else:
        candidates = [
            ["x86_64-w64-mingw32-objdump", "--dwarf=info"],
            ["i686-w64-mingw32-objdump", "--dwarf=info"],
            ["objdump", "--dwarf=info"],
        ]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            return cmd
    return None


def clean_attr(value: str) -> str:
    value = value.strip()
    # readelf often prints '(indirect string, offset: 0x123): value'.
    if value.startswith("(") and "):" in value:
        value = value.split("):", 1)[1].strip()
    # Some binutils versions prefix '(strp)'.
    value = re.sub(r"^\([^)]*\)\s*", "", value).strip()
    return value


def parse_dwarf(text: str) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if TAG in line:
            if current is not None:
                records.append(current)
            current = {}
            continue
        if current is None:
            continue
        m = ATTR_RE.search(line)
        if not m:
            continue
        key, value = m.groups()
        value = clean_attr(value)
        if key in ("linkage_name", "MIPS_linkage_name"):
            current.setdefault("linkage_name", value)
        else:
            current.setdefault("name", value)
    if current is not None:
        records.append(current)
    return records


def demangle(names: list[str]) -> dict[str, str]:
    names = sorted({n for n in names if n})
    if not names:
        return {}
    tool = shutil.which("c++filt") or shutil.which("x86_64-w64-mingw32-c++filt")
    if not tool:
        return {n: n for n in names}
    try:
        proc = subprocess.run(
            [tool], input="\n".join(names) + "\n", text=True,
            capture_output=True, timeout=60, check=True,
        )
        vals = proc.stdout.splitlines()
        return {n: vals[i] if i < len(vals) else n for i, n in enumerate(names)}
    except Exception:
        return {n: n for n in names}


def audit_binary(path: Path, root: Path) -> dict:
    kind = image_kind(path)
    assert kind is not None
    tool = choose_dump_tool(kind)
    base = {
        "path": str(path.relative_to(root)),
        "format": kind,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "dwarf_tool": tool[0] if tool else None,
    }
    if tool is None:
        return {**base, "error": "no DWARF dump tool found"}
    try:
        proc = subprocess.run(
            [*tool, str(path)], text=True, capture_output=True,
            timeout=300, check=False, errors="replace",
        )
    except Exception as exc:
        return {**base, "error": f"{type(exc).__name__}: {exc}"}

    records = parse_dwarf(proc.stdout)
    names = [r.get("name", "") for r in records if r.get("name")]
    linkages = [r.get("linkage_name", "") for r in records if r.get("linkage_name")]
    dm = demangle(linkages)
    counts = Counter(names)
    collision_names = {n: c for n, c in counts.items() if c > 1}
    collision_records = sum(c - 1 for c in collision_names.values())
    return {
        **base,
        "dump_exit_code": proc.returncode,
        "subprogram_records": len(records),
        "named_subprogram_records": len(names),
        "unique_short_names": len(counts),
        "short_name_collision_names": len(collision_names),
        "short_name_collision_excess_records": collision_records,
        "short_name_collision_rate": round(collision_records / len(names), 6) if names else 0.0,
        "linkage_name_records": len(linkages),
        "unique_linkage_names": len(set(linkages)),
        "unique_demangled_linkage_names": len(set(dm.values())),
        "top_short_name_collisions": [
            {"name": n, "records": c}
            for n, c in sorted(collision_names.items(), key=lambda kv: (-kv[1], kv[0]))[:25]
        ],
        "stderr_tail": proc.stderr[-2000:] if proc.stderr else "",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    root = args.root.resolve()

    binaries = []
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink() and image_kind(path):
            binaries.append(path)

    reports = [audit_binary(p, root) for p in sorted(binaries)]
    named = sum(int(r.get("named_subprogram_records", 0)) for r in reports)
    collisions = sum(int(r.get("short_name_collision_excess_records", 0)) for r in reports)
    out = {
        "root": str(root),
        "binary_count": len(reports),
        "named_subprogram_records": named,
        "short_name_collision_excess_records": collisions,
        "aggregate_short_name_collision_rate": round(collisions / named, 6) if named else 0.0,
        "binaries": reports,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k != "binaries"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
