#!/usr/bin/env python3
"""Stage complete DecBench C++ Tier-A corpus into official-compatible structure.

Source: ~/cpp_corpus_out/<opt>/<project>/
Target: <out>/
  ├── binaries/<opt>/<project>/<binary_name>
  ├── sources/<project>_sources.tar.gz
  ├── manifest.json
  └── build_summary.json
"""
import hashlib
import json
import os
import shutil
import tarfile
import sys
from pathlib import Path

src_root = Path(os.path.expanduser("~/cpp_corpus_out"))
out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.path.expanduser("~/cpp_corpus_staged"))
out_dir.mkdir(parents=True, exist_ok=True)

binaries_dir = out_dir / "binaries"
sources_dir = out_dir / "sources"
binaries_dir.mkdir(parents=True, exist_ok=True)
sources_dir.mkdir(parents=True, exist_ok=True)

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def is_elf(p: Path) -> bool:
    try:
        with open(p, "rb") as f:
            return f.read(4) == b"\x7fELF"
    except Exception:
        return False

manifest = {
    "language": "c++",
    "compiler": "GCC/G++ 13.3.0 (Ubuntu 24.04 aarch64)",
    "optimization_levels": ["O0", "O2", "O2-noinline"],
    "ground_truth": "DWARF + preprocessed .ii",
    "projects": {},
    "binaries": [],
    "total_binaries": 0,
    "total_projects": 0,
}

build_summary = {
    "projects": {},
    "failed_projects": [],
    "partial_projects": [],
}

all_projects = set()
for res_path in src_root.glob("*/*/result.json"):
    all_projects.add(res_path.parent.name)

print(f"Discovered {len(all_projects)} projects in build output.")

project_results = {}
for proj in sorted(all_projects):
    res_by_opt = {}
    for opt in ["O0", "O2", "O2-noinline"]:
        rf = src_root / opt / proj / "result.json"
        if rf.exists():
            res_by_opt[opt] = json.load(open(rf))
    project_results[proj] = res_by_opt

# Process projects
staged_bin_count = 0
for proj, opts_data in project_results.items():
    ok_opts = [o for o, d in opts_data.items() if d.get("ok")]
    if not ok_opts:
        build_summary["failed_projects"].append(proj)
        continue
    if len(ok_opts) < 3:
        build_summary["partial_projects"].append({proj: ok_opts})

    repo_name = opts_data[ok_opts[0]].get("repo", proj)
    revision = opts_data[ok_opts[0]].get("revision", "unknown")
    build_summary["projects"][proj] = {
        "repo": repo_name,
        "revision": revision,
        "successful_modes": ok_opts,
    }

    manifest["projects"][proj] = {
        "repo": repo_name,
        "revision": revision,
        "modes": ok_opts,
        "binaries": [],
    }

    # 1. Stage Binaries
    for opt in ok_opts:
        comp_dir = src_root / opt / proj / "compiled"
        if not comp_dir.exists():
            continue
        for p in comp_dir.rglob("*"):
            if not p.is_file() or not is_elf(p):
                continue
            dst = binaries_dir / opt / proj / p.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            if not dst.exists():
                shutil.copy2(p, dst)
            rel_path = str(dst.relative_to(out_dir))
            sz = dst.stat().st_size
            entry = {
                "path": rel_path,
                "project": proj,
                "opt": opt,
                "size": sz,
                "sha256": sha256_file(dst),
            }
            manifest["binaries"].append(entry)
            manifest["projects"][proj]["binaries"].append(rel_path)
            staged_bin_count += 1

    # 2. Package Sources (.ii) per project into tar.gz
    src_tar_path = sources_dir / f"{proj}_sources.tar.gz"
    if not src_tar_path.exists():
        print(f"Compressing sources for {proj}...")
        with tarfile.open(src_tar_path, "w:gz") as tar:
            for opt in ok_opts:
                comp_dir = src_root / opt / proj / "compiled"
                if not comp_dir.exists():
                    continue
                for p in comp_dir.rglob("*.ii"):
                    arcname = f"{opt}/{p.relative_to(comp_dir)}"
                    tar.add(p, arcname=arcname)
        manifest["projects"][proj]["sources_archive"] = f"sources/{proj}_sources.tar.gz"
        manifest["projects"][proj]["sources_size"] = src_tar_path.stat().st_size
        manifest["projects"][proj]["sources_sha256"] = sha256_file(src_tar_path)

manifest["total_binaries"] = staged_bin_count
manifest["total_projects"] = len(manifest["projects"])

(out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
(out_dir / "build_summary.json").write_text(json.dumps(build_summary, indent=2))

print(f"Staging complete: {staged_bin_count} binaries staged across {len(manifest['projects'])} projects.")
print(f"Output directory: {out_dir}")
