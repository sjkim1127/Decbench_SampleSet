#!/usr/bin/env python
"""Assemble a DecBench-layout dataset from ``scripts/compile_all.py`` output.

Input : <build_root>/<opt>/<project>/compiled/   (produced by DecBench's compile path)
Output: <dest>/
    binaries/<opt>/<project>/<file>              debug binary (DWARF kept)
    binaries_stripped/<opt>/<project>/<file>     same image, ``strip --strip-all``
    sources/<project>/<tu>.c                     header-stripped preprocessed source (dedup by content)
    pipeline_data/source_cfgs/<opt>/<project>/<stem>.json
    ground_truth/<opt>/<project>/<stem>.functions.json   DWARF function identity table
    metadata/<opt>/<project>/<stem>.json         compiler / flags / hashes
    dataset.toml, configs/cpp-sample/manifest.json

Ground truth is deliberately stored separately from any scoring policy: the
source/debug/stripped artifacts and the function identities do not depend on how
a recovery is later judged (the C++ type metric is still undecided upstream).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from decbench.publish.cfg_export import export_project_cfgs
from decbench.utils.cfg import strip_system_headers
from decbench.utils.function_identity import (
    dwarf_function_identities,
    function_storage_key,
)
from decbench.utils.results_tree import OPT_LEVELS, compiled_dir

SKIP_SUFFIXES = (".o", ".a", ".s", ".h", ".i", ".ii", ".c", ".cc", ".cpp", ".cxx")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_linked_elf(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            if f.read(4) != b"\x7fELF":
                return False
            f.seek(16)
            return struct.unpack("<H", f.read(2))[0] in (2, 3)
    except (OSError, struct.error):
        return False


def tool_version(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, check=False).stdout.splitlines()[0]
    except (OSError, IndexError):
        return "unknown"


def read_pins(toml_path: Path) -> dict:
    pins: dict[str, str] = {}
    for line in toml_path.read_text().splitlines():
        if line.startswith("# Resolved upstream commit:"):
            pins["upstream_commit"] = line.split(":", 1)[1].strip()
        elif line.startswith(("name =", "version =", "source_remote =")):
            key, val = line.split("=", 1)
            pins[key.strip()] = val.strip().strip('"')
    return pins


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("build_root", type=Path)
    ap.add_argument("dest", type=Path)
    ap.add_argument("--targets", type=Path, required=True, help="dir with <project>.toml")
    ap.add_argument("projects", nargs="+")
    args = ap.parse_args()

    dest: Path = args.dest
    dest.mkdir(parents=True, exist_ok=True)
    gcc_v = tool_version(["g++", "--version"])
    manifest_files: list[dict] = []
    stems_by_project: dict[str, dict[str, list[str]]] = {}

    for project in args.projects:
        pins = read_pins(args.targets / f"{project}.toml")
        seen_src: dict[str, str] = {}
        for opt in OPT_LEVELS:
            comp = compiled_dir(args.build_root, opt, project)
            if not comp.is_dir():
                print(f"[skip] {opt}/{project}: no compiled dir", file=sys.stderr)
                continue

            for i_path in sorted(comp.glob("*.i")) + sorted(comp.glob("*.ii")):
                stripped = strip_system_headers(i_path.read_text(errors="replace"))
                digest = hashlib.sha256(stripped.encode("utf-8", "replace")).hexdigest()
                if digest in seen_src.values():
                    continue
                out = dest / "sources" / project / f"{i_path.stem}.c"
                if out.exists():  # same TU name, different content at another opt level
                    out = out.with_name(f"{i_path.stem}.{opt}.c")
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(stripped, encoding="utf-8")
                seen_src[str(out)] = digest

            for binary in sorted(p for p in comp.iterdir() if p.is_file() and not p.is_symlink()):
                if binary.suffix in SKIP_SUFFIXES or not is_linked_elf(binary):
                    continue
                identities = dwarf_function_identities(binary)
                if not identities:
                    print(f"[skip] {binary.name}: no DWARF functions", file=sys.stderr)
                    continue
                stem = binary.name
                stems_by_project.setdefault(project, {}).setdefault(opt, []).append(stem)

                dbg = dest / "binaries" / opt / project / stem
                dbg.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(binary, dbg)
                stripped_bin = dest / "binaries_stripped" / opt / project / stem
                stripped_bin.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(["strip", "--strip-all", "-o", str(stripped_bin), str(binary)], check=True)

                counts: dict[str, int] = {}
                for ident in identities:
                    counts[ident.name] = counts.get(ident.name, 0) + 1
                functions = [
                    {
                        "name": i.name,
                        "linkage_name": i.linkage_name,
                        "address": f"0x{i.address:x}",
                        "ambiguous_name": counts[i.name] > 1,
                        "storage_key": function_storage_key(i) if counts[i.name] > 1 else i.name,
                    }
                    for i in identities
                ]
                gt = dest / "ground_truth" / opt / project / f"{stem}.functions.json"
                gt.parent.mkdir(parents=True, exist_ok=True)
                gt.write_text(json.dumps({"binary": stem, "functions": functions}, indent=2))

                meta = {
                    "project": project,
                    "opt": opt,
                    "binary": stem,
                    "language": "c++",
                    "compiler": gcc_v,
                    "debug_sha256": sha256(dbg),
                    "stripped_sha256": sha256(stripped_bin),
                    "function_count": len(functions),
                    "ambiguous_function_count": sum(f["ambiguous_name"] for f in functions),
                    **pins,
                }
                mp = dest / "metadata" / opt / project / f"{stem}.json"
                mp.parent.mkdir(parents=True, exist_ok=True)
                mp.write_text(json.dumps(meta, indent=2))
                manifest_files.append(
                    {"opt": opt, "project": project, "binary": stem, "functions": len(functions)}
                )

    for project, stems_by_opt in stems_by_project.items():
        try:
            export_project_cfgs(args.build_root, dest, project, stems_by_opt)
        except Exception as exc:  # noqa: BLE001 - keep binaries even if CFG export fails
            print(f"[cfg] {project}: FAILED ({exc})", file=sys.stderr)

    (dest / "configs" / "cpp-sample").mkdir(parents=True, exist_ok=True)
    (dest / "configs" / "cpp-sample" / "manifest.json").write_text(
        json.dumps({"config": "cpp-sample", "binaries": manifest_files}, indent=2)
    )
    (dest / "dataset.toml").write_text(
        "[dataset]\n"
        'name = "decbench-cpp-dataset"\n'
        'status = "unofficial prototype"\n'
        'language = "c++"\n'
        f'compiler = "{gcc_v}"\n'
        f"binaries = {len(manifest_files)}\n"
        f"functions = {sum(f['functions'] for f in manifest_files)}\n\n"
        "[configs.cpp-sample]\n"
        'description = "ninja, snappy, double-conversion at O0 / O2 / O2-noinline"\n'
    )
    print(f"assembled {len(manifest_files)} binaries into {dest}")
    return 0 if manifest_files else 1


if __name__ == "__main__":
    raise SystemExit(main())
