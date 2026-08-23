#!/usr/bin/env python3
"""DWARF short-name collision measurement for DecBench C++ target validation.

DecBench-Exact Matching & Identity Model:
  1. Collision Identity Key: Resolved DW_AT_name following DW_AT_specification
     and DW_AT_abstract_origin chains across DIEs (matches DecBench binfmt.die_attr_owner).
  2. Diagnostic Display: Demangled DW_AT_linkage_name (for human review in reports).
  3. Source-Stem Filter: Exact DecBench evalkit/resolve.py logic:
     - Collects *.i / *.ii translation unit stems from the compiled directory.
     - Builds stem_index via strip_source_ext() and build_stem_index().
     - Resolves DW_AT_decl_file for each concrete subprogram and matches its basename stem
       against the stem_index (including -stem / _stem object-prefix fallback).
     - Raw metrics include all concrete subprograms in non-probe CUs.
     - Project metrics include only functions declared in project translation units.

Usage:
    python3 scripts/measure_collisions.py <compiled_dir> [--output report.json]
"""

from __future__ import annotations

import argparse
import json
import os
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


C_SOURCE_EXTS = (".c",)
CXX_SOURCE_EXTS = (".cc", ".cpp", ".cxx", ".c++", ".C")
SOURCE_EXTS = (*C_SOURCE_EXTS, *CXX_SOURCE_EXTS)
PREPROC_EXTS = (".i", ".ii")

_CXX_LANGS = frozenset({0x04, 0x19, 0x1A, 0x21, 0x2A, 0x2B, 0x33})
_SPEC_ONLY = ("DW_AT_specification",)
_SPEC_AND_ORIGIN = ("DW_AT_specification", "DW_AT_abstract_origin")

_PROBE_KEYWORDS = frozenset([
    "CMakeFiles", "cmake_install", "CMakeCXXCompilerId",
    "CMakeCCompilerId", "CompilerIdCXX", "CompilerIdC", "feature_tests",
])


def strip_source_ext(name: str) -> str:
    """Drop a trailing C/C++ source extension from name (DecBench utils.langs)."""
    stem, ext = os.path.splitext(name)
    return stem if ext in SOURCE_EXTS else name


def preprocessed_stems(directory: Path) -> list[str]:
    """Collect all preprocessed translation unit stems (*.i, *.ii)."""
    stems = []
    for ext in PREPROC_EXTS:
        for p in sorted(directory.glob(f"*{ext}")):
            stems.append(p.stem)
    return stems


def build_stem_index(stems: list[str]) -> dict[str, str]:
    """{strip_source_ext(stem): stem} (DecBench utils.langs)."""
    index: dict[str, str] = {}
    for stem in sorted(stems):
        key = strip_source_ext(stem)
        index[key] = stem
    return index


