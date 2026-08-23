#!/usr/bin/env python3
"""DWARF short-name collision measurement for DecBench C++ target validation.

Usage:
    python3 scripts/measure_collisions.py <compiled_dir> [OPTIONS]

Options:
    --output FILE           Write JSON report to FILE instead of stdout
    --exclude-image NAME    Skip ELF images by basename (repeatable)
    --verbose               Print per-CU classification to stderr

The script produces TWO collision-rate measurements per ELF image:

  raw     – all concrete DWARF subprograms, excluding only cmake probe CUs.
  project – functions whose fully-qualified demangled name does NOT start with
             a stdlib/system namespace prefix (std::, __gnu_cxx::, __cxxabiv::,
             __detail::, etc.).  This is the reproducible "project-owned" rate.

Both sets report:
    source_function_addresses   (distinct low_pc values)
    unique_short_names
    collision_groups            (short names -> >1 address)
    collision_addresses         (addresses belonging to collision groups)
    collision_rate              collision_addresses / source_function_addresses

NOTE on DecBench identity fidelity
-----------------------------------
DecBench's C++ matching logic (at the pinned revision d9f4f8a) resolves
DW_AT_specification / DW_AT_abstract_origin chains to obtain DW_AT_name, then
applies its own short-name trimming. This script uses the same chain resolution
but derives the short name from DW_AT_linkage_name (demangled) when available,
which is usually more reliable. The resulting short names are equivalent for
most functions but may differ for template specialisations and some corner cases
(e.g. anonymous / unnamed functions). Treat the collision numbers as a close
diagnostic approximation, not a byte-for-byte replay of DecBench's own counter.

Dependencies:
    pip install pyelftools   (present in decbench-compile Docker image)
"""

from __future__ import annotations

import argparse
import json
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


# ---------------------------------------------------------------------------
# ELF identification
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Demangling
# ---------------------------------------------------------------------------

def _demangle(raw: str) -> str:
    if not raw.startswith("_Z"):
        return raw
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


# ---------------------------------------------------------------------------
# Short-name derivation
# ---------------------------------------------------------------------------

def _strip_template_args(s: str) -> str:
    """Remove <...> template argument lists using bracket-depth counting."""
    out: list[str] = []
    depth = 0
    for ch in s:
        if ch == '<':
            depth += 1
        elif ch == '>':
            if depth > 0:
                depth -= 1
                continue
            # else: stray '>', shouldn't happen after proper demangling
        if depth == 0:
            out.append(ch)
    return ''.join(out)


def _short_name(demangled: str) -> str:
    """Derive the DecBench-style unqualified short name from a demangled string.

    Strategy:
      1. Strip the return-type prefix if present (space before a qualified name).
      2. Strip the argument list (everything from the first top-level '(').
      3. Remove template parameters.
      4. Take the last '::' component.

    This avoids regex-based approaches that leave artefacts like 'X>'.
    """
    name = demangled.strip()

    # 1. Strip return type: drop leading word(s) if followed by a space and
    #    what looks like a qualified identifier.
    # Only strip if the token before the space looks like a type keyword.
    sp = name.find(' ')
    if sp != -1:
        after = name[sp + 1:].lstrip()
        if after and (after[0].isalpha() or after[0] in ('_', '~', ':')):
            name = after

    # 2. Strip argument list: find first '(' at angle-bracket depth 0.
    #    We must track '<' depth because template args can contain '('.
    depth = 0
    cut = len(name)
    for i, ch in enumerate(name):
        if ch == '<':
            depth += 1
        elif ch == '>':
            if depth > 0:
                depth -= 1
        elif ch == '(' and depth == 0:
            cut = i
            break
    name = name[:cut]

    # 3. Remove template parameters from what remains.
    name = _strip_template_args(name)
    name = name.strip()

    # 4. Take the last '::' component.
    parts = name.split("::")
    short = parts[-1].strip()
    return short if short else name


# ---------------------------------------------------------------------------
# Namespace-based stdlib classification
# ---------------------------------------------------------------------------

# Fully-qualified demangled names starting with any of these prefixes are
# treated as stdlib/system — excluded from the "project" measurement.
_STDLIB_PREFIXES = (
    "std::",
    "__gnu_cxx::",
    "__cxxabiv",
    "__detail::",
    "std::__",
    "__gnu_pbds::",
)


def _is_stdlib_fn(demangled: str) -> bool:
    return any(demangled.startswith(p) for p in _STDLIB_PREFIXES)


# ---------------------------------------------------------------------------
# CMake probe CU filter
# ---------------------------------------------------------------------------

_PROBE_KEYWORDS = frozenset([
    "CMakeFiles", "cmake_install", "CMakeCXXCompilerId",
    "CMakeCCompilerId", "CompilerIdCXX", "CompilerIdC", "feature_tests",
])


def _is_probe_cu(cu_name: str) -> bool:
    return any(kw in cu_name for kw in _PROBE_KEYWORDS)


# ---------------------------------------------------------------------------
# DWARF attribute helpers
# ---------------------------------------------------------------------------

def _attr_str(die, name: str) -> str:
    attr = die.attributes.get(name)
    if attr is None:
        return ""
    v = attr.value
    return v.decode("utf-8", errors="replace") if isinstance(v, bytes) else str(v)


def _attr_val(die, name: str):
    attr = die.attributes.get(name)
    return attr.value if attr else None


def _resolve_linkage_name(die, die_map: dict) -> str:
    for attr in ("DW_AT_linkage_name", "DW_AT_MIPS_linkage_name"):
        v = _attr_str(die, attr)
        if v:
            return v
    for ref_attr in ("DW_AT_specification", "DW_AT_abstract_origin"):
        ref = _attr_val(die, ref_attr)
        if ref is not None:
            ref_die = die_map.get(ref)
            if ref_die is not None:
                r = _resolve_linkage_name(ref_die, die_map)
                if r:
                    return r
    return ""


