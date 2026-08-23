#!/usr/bin/env python3
"""DWARF short-name collision measurement for DecBench C++ target validation.

Usage:
    python3 scripts/measure_collisions.py <compiled_dir> [--output report.json]

Where <compiled_dir> is e.g.:
    results/cpp_local/O0/snappy/compiled/

The script:
  1. Finds all ELF linked images (ET_EXEC or ET_DYN) in the directory.
  2. Iterates DW_TAG_subprogram DIEs with DW_AT_low_pc / DW_AT_ranges (concrete
     addresses).
  3. Resolves deferred names through DW_AT_specification and
     DW_AT_abstract_origin chains.
  4. Filters out compiler-probe and CMakeFiles compilation units.
  5. Demangles the raw DWARF name to a fully-qualified C++ name.
  6. Derives the DecBench-style short/unqualified name as the final
     double-colon segment of the demangled name.
  7. Groups distinct function addresses by short name.
  8. Reports:
       source_function_addresses
       unique_short_names
       collision_groups          (short names with >1 distinct address)
       collision_addresses       (addresses belonging to collision groups)
       collision_rate            collision_addresses / source_function_addresses

Dependencies:
    pip install pyelftools  (already in decbench-compile Docker image)
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

try:
    import cxxfilt
    _HAVE_CXXFILT = True
except ImportError:
    _HAVE_CXXFILT = False

from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFError


def _is_linked_elf(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                return False
            f.seek(16)
            e_type = struct.unpack("<H", f.read(2))[0]
            return e_type in (2, 3)
    except (OSError, struct.error):
        return False


def _demangle(raw: str) -> str:
    if not raw.startswith("_Z"):
        return raw
    if _HAVE_CXXFILT:
        try:
            return cxxfilt.demangle(raw)
        except Exception:
            pass
    try:
        result = subprocess.run(
            ["c++filt", raw],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or raw
    except Exception:
        return raw


def _short_name(demangled: str) -> str:
    name = demangled
    paren = name.find("(")
    if paren != -1:
        name = name[:paren]
    name = re.sub(r"<[^<>]*>", "", name)
    parts = name.split("::")
    short = parts[-1].strip()
    return short if short else name


_FILTER_KEYWORDS = frozenset([
    "CMakeFiles", "cmake_install", "compiler_id",
    "CMakeCXXCompilerId", "CMakeCCompilerId",
    "feature_tests", "CompilerIdCXX", "CompilerIdC",
])


def _is_compiler_probe_cu(cu_name: str) -> bool:
    return any(kw in cu_name for kw in _FILTER_KEYWORDS)


def _get_attr_value(die, attr_name: str):
    attr = die.attributes.get(attr_name)
    return attr.value if attr else None


def _has_concrete_address(die) -> bool:
    return (
        "DW_AT_low_pc" in die.attributes
        or "DW_AT_ranges" in die.attributes
    )


def _resolve_name(die, cu_die_map: dict) -> str | None:
    name_attr = die.attributes.get("DW_AT_name")
    if name_attr:
        raw = name_attr.value
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        return raw
    for ref_attr in ("DW_AT_specification", "DW_AT_abstract_origin"):
        ref = _get_attr_value(die, ref_attr)
        if ref is not None:
            ref_die = cu_die_map.get(ref)
            if ref_die is not None:
                result = _resolve_name(ref_die, cu_die_map)
                if result:
                    return result
    return None


def _resolve_linkage_name(die, cu_die_map: dict) -> str | None:
    for attr in ("DW_AT_linkage_name", "DW_AT_MIPS_linkage_name"):
        ln = die.attributes.get(attr)
        if ln:
            v = ln.value
            return v.decode("utf-8", errors="replace") if isinstance(v, bytes) else str(v)
    for ref_attr in ("DW_AT_specification", "DW_AT_abstract_origin"):
        ref = _get_attr_value(die, ref_attr)
        if ref is not None:
            ref_die = cu_die_map.get(ref)
            if ref_die is not None:
                result = _resolve_linkage_name(ref_die, cu_die_map)
                if result:
                    return result
    return None


def measure_elf(elf_path: Path, verbose: bool = False) -> dict:
    name_to_addrs: dict[str, set[int]] = defaultdict(set)
    addr_to_info: dict[int, tuple[str, str]] = {}

    with elf_path.open("rb") as f:
        try:
            elf = ELFFile(f)
        except ELFError as e:
            return {"error": str(e), "path": str(elf_path)}

        if not elf.has_dwarf_info():
            return {
                "path": str(elf_path),
                "error": "no DWARF info",
                "source_function_addresses": 0,
                "unique_short_names": 0,
                "collision_groups": 0,
                "collision_addresses": 0,
                "collision_rate": 0.0,
            }

        dwarf = elf.get_dwarf_info()
        last_cu_name = ""

        for CU in dwarf.iter_CUs():
            top_die = CU.get_top_DIE()
            cu_name_attr = top_die.attributes.get("DW_AT_name")
            cu_name = ""
            if cu_name_attr:
                v = cu_name_attr.value
                cu_name = v.decode("utf-8", errors="replace") if isinstance(v, bytes) else str(v)
            last_cu_name = cu_name

            if _is_compiler_probe_cu(cu_name):
                if verbose:
                    print(f"    [SKIP probe CU] {cu_name}", file=sys.stderr)
                continue

            cu_die_map: dict[int, object] = {}
            for die in CU.iter_DIEs():
                cu_die_map[die.offset] = die

            for die in CU.iter_DIEs():
                if die.tag != "DW_TAG_subprogram":
                    continue
                if not _has_concrete_address(die):
                    continue
                inline_attr = die.attributes.get("DW_AT_inline")
                if inline_attr and inline_attr.value != 0:
                    continue

                low_pc_attr = die.attributes.get("DW_AT_low_pc")
                if low_pc_attr is None:
                    continue
                low_pc = int(low_pc_attr.value) if low_pc_attr.value else None
                if low_pc is None or low_pc == 0:
                    continue

                linkage = _resolve_linkage_name(die, cu_die_map)
                if linkage:
                    demangled = _demangle(linkage)
                else:
                    raw_name = _resolve_name(die, cu_die_map)
                    if not raw_name:
                        continue
                    demangled = _demangle(raw_name) if raw_name.startswith("_Z") else raw_name

                short = _short_name(demangled)
                name_to_addrs[short].add(low_pc)
                addr_to_info[low_pc] = (short, demangled)

    total_addresses = len(addr_to_info)
    unique_short_names = len(name_to_addrs)

    collision_groups = {name: addrs for name, addrs in name_to_addrs.items() if len(addrs) > 1}
    collision_address_set: set[int] = set()
    for addrs in collision_groups.values():
        collision_address_set.update(addrs)

    collision_count = len(collision_address_set)
    collision_rate = (collision_count / total_addresses) if total_addresses > 0 else 0.0

    top_collisions = sorted(
        [
            {
                "short_name": name,
                "distinct_addresses": len(addrs),
                "addresses": sorted(hex(a) for a in addrs),
                "example_qualified": [addr_to_info[a][1] for a in sorted(addrs)[:3]],
            }
            for name, addrs in collision_groups.items()
        ],
        key=lambda x: -x["distinct_addresses"],
    )[:25]

    return {
        "path": str(elf_path),
        "source_function_addresses": total_addresses,
        "unique_short_names": unique_short_names,
        "collision_groups": len(collision_groups),
        "collision_addresses": collision_count,
        "collision_rate": round(collision_rate, 6),
        "collision_rate_pct": f"{collision_rate * 100:.2f}%",
        "top_collision_groups": top_collisions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure DWARF short-name collisions")
    parser.add_argument("compiled_dir", help="Path to compiled/ output directory")
    parser.add_argument("--output", "-o", default=None, help="JSON output path")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    compiled = Path(args.compiled_dir)
    if not compiled.is_dir():
        print(f"ERROR: {compiled} is not a directory", file=sys.stderr)
        return 1

    elf_paths = [p for p in compiled.iterdir() if p.is_file() and _is_linked_elf(p)]

    if not elf_paths:
        print(f"WARNING: No linked ELF images found in {compiled}", file=sys.stderr)
        result = {"compiled_dir": str(compiled), "elf_images": [], "elf_image_count": 0, "aggregated": {}}
    else:
        per_image = []
        for elf_path in sorted(elf_paths):
            if args.verbose:
                print(f"  Measuring {elf_path.name} ...", file=sys.stderr, flush=True)
            per_image.append(measure_elf(elf_path, verbose=args.verbose))

        total_addresses = sum(r.get("source_function_addresses", 0) for r in per_image)
        total_collision_addresses = sum(r.get("collision_addresses", 0) for r in per_image)
        agg_rate = (total_collision_addresses / total_addresses) if total_addresses > 0 else 0.0

        result = {
            "compiled_dir": str(compiled),
            "elf_images": [str(p) for p in sorted(elf_paths)],
            "elf_image_count": len(elf_paths),
            "per_image": per_image,
            "aggregated": {
                "source_function_addresses": total_addresses,
                "collision_addresses": total_collision_addresses,
                "collision_rate": round(agg_rate, 6),
                "collision_rate_pct": f"{agg_rate * 100:.2f}%",
            },
        }

    output_str = json.dumps(result, indent=2)

    if args.output:
        Path(args.output).write_text(output_str)
        print(f"Report written to {args.output}")
    else:
        print(output_str)

    agg = result.get("aggregated", {})
    print(
        f"\nSUMMARY: {result.get('elf_image_count', 0)} ELF image(s) | "
        f"{agg.get('source_function_addresses', 0)} source addresses | "
        f"collision_rate={agg.get('collision_rate_pct', 'N/A')}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