def _is_linked_elf(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            magic = f.read(4)
            if magic != b"\x7fELF":
                return False
            f.seek(16)
            e_type = struct.unpack("<H", f.read(2))[0]
            return e_type in (2, 3)  # ET_EXEC=2, ET_DYN=3
    except (OSError, struct.error):
        return False


def _demangle(raw: str) -> str:
    if not raw or not raw.startswith("_Z"):
        return raw or ""
    if _HAVE_CXXFILT:
        try:
            return cxxfilt.demangle(raw)
        except Exception:
            pass
    try:
        r = subprocess.run(["c++filt", raw], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or raw
    except Exception:
        return raw


def _is_probe_cu(cu_name: str) -> bool:
    return any(kw in cu_name for kw in _PROBE_KEYWORDS)


def cu_is_cxx(cu) -> bool:
    """True when the compilation unit's DW_AT_language is a C++ dialect."""
    try:
        attr = cu.get_top_DIE().attributes.get("DW_AT_language")
    except Exception:
        return False
    return attr is not None and attr.value in _CXX_LANGS


def die_attr_owner(die, name: str):
    """(attribute, owning DIE) following specification/origin chains (DecBench binfmt)."""
    cur = die
    refs = _SPEC_AND_ORIGIN if cu_is_cxx(die.cu) else _SPEC_ONLY
    for _ in range(5):
        attr = cur.attributes.get(name)
        if attr is not None:
            return attr, cur
        nxt = None
        for ref in refs:
            if ref in cur.attributes:
                try:
                    nxt = cur.get_DIE_from_attribute(ref)
                except Exception:
                    nxt = None
                break
        if nxt is None:
            return None, None
        cur = nxt
    return None, None


def die_str_attr(die, name: str) -> str | None:
    attr, _ = die_attr_owner(die, name)
    if attr is None:
        return None
    val = attr.value
    return val.decode("utf-8", "replace") if isinstance(val, bytes) else str(val)


def cu_file_table(dwarfinfo, cu, cache: dict[int, list] | None = None) -> list:
    """A CU's DW_AT_decl_file index table, memoized by CU offset (DecBench binfmt)."""
    if cache is not None:
        cached = cache.get(cu.cu_offset)
        if cached is not None:
            return cached
    lp = dwarfinfo.line_program_for_CU(cu)
    version = 4
    if lp is not None:
        version = lp.header.get("version", cu.header.get("version", 4))
    files: list = [] if version >= 5 else [None]
    if lp is not None and lp.header and lp.header.get("file_entry"):
        for fe in lp["file_entry"]:
            nm = fe.name
            files.append(nm.decode("utf-8", "replace") if isinstance(nm, bytes) else str(nm))
    if cache is not None:
        cache[cu.cu_offset] = files
    return files


def get_decl_file_basename(die, dwarfinfo, file_tables: dict) -> str:
    fi, fi_owner = die_attr_owner(die, "DW_AT_decl_file")
    if fi is None or fi_owner is None:
        return ""
    files = cu_file_table(dwarfinfo, fi_owner.cu, file_tables)
    if 0 <= fi.value < len(files) and files[fi.value]:
        return os.path.basename(files[fi.value])
    return ""


def _make_stats(n2a: dict[str, set[int]], a2diag: dict[int, str]) -> dict:
    all_addrs: set[int] = set()
    for s in n2a.values():
        all_addrs.update(s)
    total = len(all_addrs)
    unique = len(n2a)
    coll = {n: a for n, a in n2a.items() if len(a) > 1}
    coll_set: set[int] = set()
    for addrs in coll.values():
        coll_set.update(addrs)
    n_coll = len(coll_set)
    rate = n_coll / total if total > 0 else 0.0
    top = sorted(
        [
            {
                "short_name": nm,
                "distinct_addresses": len(addrs),
                "addresses": sorted(hex(a) for a in addrs),
                "example_qualified": [a2diag[a] for a in sorted(addrs)[:3]],
            }
            for nm, addrs in coll.items()
        ],
        key=lambda x: -x["distinct_addresses"],
    )[:25]
    return {
        "source_function_addresses": total,
        "unique_short_names": unique,
        "collision_groups": len(coll),
        "collision_addresses": n_coll,
        "collision_rate": round(rate, 6),
        "collision_rate_pct": f"{rate * 100:.2f}%",
        "top_collision_groups": top,
    }


def measure_elf(elf_path: Path, stem_index: dict[str, str], verbose: bool = False) -> dict:
    raw_n2a: dict[str, set[int]] = defaultdict(set)
    raw_a2diag: dict[int, str] = {}
    proj_n2a: dict[str, set[int]] = defaultdict(set)
    proj_a2diag: dict[int, str] = {}

    cu_stats = {"total": 0, "probe": 0, "non_project_subprograms": 0, "project_subprograms": 0}

    with elf_path.open("rb") as f:
        try:
            elf = ELFFile(f)
        except ELFError as e:
            return {"path": str(elf_path), "error": str(e)}

        if not elf.has_dwarf_info():
            return {
                "path": str(elf_path),
                "error": "no DWARF info",
                "raw": _make_stats({}, {}),
                "project": _make_stats({}, {}),
            }

        dwarf = elf.get_dwarf_info()
        file_tables: dict[int, list] = {}

        for CU in dwarf.iter_CUs():
            cu_stats["total"] += 1
            top = CU.get_top_DIE()
            raw_cu_name = top.attributes.get("DW_AT_name")
            cu_name = raw_cu_name.value.decode("utf-8", "replace") if raw_cu_name and isinstance(raw_cu_name.value, bytes) else str(raw_cu_name or "")

            if _is_probe_cu(cu_name):
                cu_stats["probe"] += 1
                if verbose:
                    print(f"    [skip probe CU] {cu_name}", file=sys.stderr)
                continue

            for die in CU.iter_DIEs():
                if die.tag != "DW_TAG_subprogram" or "DW_AT_low_pc" not in die.attributes:
                    continue

                low_pc = die.attributes["DW_AT_low_pc"].value
                if low_pc == 0:
                    continue

                # 1. Resolve exact unqualified function name (DecBench identity key)
                name = die_str_attr(die, "DW_AT_name")
                if not name:
                    continue

                # 2. Resolve linkage name for diagnostic display
                raw_link = die_str_attr(die, "DW_AT_linkage_name") or die_str_attr(die, "DW_AT_MIPS_linkage_name") or ""
                demangled = _demangle(raw_link) if raw_link else name

                # 3. Resolve source declaration stem matching DecBench evalkit/resolve.py
                decl_basename = get_decl_file_basename(die, dwarf, file_tables)
                stem = strip_source_ext(decl_basename) if decl_basename else ""

                is_project = False
                if stem and stem_index:
                    if stem in stem_index or any(s.endswith("-" + stem) or s.endswith("_" + stem) for s in stem_index):
                        is_project = True

                raw_n2a[name].add(low_pc)
                raw_a2diag[low_pc] = demangled

                if is_project:
                    cu_stats["project_subprograms"] += 1
                    proj_n2a[name].add(low_pc)
                    proj_a2diag[low_pc] = demangled
                else:
                    cu_stats["non_project_subprograms"] += 1

    return {
        "path": str(elf_path),
        "cu_stats": cu_stats,
        "raw": _make_stats(raw_n2a, raw_a2diag),
        "project": _make_stats(proj_n2a, proj_a2diag),
    }


def _agg(per_image: list[dict], key: str) -> dict:
    addrs = sum(r.get(key, {}).get("source_function_addresses", 0) for r in per_image)
    coll = sum(r.get(key, {}).get("collision_addresses", 0) for r in per_image)
    rate = coll / addrs if addrs > 0 else 0.0
    return {
        "source_function_addresses": addrs,
        "collision_addresses": coll,
        "collision_rate": round(rate, 6),
        "collision_rate_pct": f"{rate * 100:.2f}%",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Measure DWARF short-name collisions (DecBench-exact source-stem matching)")
    ap.add_argument("compiled_dir")
    ap.add_argument("--output", "-o", default=None)
    ap.add_argument("--exclude-image", nargs="*", default=[], metavar="NAME")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    compiled = Path(args.compiled_dir)
    if not compiled.is_dir():
        print(f"ERROR: {compiled} is not a directory", file=sys.stderr)
        return 1

    stems = preprocessed_stems(compiled)
    stem_index = build_stem_index(stems)

    exclude = set(args.exclude_image)
    elf_paths = sorted(
        p for p in compiled.iterdir()
        if p.is_file() and p.name not in exclude and _is_linked_elf(p)
    )

    # Format paths relative to repo root / working dir
    clean_dir = str(compiled)
    if "results/cpp_local" in clean_dir:
        clean_dir = "results/cpp_local" + clean_dir.split("results/cpp_local")[-1]

    if not elf_paths:
        print(f"WARNING: No ELF images in {compiled}", file=sys.stderr)
        result = {
            "compiled_dir": clean_dir,
            "source_stems": stems,
            "elf_image_count": 0,
            "aggregated_raw": {},
            "aggregated_project": {},
        }
    else:
        per_image = []
        for ep in elf_paths:
            if args.verbose:
                print(f"  [{ep.name}] (stems={len(stems)})", file=sys.stderr)
            img_res = measure_elf(ep, stem_index, args.verbose)
            img_res["path"] = ep.name
            per_image.append(img_res)

        result = {
            "compiled_dir": clean_dir,
            "source_stems": stems,
            "exclude_images": list(exclude),
            "elf_images": [p.name for p in elf_paths],
            "elf_image_count": len(elf_paths),
            "per_image": per_image,
            "aggregated_raw": _agg(per_image, "raw"),
            "aggregated_project": _agg(per_image, "project"),
        }

    out = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(out)
        print(f"Report: {args.output}")
    else:
        print(out)

    r = result.get("aggregated_raw", {})
    p = result.get("aggregated_project", {})
    parts = compiled.parts
    tag = f"{parts[-3]}/{parts[-2]}" if len(parts) >= 3 else str(compiled)
    print(
        f"SUMMARY [{tag}]  stems={len(stems)}"
        f"  raw={r.get('source_function_addresses','?')} addrs @{r.get('collision_rate_pct','?')}"
        f"  project={p.get('source_function_addresses','?')} addrs @{p.get('collision_rate_pct','?')}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
