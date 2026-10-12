#!/usr/bin/env python3
"""Verify code-preserving inputs and native debug pairing without claiming scores."""

import argparse, hashlib, json, shutil, subprocess
from pathlib import Path
import lief
from elftools.elf.elffile import ELFFile
from import_qualification_msvc import codeview


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def elf_code(path):
    with path.open("rb") as stream:
        binary = ELFFile(stream)
        return {
            section.name: hashlib.sha256(section.data()).hexdigest()
            for section in binary.iter_sections()
            if section["sh_flags"] & 4 and section["sh_type"] != "SHT_NOBITS"
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    base = args.root.resolve() / "staged/qualification-v2"
    for platform in ["linux", "windows", "macos"]:
        for path in sorted((base / platform).rglob("status.json")):
            status = json.loads(path.read_text())
            original = base / status["binary"]
            assert sha(original) == status["binary_sha256"]
            stripped = (
                base / status["stripped"]
                if status.get("stripped")
                else original.with_name(original.name + ".stripped")
            )
            if platform == "linux":
                subprocess.run(
                    ["llvm-strip", "--strip-all", "-o", str(stripped), str(original)],
                    check=True,
                )
                assert elf_code(original) == elf_code(stripped) and elf_code(original)
                with stripped.open("rb") as stream:
                    elf = ELFFile(stream)
                    assert (
                        not elf.has_dwarf_info(strict=True)
                        and elf.get_section_by_name(".symtab") is None
                    )
                status.update(debug_removed=True, symtab_removed=True)
            elif platform == "macos":
                if not stripped.exists():
                    shutil.copy2(original, stripped)
                    subprocess.run(
                        ["llvm-strip", "--strip-all", str(stripped)], check=True
                    )
                before = lief.parse(str(original))
                after = lief.parse(str(stripped))

                def sections(binary):
                    return {
                        (
                            s.segment_name,
                            s.name,
                            s.virtual_address,
                            s.size,
                        ): hashlib.sha256(bytes(s.content)).hexdigest()
                        for s in binary.sections
                        if s.segment_name != "__DWARF"
                    }

                assert sections(before) == sections(after)
                assert not [s for s in after.sections if s.segment_name == "__DWARF"]
                uuids = subprocess.check_output(
                    [
                        "xcrun",
                        "dwarfdump",
                        "--uuid",
                        str(original),
                        str(original) + ".dSYM",
                    ],
                    text=True,
                ).splitlines()
                assert len(uuids) == 2 and uuids[0].split()[1] == uuids[1].split()[1]
                status.update(
                    debug_removed=True,
                    runtime_sections_equal=True,
                    dsym_uuid=uuids[0].split()[1],
                )
            else:
                assert (
                    stripped.exists()
                ), "Use the native evidence importer to remove the PE debug directory"
                assert not list(lief.PE.parse(str(stripped)).debug)

                def sections(binary):
                    return {
                        (s.name, s.virtual_address): hashlib.sha256(
                            bytes(s.content)
                        ).hexdigest()
                        for s in binary.sections
                        if int(s.characteristics) & 0x20000000
                    }

                assert sections(lief.PE.parse(str(original))) == sections(
                    lief.PE.parse(str(stripped))
                )
                guid, age = codeview(original)[1]
                assert (guid, age) == (status["pdb_guid"], status["pdb_age"])
            status.update(
                stripped=str(stripped.relative_to(base)),
                stripped_sha256=sha(stripped),
                code_sections_equal=True,
            )
            status["remaining_gates"] = [
                gate
                for gate in status["remaining_gates"]
                if "input strip" not in gate and "code-section parity" not in gate
            ]
            path.write_text(json.dumps(status, indent=2))
            print(
                platform,
                status["project"],
                status["optimization"],
                "verified",
                flush=True,
            )


if __name__ == "__main__":
    main()
