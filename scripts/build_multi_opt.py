#!/usr/bin/env python3
"""Build one pinned repo at one DecBench opt level and collect oracle artifacts.

Runs inside the build container. Reuses probe_linux.build/inspect and only swaps
the optimization flags (probe_linux reads cp.O0_FLAGS at call time).

Output: <out>/<opt>/<project>/compiled/<relative path>   (linked ELF with DWARF, *.ii)
        <out>/<opt>/<project>/result.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import corpus_pipeline as cp
import probe_linux as pl

BASE = "-g -fno-builtin -save-temps=obj"
OPT_FLAGS = {
    "O0": f"-O0 {BASE}",
    "O2": f"-O2 {BASE}",
    "O2-noinline": f"-O2 -fno-inline {BASE}",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--opt", required=True, choices=OPT_FLAGS)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-elf", type=int, default=25)
    ap.add_argument("--extra-flags", default="")
    ap.add_argument("--timeout-scale", type=int, default=1)
    a = ap.parse_args()

    project = a.repo.split("/")[1]
    dest = Path(a.out) / a.opt / project
    shutil.rmtree(dest, ignore_errors=True)
    (dest / "compiled").mkdir(parents=True)
    cp.O0_FLAGS = (OPT_FLAGS[a.opt] + " " + a.extra_flags).strip()
    if a.timeout_scale > 1:
        _run = cp.run
        cp.run = lambda cmd, cwd, env, timeout, *r, **k: _run(cmd, cwd, env, timeout * a.timeout_scale, *r, **k)
    res: dict = {"repo": a.repo, "revision": a.revision, "opt": a.opt,
                 "flags": cp.O0_FLAGS, "ok": False, "timeout_scale": a.timeout_scale}

    with tempfile.TemporaryDirectory(prefix="decbench-") as td:
        root = Path(td) / "src"
        env = os.environ.copy()
        for cmd in (["git", "init", "-q", str(root)],
                    ["git", "-C", str(root), "remote", "add", "origin", f"https://github.com/{a.repo}.git"],
                    ["git", "-C", str(root), "fetch", "-q", "--depth", "1", "origin", a.revision],
                    ["git", "-C", str(root), "checkout", "-q", "FETCH_HEAD"],
                    ["git", "-C", str(root), "submodule", "update", "-q", "--init", "--recursive", "--depth", "1"]):
            r = cp.run(cmd, Path(td), env, 300)
            if r["returncode"] != 0 and "submodule" not in cmd:
                res["failure_stage"] = "clone"
                res["output"] = r.get("output", "")[-2000:]
                (dest / "result.json").write_text(json.dumps(res, indent=2))
                return 0
        system = cp.detect_build_system(root)
        res["build_system"] = system
        ok, steps, search_root = pl.build(root, system)
        res["steps"] = [{k: (v[-1500:] if k == "output" and isinstance(v, str) else v)
                         for k, v in s.items()} for s in steps]
        if not ok:
            res["failure_stage"] = "build"
            (dest / "result.json").write_text(json.dumps(res, indent=2))
            return 0
        search_root = search_root if search_root.exists() else root
        elfs, seen = [], set()
        for p in search_root.rglob("*"):
            if (p.is_file() and not p.is_symlink() and ".git" not in p.parts
                    and not pl.is_toolchain_probe(p, search_root) and cp.is_elf_linked(p)
                    and cp.dwarf_present(p)):
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    elfs.append(p)
        elfs.sort(key=lambda q: q.stat().st_size, reverse=True)
        res["elf_found"] = len(elfs)
        elfs = elfs[: a.max_elf]
        iis = [p for p in search_root.rglob("*.ii")
               if p.is_file() and not pl.is_toolchain_probe(p, search_root)]
        for p in elfs + iis:
            t = dest / "compiled" / p.relative_to(search_root)
            t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, t)
        res.update(linked_binaries=len(elfs), i_files=len(iis),
                   binaries=[str(p.relative_to(search_root)) for p in elfs],
                   gcc=subprocess.check_output(["g++", "--version"], text=True).splitlines()[0],
                   ok=bool(elfs) and bool(iis))
    (dest / "result.json").write_text(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
