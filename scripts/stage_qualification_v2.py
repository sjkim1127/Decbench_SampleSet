#!/usr/bin/env python3
"""Import pinned raw payloads without treating missing provenance as qualification."""

import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
from huggingface_hub import hf_hub_download
from elftools.elf.elffile import ELFFile


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--raw-manifest", type=Path, required=True)
    ap.add_argument("--local-raw", type=Path)
    a = ap.parse_args()
    root = a.root.resolve()
    base = root / "staged/qualification-v2"
    base.mkdir(parents=True, exist_ok=True)
    plan = json.loads(a.plan.read_text())
    raw = json.loads(a.raw_manifest.read_text())
    audit = []
    for c in plan["cells"]:
        if c["platform"] != "linux" or c["project"] == "the-powder-toy":
            continue
        proj = raw["projects"][c["project"]]
        sp = proj["sources_archive"]
        src = a.local_raw / sp if a.local_raw else Path("/not-local")
        if not src.exists() or sha(src) != proj["sources_sha256"]:
            src = Path(
                hf_hub_download(
                    plan["raw_corpus"]["repo"],
                    "cpp-compiled/" + sp,
                    repo_type="dataset",
                    revision=plan["raw_corpus"]["revision"],
                    local_dir=root / "downloads/raw",
                )
            )
        assert sha(src) == proj["sources_sha256"]
        dest = base / "sources" / c["project"] / "preprocessed-all-modes.tar.gz"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        for mode in c["optimization_modes"]:
            path = "binaries/" + mode + "/" + c["project"] + "/" + c["target"]
            records = [r for r in raw["binaries"] if r["path"] == path]
            assert records and len({r["sha256"] for r in records}) == 1, path
            record = records[0]
            src = a.local_raw / path if a.local_raw else Path("/not-local")
            if not src.exists() or sha(src) != record["sha256"]:
                src = Path(
                    hf_hub_download(
                        plan["raw_corpus"]["repo"],
                        "cpp-compiled/" + path,
                        repo_type="dataset",
                        revision=plan["raw_corpus"]["revision"],
                        local_dir=root / "downloads/raw",
                    )
                )
            assert sha(src) == record["sha256"] and src.stat().st_size == record["size"]
            out = base / "linux/arm64" / mode / c["project"]
            out.mkdir(parents=True, exist_ok=True)
            target = out / c["target"]
            shutil.copy2(src, target)
            with target.open("rb") as f:
                elf = ELFFile(f)
                assert elf.header["e_machine"] == "EM_AARCH64"
                assert elf.header["e_type"] in ["ET_EXEC", "ET_DYN"]
                assert elf.has_dwarf_info(strict=True)
                code = {
                    s.name: sha_bytes(s.data())
                    for s in elf.iter_sections()
                    if s["sh_flags"] & 4 and s["sh_type"] != "SHT_NOBITS"
                }
            stripped = out / (target.name + ".stripped")
            subprocess.run(
                ["llvm-strip", "--strip-all", "-o", str(stripped), str(target)],
                check=True,
            )
            with stripped.open("rb") as f:
                elf = ELFFile(f)
                assert (
                    not elf.has_dwarf_info(strict=True)
                    and elf.get_section_by_name(".symtab") is None
                )
                after = {
                    s.name: sha_bytes(s.data())
                    for s in elf.iter_sections()
                    if s["sh_flags"] & 4 and s["sh_type"] != "SHT_NOBITS"
                }
                assert code == after
            status = {
                "schema": "decbench-cpp-qualification-cell-v2",
                "state": "imported-payload-verified",
                "platform": "linux",
                "architecture": "aarch64",
                "project": c["project"],
                "optimization": mode,
                "source_repository": c["source_repository"],
                "source_revision": c["source_revision"],
                "binary": str(target.relative_to(base)),
                "binary_sha256": sha(target),
                "stripped": str(stripped.relative_to(base)),
                "stripped_sha256": sha(stripped),
                "code_sections_equal": True,
                "debug_removed": True,
                "symtab_removed": True,
                "source_preprocessed_sha256": proj["sources_sha256"],
                "raw_corpus_revision": plan["raw_corpus"]["revision"],
                "scoring_ready": False,
                "remaining_gates": [
                    "original source archive",
                    "effective per-TU compile/link command provenance",
                    "source-owned function index and TU identity",
                ],
            }
            (out / "status.json").write_text(json.dumps(status, indent=2))
            audit.append(status)
            print(json.dumps(status), flush=True)
    (root / "audit/raw-import.json").write_text(json.dumps(audit, indent=2))


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


if __name__ == "__main__":
    main()