def _resolve_name(die, die_map: dict) -> str:
    v = _attr_str(die, "DW_AT_name")
    if v:
        return v
    for ref_attr in ("DW_AT_specification", "DW_AT_abstract_origin"):
        ref = _attr_val(die, ref_attr)
        if ref is not None:
            ref_die = die_map.get(ref)
            if ref_die is not None:
                r = _resolve_name(ref_die, die_map)
                if r:
                    return r
    return ""


# ---------------------------------------------------------------------------
# Statistics builder
# ---------------------------------------------------------------------------

def _make_stats(n2a: dict[str, set[int]], a2name: dict[int, str]) -> dict:
    total = len(a2name)
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
                "example_qualified": [a2name[a] for a in sorted(addrs)[:3]],
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


# ---------------------------------------------------------------------------
# Per-ELF measurement
# ---------------------------------------------------------------------------

def measure_elf(elf_path: Path, verbose: bool = False) -> dict:
    # raw: all non-probe subprograms
    raw_n2a: dict[str, set[int]] = defaultdict(set)
    raw_a2name: dict[int, str] = {}
    # project: non-stdlib, non-probe subprograms
    proj_n2a: dict[str, set[int]] = defaultdict(set)
    proj_a2name: dict[int, str] = {}

    cu_stats = {"total": 0, "probe": 0, "stdlib_fns": 0}

    with elf_path.open("rb") as f:
        try:
            elf = ELFFile(f)
        except ELFError as e:
            return {"path": str(elf_path), "error": str(e)}

        if not elf.has_dwarf_info():
            return {"path": str(elf_path), "error": "no DWARF",
                    "raw": _make_stats({}, {}),
                    "project": _make_stats({}, {})}

        dwarf = elf.get_dwarf_info()

        for CU in dwarf.iter_CUs():
            cu_stats["total"] += 1
            top = CU.get_top_DIE()
            cu_name = _attr_str(top, "DW_AT_name")

            if _is_probe_cu(cu_name):
                cu_stats["probe"] += 1
                if verbose:
                    print(f"    [probe] {cu_name}", file=sys.stderr)
                continue

            # Build die offset map for this CU
            die_map: dict[int, object] = {}
            for die in CU.iter_DIEs():
                die_map[die.offset] = die

            for die in CU.iter_DIEs():
                if die.tag != "DW_TAG_subprogram":
                    continue

                # Must have a concrete low_pc
                lp_attr = die.attributes.get("DW_AT_low_pc")
                if lp_attr is None:
                    continue
                low_pc = int(lp_attr.value) if lp_attr.value else 0
                if low_pc == 0:
                    continue

                # Skip abstract instances
                inl = die.attributes.get("DW_AT_inline")
                if inl and inl.value != 0:
                    continue

                # Resolve name
                linkage = _resolve_linkage_name(die, die_map)
                if linkage:
                    demangled = _demangle(linkage)
                else:
                    raw_n = _resolve_name(die, die_map)
                    if not raw_n:
                        continue
                    demangled = _demangle(raw_n) if raw_n.startswith("_Z") else raw_n

                short = _short_name(demangled)
                is_std = _is_stdlib_fn(demangled)

                # Raw set: everything non-probe
                raw_n2a[short].add(low_pc)
                raw_a2name[low_pc] = demangled

                # Project set: exclude stdlib
                if is_std:
                    cu_stats["stdlib_fns"] += 1
                else:
                    proj_n2a[short].add(low_pc)
                    proj_a2name[low_pc] = demangled

    return {
        "path": str(elf_path),
        "cu_stats": cu_stats,
        "raw": _make_stats(raw_n2a, raw_a2name),
        "project": _make_stats(proj_n2a, proj_a2name),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Measure DWARF short-name collisions")
    ap.add_argument("compiled_dir")
    ap.add_argument("--output", "-o", default=None)
    ap.add_argument("--exclude-image", nargs="*", default=[], metavar="NAME")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    compiled = Path(args.compiled_dir)
    if not compiled.is_dir():
        print(f"ERROR: {compiled} is not a directory", file=sys.stderr)
        return 1

    exclude = set(args.exclude_image)
    elf_paths = sorted(
        p for p in compiled.iterdir()
        if p.is_file() and p.name not in exclude and _is_linked_elf(p)
    )

    if not elf_paths:
        print(f"WARNING: No ELF images in {compiled}", file=sys.stderr)
        result = {"compiled_dir": str(compiled), "elf_image_count": 0,
                  "aggregated_raw": {}, "aggregated_project": {}}
    else:
        per_image = []
        for ep in elf_paths:
            if args.verbose:
                print(f"  [{ep.name}]", file=sys.stderr, flush=True)
            per_image.append(measure_elf(ep, args.verbose))

        result = {
            "compiled_dir": str(compiled),
            "exclude_images": list(exclude),
            "elf_images": [str(p) for p in elf_paths],
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
    # Extract target/mode from path for cleaner summary line
    parts = compiled.parts
    try:
        tag = f"{parts[-3]}/{parts[-2]}"
    except IndexError:
        tag = str(compiled)
    print(
        f"SUMMARY [{tag}]"
        f"  ELF={result.get('elf_image_count',0)}"
        f"  raw={r.get('source_function_addresses','?')} addrs @{r.get('collision_rate_pct','?')}"
        f"  project={p.get('source_function_addresses','?')} addrs @{p.get('collision_rate_pct','?')}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
