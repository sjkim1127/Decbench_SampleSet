#!/usr/bin/env python3
"""Stage DecBench C++ compile output into the official dataset layout.

Input : decbench/results/cpp_local/<opt>/<project>/compiled/
Output: <out>/binaries/<opt>/<project>/<linked image>
        <out>/sources/<project>/<file>        (content-deduplicated across opts)
        <out>/cpp-compiled/manifest.json      (sha256, build metadata; no scoring)
Ground truth (source + DWARF binaries) is kept separate from any scoring policy.
"""
import hashlib, json, shutil, sys
from pathlib import Path

src_root = Path(sys.argv[1])
out = Path(sys.argv[2])
report = {(r["project"], r["opt"]): r for r in json.loads((src_root / "compile_report.json").read_text())}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def is_elf(p):
    with p.open("rb") as f:
        return f.read(4) == b"\x7fELF"


manifest = {"language": "c++", "compiler": "GCC/G++ 13.3.0 (Ubuntu 24.04 aarch64)",
            "ground_truth": "DWARF + preprocessed .ii", "binaries": [], "sources": {},
            "source_variants": []}
for opt_dir in sorted(p for p in src_root.iterdir() if p.is_dir()):
    for proj_dir in sorted(p for p in opt_dir.iterdir() if p.is_dir()):
        opt, proj = opt_dir.name, proj_dir.name
        comp = proj_dir / "compiled"
        for f in sorted(comp.iterdir()):
            if not f.is_file():
                continue
            if is_elf(f):
                dst = out / "binaries" / opt / proj / f.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                manifest["binaries"].append({
                    "path": str(dst.relative_to(out)), "opt": opt, "project": proj,
                    "sha256": sha(f), "size": f.stat().st_size,
                    "compile_ok": report[(proj, opt)]["ok"]})
            else:
                h = sha(f)
                dst = out / "sources" / proj / f.name
                if dst.exists() and sha(dst) != h:
                    # content differs between opt levels: keep per-opt variant
                    dst = out / "sources" / proj / "_variants" / opt / f.name
                    manifest["source_variants"].append(str(dst.relative_to(out)))
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(f, dst)
                manifest["sources"].setdefault(proj, {})[f.name] = h

(out / "cpp-compiled").mkdir(parents=True, exist_ok=True)
(out / "cpp-compiled" / "manifest.json").write_text(json.dumps(manifest, indent=2))
shutil.copy2(src_root / "compile_report.json", out / "cpp-compiled" / "compile_report.json")
print(len(manifest["binaries"]), "binaries;",
      sum(len(v) for v in manifest["sources"].values()), "source entries;",
      len(manifest["source_variants"]), "variants")
