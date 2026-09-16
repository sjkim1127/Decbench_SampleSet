#!/usr/bin/env python3
"""Characterize C++ function identity and source feature signals for one qualified repo.

This stage is deliberately diagnostic. It rebuilds the pinned revision under the
same generic O0/GCC policy as the corpus funnel, then inspects project-owned DWARF
subprograms. It does not claim that heuristic source feature counts are semantic
ground truth.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from elftools.elf.elffile import ELFFile

import corpus_pipeline as cp
import probe_linux as probe

SOURCE_EXTS = {".c", ".cc", ".cpp", ".cxx", ".c++", ".C", ".h", ".hh", ".hpp", ".hxx", ".ipp", ".tpp"}
EXCLUDED_PARTS = {
    ".git", "_decbench_build", "_deps", "third_party", "third-party", "3rdparty",
    "vendor", "vendors", "external", "extern", "deps", "subprojects",
    "vcpkg_installed", "node_modules", "conan", ".cache",
}
TEST_PART_RE = re.compile(r"(?:^|[/_.-])(?:tests?|bench(?:mark)?s?|examples?|samples?)(?:[/_.-]|$)", re.I)

FEATURE_PATTERNS: dict[str, re.Pattern[str]] = {
    "templates": re.compile(r"\btemplate\s*<"),
    "inheritance": re.compile(r"\b(?:class|struct)\s+[A-Za-z_]\w*[^;{\n]{0,180}:\s*(?:public|protected|private)?\s*[A-Za-z_:]"),
    "virtual_dispatch": re.compile(r"\b(?:virtual|override)\b"),
    "exceptions": re.compile(r"\b(?:try|catch|throw)\b"),
    "rtti": re.compile(r"\b(?:dynamic_cast|typeid)\s*[<(]"),
    "lambdas": re.compile(r"\[[^\]\n]{0,100}\]\s*(?:\([^;\n{}]*\))?\s*(?:mutable\s*)?(?:->[^{}\n]+)?\s*\{"),
    "operator_overload": re.compile(r"\boperator\s*(?:\(\)|\[\]|new\b|delete\b|[+\-*/%<>=!&|^~]+)"),
    "smart_pointers": re.compile(r"\b(?:std::)?(?:unique_ptr|shared_ptr|weak_ptr)\s*<"),
    "constexpr": re.compile(r"\bconstexpr\b"),
    "concepts_requires": re.compile(r"\b(?:concept\s+[A-Za-z_]\w*|requires\b)"),
    "coroutines": re.compile(r"\b(?:co_await|co_yield|co_return)\b"),
}

SCOPE_TAGS = {"DW_TAG_namespace", "DW_TAG_class_type", "DW_TAG_structure_type", "DW_TAG_union_type"}


def b2s(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def clone_revision(repo: str, revision: str, root: Path) -> dict[str, Any]:
    env = os.environ.copy()
    commands = [
        ["git", "init", str(root)],
        ["git", "-C", str(root), "remote", "add", "origin", f"https://github.com/{repo}.git"],
        ["git", "-C", str(root), "fetch", "--depth", "1", "origin", revision],
        ["git", "-C", str(root), "checkout", "--detach", "FETCH_HEAD"],
        ["git", "-C", str(root), "submodule", "update", "--init", "--recursive", "--depth", "1"],
    ]
    steps: list[dict[str, Any]] = []
    for command in commands:
        r = cp.run(command, root.parent, env, 180)
        steps.append({"command": command, **r})
        if r["returncode"] != 0:
            return {"ok": False, "steps": steps}
    actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    return {"ok": actual == revision, "actual_revision": actual, "steps": steps}


def is_project_path(path: Path | None, root: Path) -> bool:
    if path is None:
        return False
    try:
        resolved = path.resolve(strict=False)
        rel = resolved.relative_to(root.resolve(strict=False))
    except (ValueError, OSError):
        return False
    return not any(part.lower() in EXCLUDED_PARTS for part in rel.parts)


def die_attr_target(die: Any, attr_name: str) -> Any | None:
    if attr_name not in die.attributes:
        return None
    try:
        return die.get_DIE_from_attribute(attr_name)
    except Exception:
        return None


def resolve_attr(die: Any, names: Iterable[str], depth: int = 0) -> Any | None:
    if depth > 5:
        return None
    for name in names:
        attr = die.attributes.get(name)
        if attr is not None:
            return attr.value
    for ref_name in ("DW_AT_specification", "DW_AT_abstract_origin"):
        target = die_attr_target(die, ref_name)
        if target is not None:
            value = resolve_attr(target, names, depth + 1)
            if value is not None:
                return value
    return None


def walk_scopes(die: Any, scope: tuple[str, ...], scope_by_offset: dict[int, tuple[str, ...]]) -> None:
    current = scope
    if die.tag in SCOPE_TAGS:
        name = b2s(resolve_attr(die, ("DW_AT_name",)))
        if name:
            current = (*scope, name)
    scope_by_offset[die.offset] = current
    try:
        children = die.iter_children()
    except Exception:
        return
    for child in children:
        walk_scopes(child, current, scope_by_offset)


def decl_path(die: Any, cu: Any, dwarf: Any, comp_dir: Path | None) -> Path | None:
    raw_index = resolve_attr(die, ("DW_AT_decl_file",))
    if raw_index is None:
        return None
    try:
        idx = int(raw_index)
        lp = dwarf.line_program_for_CU(cu)
        if lp is None:
            return None
        entries = lp["file_entry"]
        entry = entries[idx - 1] if idx > 0 and idx - 1 < len(entries) else entries[idx] if idx < len(entries) else None
        if entry is None:
            return None
        name = Path(b2s(entry.name) or "")
        if name.is_absolute():
            return name
        dir_index = int(getattr(entry, "dir_index", 0) or 0)
        include_dirs = lp["include_directory"]
        base: Path | None = None
        if dir_index > 0 and dir_index - 1 < len(include_dirs):
            base = Path(b2s(include_dirs[dir_index - 1]) or "")
            if not base.is_absolute() and comp_dir is not None:
                base = comp_dir / base
        elif comp_dir is not None:
            base = comp_dir
        return (base / name) if base is not None else name
    except Exception:
        return None


def binary_role(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    if TEST_PART_RE.search(rel):
        return "test-like"
    name = path.name
    if ".so" in name or name.endswith((".a", ".dylib")):
        return "library"
    return "executable"


def inspect_binary(path: Path, root: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as f:
            elf = ELFFile(f)
            if not elf.has_dwarf_info():
                return {"error": "no_dwarf"}
            dwarf = elf.get_dwarf_info()
            scope_by_offset: dict[int, tuple[str, ...]] = {}
            cus = list(dwarf.iter_CUs())
            for cu in cus:
                walk_scopes(cu.get_top_DIE(), (), scope_by_offset)

            records_by_address: dict[int, dict[str, Any]] = {}
            unaddressed_project = 0
            concrete_total = 0
            project_decl_unknown = 0
            spec_or_origin = 0

            for cu in cus:
                top = cu.get_top_DIE()
                comp_dir_s = b2s(resolve_attr(top, ("DW_AT_comp_dir",)))
                comp_dir = Path(comp_dir_s) if comp_dir_s else None
                for die in cu.iter_DIEs():
                    if die.tag != "DW_TAG_subprogram":
                        continue
                    if die.attributes.get("DW_AT_declaration") is not None:
                        try:
                            if bool(die.attributes["DW_AT_declaration"].value):
                                continue
                        except Exception:
                            pass
                    has_code = "DW_AT_low_pc" in die.attributes or "DW_AT_ranges" in die.attributes
                    if not has_code:
                        continue
                    concrete_total += 1
                    if "DW_AT_specification" in die.attributes or "DW_AT_abstract_origin" in die.attributes:
                        spec_or_origin += 1

                    name = b2s(resolve_attr(die, ("DW_AT_name",)))
                    linkage = b2s(resolve_attr(die, ("DW_AT_linkage_name", "DW_AT_MIPS_linkage_name")))
                    path_decl = decl_path(die, cu, dwarf, comp_dir)
                    owned = is_project_path(path_decl, root)
                    if path_decl is None:
                        project_decl_unknown += 1
                    if not owned:
                        continue

                    scope = scope_by_offset.get(die.offset, ())
                    if not scope:
                        for ref_name in ("DW_AT_specification", "DW_AT_abstract_origin"):
                            target = die_attr_target(die, ref_name)
                            if target is not None and scope_by_offset.get(target.offset):
                                scope = scope_by_offset[target.offset]
                                break
                    qualified = "::".join((*scope, name)) if scope and name else name
                    line_v = resolve_attr(die, ("DW_AT_decl_line",))
                    try:
                        line = int(line_v) if line_v is not None else None
                    except Exception:
                        line = None

                    if "DW_AT_low_pc" not in die.attributes:
                        unaddressed_project += 1
                        continue
                    try:
                        address = int(die.attributes["DW_AT_low_pc"].value)
                    except Exception:
                        unaddressed_project += 1
                        continue

                    rec = {
                        "address": address,
                        "name": name,
                        "qualified_name": qualified,
                        "linkage_name": linkage,
                        "decl_file": str(path_decl) if path_decl else None,
                        "decl_line": line,
                        "scope_depth": len(scope),
                    }
                    old = records_by_address.get(address)
                    if old is None:
                        records_by_address[address] = rec
                    else:
                        def richness(x: dict[str, Any]) -> tuple[int, int, int]:
                            return (bool(x.get("linkage_name")), bool(x.get("qualified_name")), x.get("scope_depth", 0))
                        if richness(rec) > richness(old):
                            records_by_address[address] = rec

            records = list(records_by_address.values())
            named = [r for r in records if r["name"]]
            linkage = [r for r in records if r["linkage_name"]]
            qualified = [r for r in records if r["qualified_name"]]

            def collision_stats(key: str, subset: list[dict[str, Any]] | None = None) -> dict[str, Any]:
                rows = subset if subset is not None else records
                groups: dict[str, set[int]] = defaultdict(set)
                for rec in rows:
                    value = rec.get(key)
                    if value:
                        groups[str(value)].add(int(rec["address"]))
                colliding = {k: v for k, v in groups.items() if len(v) > 1}
                exposed = sum(len(v) for v in colliding.values())
                denominator = sum(len(v) for v in groups.values())
                top = sorted(colliding.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:20]
                return {
                    "unique_keys": len(groups),
                    "colliding_keys": len(colliding),
                    "exposed_functions": exposed,
                    "denominator": denominator,
                    "exposure_pct": round(100.0 * exposed / denominator, 3) if denominator else 0.0,
                    "top_collisions": [{"key": k, "functions": len(v)} for k, v in top],
                }

            project_files = sorted({r["decl_file"] for r in records if r["decl_file"]})
            return {
                "path": str(path.relative_to(root)) if root in path.parents else str(path),
                "size_bytes": path.stat().st_size,
                "role": binary_role(path, root),
                "concrete_subprogram_dies": concrete_total,
                "project_addressed_functions": len(records),
                "project_unaddressed_functions": unaddressed_project,
                "unknown_decl_file_dies": project_decl_unknown,
                "spec_or_origin_dies": spec_or_origin,
                "project_translation_units": len(project_files),
                "linkage_name_coverage_pct": round(100.0 * len(linkage) / len(records), 3) if records else 0.0,
                "qualified_name_coverage_pct": round(100.0 * len(qualified) / len(records), 3) if records else 0.0,
                "short_name": collision_stats("name", named),
                "qualified_name": collision_stats("qualified_name", qualified),
                "linkage_name": collision_stats("linkage_name", linkage),
                "project_file_sample": project_files[:20],
            }
    except Exception as exc:
        return {"path": str(path), "error": f"{type(exc).__name__}: {exc}"}


def source_feature_signals(root: Path, max_bytes: int = 40 * 1024 * 1024) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    scanned_files = 0
    scanned_bytes = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in SOURCE_EXTS:
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        if any(part.lower() in EXCLUDED_PARTS for part in rel.parts):
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > 2 * 1024 * 1024 or scanned_bytes + size > max_bytes:
            continue
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        scanned_files += 1
        scanned_bytes += size
        for name, pattern in FEATURE_PATTERNS.items():
            counts[name] += len(pattern.findall(text))
    return {
        "files_scanned": scanned_files,
        "bytes_scanned": scanned_bytes,
        "features_present": sum(1 for name in FEATURE_PATTERNS if counts[name] > 0),
        "signals": {name: counts[name] for name in FEATURE_PATTERNS},
    }


def candidate_elfs(search_root: Path) -> list[Path]:
    linked: list[Path] = []
    for path in search_root.rglob("*"):
        if not path.is_file() or path.is_symlink() or probe.is_toolchain_probe(path, search_root):
            continue
        if ".git" in path.parts:
            continue
        try:
            if path.stat().st_size > 400 * 1024 * 1024:
                continue
        except OSError:
            continue
        if cp.is_elf_linked(path) and cp.dwarf_present(path):
            linked.append(path)

    def key(p: Path) -> tuple[int, int]:
        role = binary_role(p, search_root)
        non_test = 0 if role == "test-like" else 1
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        return (non_test, size)

    linked.sort(key=key, reverse=True)
    non_test = [p for p in linked if binary_role(p, search_root) != "test-like"][:16]
    test_like = [p for p in linked if binary_role(p, search_root) == "test-like"][:4]
    return non_test + test_like


def choose_binary(reports: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [r for r in reports if "error" not in r and r.get("project_addressed_functions", 0) > 0]
    if not valid:
        return None
    role_rank = {"library": 2, "executable": 1, "test-like": 0}
    return max(
        valid,
        key=lambda r: (
            role_rank.get(r.get("role", ""), 0),
            int(r.get("project_addressed_functions", 0)),
            int(r.get("project_translation_units", 0)),
            int(r.get("size_bytes", 0)),
        ),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "repo": args.repo,
        "requested_revision": args.revision,
        "characterizer_version": 1,
        "status": "FAIL",
    }

    with tempfile.TemporaryDirectory(prefix="decbench-cpp-id-") as td:
        root = Path(td) / "src"
        clone = clone_revision(args.repo, args.revision, root)
        result["clone"] = clone
        if not clone.get("ok"):
            result["failure_stage"] = "clone"
            out.write_text(json.dumps(result, indent=2) + "\n")
            return 0

        system = cp.detect_build_system(root)
        result["build_system"] = system
        if not system:
            result["failure_stage"] = "build_system"
            out.write_text(json.dumps(result, indent=2) + "\n")
            return 0

        ok, build_steps, search_root = probe.build(root, system)
        result["build_steps"] = build_steps
        if not ok:
            result["failure_stage"] = "build"
            out.write_text(json.dumps(result, indent=2) + "\n")
            return 0

        root_for_artifacts = search_root if search_root.exists() else root
        elfs = candidate_elfs(root_for_artifacts)
        result["dwarf_elf_candidates"] = len(elfs)
        reports = [inspect_binary(path, root) for path in elfs]
        selected = choose_binary(reports)
        result["binary_reports"] = reports
        result["selected_binary"] = selected
        result["source_features"] = source_feature_signals(root)
        result["ii_count"] = sum(
            1 for p in root_for_artifacts.rglob("*.ii")
            if p.is_file() and not probe.is_toolchain_probe(p, root_for_artifacts)
        )

        if selected is None:
            result["failure_stage"] = "identity_no_project_binary"
        else:
            result["status"] = "PASS"
            result["failure_stage"] = None

    out.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
