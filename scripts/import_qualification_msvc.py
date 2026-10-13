#!/usr/bin/env python3
"""Import artifact-backed native MSVC evidence with PE/PDB identity checks."""

import argparse, hashlib, json, re, shutil, struct, subprocess, tarfile, uuid
from pathlib import Path
import lief


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def text_sections(p):
    b = lief.PE.parse(str(p))
    return {
        (s.name, s.virtual_address): hashlib.sha256(bytes(s.content)).hexdigest()
        for s in b.sections
        if int(s.characteristics) & 0x20000000
    }


def codeview(p):
    data = p.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    assert data[pe : pe + 4] == b"PE\0\0"
    count = struct.unpack_from("<H", data, pe + 6)[0]
    size = struct.unpack_from("<H", data, pe + 20)[0]
    optional = pe + 24
    magic = struct.unpack_from("<H", data, optional)[0]
    dirs = optional + (112 if magic == 0x20B else 96)
    rva, total = struct.unpack_from("<II", data, dirs + 48)
    sections = []
    for i in range(count):
        at = optional + size + 40 * i
        vsize, va, rsize, raw = struct.unpack_from("<IIII", data, at + 8)
        sections.append((va, max(vsize, rsize), raw))

    def fileoff(addr):
        return next(
            raw + addr - va for va, length, raw in sections if va <= addr < va + length
        )

    assert total and total % 28 == 0
    debug = fileoff(rva)
    identities = []
    for at in range(debug, debug + total, 28):
        kind, length, addr, raw = struct.unpack_from("<IIII", data, at + 12)
        if kind == 2 and data[raw : raw + 4] == b"RSDS":
            identities.append(
                (
                    str(uuid.UUID(bytes_le=data[raw + 4 : raw + 20])).upper(),
                    struct.unpack_from("<I", data, raw + 20)[0],
                )
            )
    assert len(identities) == 1, identities
    return dirs + 48, identities[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--projects", nargs="+", default=["detours", "winsparkle"])
    ap.add_argument("--evidence-root", type=Path)
    ap.add_argument("--github-run", type=int, default=38208011147)
    a = ap.parse_args()
    r = a.root.resolve()
    base = r / "staged/qualification-v2"
    plan = json.loads(a.plan.read_text())
    evidence_root = a.evidence_root or r / "msvc-existing-evidence"
    available = {c["project"] for c in plan["cells"] if c["platform"] == "windows"}
    assert set(a.projects) <= available, "Unplanned Windows project"
    audit = []
    for cell in plan["cells"]:
        name = cell["project"]
        if cell["platform"] != "windows" or name not in a.projects:
            continue
        for mode in cell["optimization_modes"]:
            src = evidence_root / name / mode
            q = json.loads((src / "qualification.json").read_text(encoding="utf-8-sig"))
            assert q["target"] == name and q["optimization"] == mode
            assert q["project_procedure_records"] > 0
            replay = src / "preprocessed/source-map.json"
            if replay.exists():
                provenance = json.loads(
                    (src / "build-provenance.json").read_text(encoding="utf-8-sig")
                )
                assert provenance["source_revision"] == cell["source_revision"]
                assert provenance["source_repository"] == cell["source_repository"]
                assert provenance["optimization"] == mode
                mappings = json.loads(replay.read_text(encoding="utf-8-sig"))
                assert mappings and (src / "original.tar.gz").is_file()
                for record in mappings:
                    path = src / "preprocessed" / record["preprocessed"]
                    assert path.is_file() and path.stat().st_size > 0
                    flags = [flag.lower() for flag in record["preprocess_argv"]]
                    optimization_flags = [
                        flag for flag in flags if re.fullmatch(r"[-/]o[d012sx]", flag)
                    ]
                    expected = "/od" if mode == "O0" else "/o2"
                    assert (
                        optimization_flags and optimization_flags[-1] == expected
                    ), record["source"]
                    if mode in ["O0", "O2-noinline"]:
                        inline_flags = [
                            flag
                            for flag in flags
                            if re.fullmatch(r"[-/]ob[0123]", flag)
                        ]
                        assert inline_flags and inline_flags[-1] == "/ob0", record[
                            "source"
                        ]
                    assert "/gl" not in flags, "Unexpected LTCG compilation"
            binary = src / "binary" / q["linked_image"]
            pdb = src / "binary" / q["pdb"]
            binary_digest = sha(binary)
            out = base / "windows/x86_64" / mode / name
            out.mkdir(parents=True, exist_ok=True)
            native_guid, native_age = codeview(binary)[1]
            summary = subprocess.check_output(
                ["llvm-pdbutil", "dump", "-summary", str(pdb)], text=True
            )
            pdb_guid = re.search(r"GUID:\s*\{([^}]+)\}", summary).group(1).upper()
            pdb_age = int(re.search(r"Age:\s*(\d+)", summary).group(1))
            assert (native_guid, native_age) == (pdb_guid, pdb_age)
            assert "Has Types: true" in summary and "Is stripped: false" in summary
            before = text_sections(binary)
            target = out / binary.name
            shutil.copy2(binary, target)
            shutil.copy2(pdb, out / pdb.name)
            stripped = out / (binary.name + ".stripped")
            data = bytearray(binary.read_bytes())
            offset, _ = codeview(binary)
            struct.pack_into("<II", data, offset, 0, 0)
            stripped.write_bytes(data)
            assert not list(lief.PE.parse(str(stripped)).debug)
            assert before == text_sections(stripped)
            shutil.copy2(
                src / "qualification.json", out / "upstream-qualification.json"
            )
            shutil.copy2(
                src / "project-procedures.json", out / "project-procedures.json"
            )
            shutil.copy2(src / "build.log", out / "build.log")
            (out / "pdb-summary.txt").write_text(summary)
            if replay.exists():
                for file in [
                    "build-provenance.json",
                    "compile_commands.json",
                    "original.tar.gz",
                ]:
                    shutil.copy2(src / file, out / file)
                with tarfile.open(out / "preprocessed.tar.gz", "w:gz") as archive:
                    archive.add(src / "preprocessed", arcname="preprocessed")
                for file in ["CMakeCache.txt", "target-commands.txt"]:
                    if (src / file).is_file():
                        shutil.copy2(src / file, out / file)
            procedures = json.loads(
                (src / "project-procedures.json").read_text(encoding="utf-8-sig")
            )
            pe = lief.PE.parse(str(binary))
            identities = []
            for proc in procedures:
                if not proc.get("project_owned") or proc["code_size"] <= 0:
                    continue
                section, offset = proc["address"].split(":")
                section_index = int(section, 16) - 1
                assert 0 <= section_index < len(pe.sections)
                rva = pe.sections[section_index].virtual_address + int(offset)
                section = pe.sections[section_index]
                assert int(section.characteristics) & 0x20000000
                assert int(offset) + proc["code_size"] <= len(
                    section.content
                ), "Unmapped PDB procedure"
                identities.append(
                    {
                        **proc,
                        "binary_sha256": binary_digest,
                        "rva": rva,
                        "va": pe.optional_header.imagebase + rva,
                        "identity": [binary_digest, rva],
                    }
                )
            assert identities
            (out / "function-identities.json").write_text(
                json.dumps(identities, indent=2)
            )
            status = {
                "state": "imported-pe-pdb-verified",
                "project": name,
                "platform": "windows",
                "architecture": "x86_64",
                "optimization": mode,
                "source_repository": cell["source_repository"],
                "source_revision": cell["source_revision"],
                "binary": str(target.relative_to(base)),
                "binary_sha256": sha(target),
                "stripped": str(stripped.relative_to(base)),
                "stripped_sha256": sha(stripped),
                "pdb_sha256": sha(out / pdb.name),
                "pdb_guid": native_guid,
                "pdb_age": native_age,
                "code_sections_equal": True,
                "debug_directory_removed": True,
                "project_owned_function_count": len(identities),
                "project_ownership_method": q["project_ownership_method"],
                "ownership_scope": "procedures in source-matched compilands; header-origin and dependency ownership need per-procedure verification",
                "evidence_github_run": a.github_run,
                "preprocessed_tu_count": len(mappings) if replay.exists() else 0,
                "scoring_ready": False,
                "remaining_gates": [
                    "original source archive and preprocessed TU replay",
                    "full source-range identity correspondence",
                    "MSVC source/ABI type evaluation adapter",
                ],
            }
            if replay.exists():
                status["effective_optimization_profile_verified"] = True
                status["build_environment"] = provenance["environment"]
                status["preprocessed_archive"] = str(
                    (out / "preprocessed.tar.gz").relative_to(base)
                )
                status["build_provenance"] = str(
                    (out / "build-provenance.json").relative_to(base)
                )
                status["remaining_gates"].remove(
                    "original source archive and preprocessed TU replay"
                )
            (out / "status.json").write_text(json.dumps(status, indent=2))
            audit.append(status)
            print(json.dumps(status), flush=True)
    (r / f"audit/msvc-import-{a.github_run}.json").write_text(
        json.dumps(audit, indent=2)
    )


if __name__ == "__main__":
    main()
