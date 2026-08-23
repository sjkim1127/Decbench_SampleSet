#!/usr/bin/env python3
"""Render compile/DWARF/ownership/Joern evidence into a compact handoff."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--replicate", required=True)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--dwarf", type=Path, required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--joern", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    compile_report = load(args.results / "compile_report.json") or []
    dwarf = load(args.dwarf) or {}
    source = load(args.source) or {}
    joern = load(args.joern) or {}

    rows = []
    for row in sorted(compile_report, key=lambda r: r.get("opt", "")):
        rows.append(
            f"| {row.get('opt','?')} | {'PASS' if row.get('ok') else 'FAIL'} | "
            f"{row.get('linked_binaries',0)} | {row.get('i_files',0)} | {row.get('seconds',0)} |"
        )

    binaries = dwarf.get("binaries", [])
    hashes = sorted({b.get("sha256") for b in binaries if b.get("sha256")})
    source_rows = []
    per_opt = source.get("per_optimization", {})
    survival = source.get("optimization_survival", {})
    for opt in ("O0", "O2-noinline", "O2"):
        data = per_opt.get(opt, {})
        surv = survival.get(opt, {})
        source_rows.append(
            f"| {opt} | {data.get('project_owned_function_records', 0)} | "
            f"{data.get('unique_short_names', 0)} | {surv.get('survival_rate_vs_O0', 0):.2%} |"
        )

    lines = [
        f"# DecBench C++ qualification — {args.target}",
        "",
        f"Replicate: **{args.replicate}**",
        "",
        "## Compile path",
        "",
        "| Optimization | Build | linked images | `.ii` files | seconds |",
        "| --- | --- | ---: | ---: | ---: |",
        *rows,
        "",
        "## DWARF / identity audit",
        "",
        f"- Linked images audited: **{dwarf.get('binary_count', 0)}**",
        f"- Named `DW_TAG_subprogram` records: **{dwarf.get('named_subprogram_records', 0)}**",
        f"- Short-name collision excess records: **{dwarf.get('short_name_collision_excess_records', 0)}**",
        f"- Aggregate short-name collision rate: **{dwarf.get('aggregate_short_name_collision_rate', 0):.2%}**",
        f"- Distinct image SHA-256 values: **{len(hashes)}**",
        "",
        "## Project-owned function / optimization survival",
        "",
        "| Optimization | project-owned DWARF records | unique short names | identity survival vs O0 |",
        "| --- | ---: | ---: | ---: |",
        *source_rows,
        "",
        "The ownership audit uses the captured `.ii` translation-unit stems plus DecBench's own DWARF helpers, so bundled/toolchain functions are not intentionally counted as project source.",
        "",
        "## Joern / source CFG qualification",
        "",
        f"- `.ii` files checked: **{joern.get('ii_files', 0)}**",
        f"- Parse success: **{joern.get('parsed_files', 0)}/{joern.get('ii_files', 0)} ({joern.get('parse_rate', 0):.2%})**",
        f"- Non-empty parses: **{joern.get('nonempty_files', 0)}/{joern.get('ii_files', 0)} ({joern.get('nonempty_rate', 0):.2%})**",
        f"- Functions seen by Joern: **{joern.get('functions_seen', 0)}**",
        f"- Unique Joern short names: **{joern.get('unique_joern_short_names', 0)}**",
        f"- Cross-TU duplicate short names: **{joern.get('cross_tu_duplicate_short_names', 0)}**",
        "",
        "## Interpretation",
        "",
        "This report separates build success, ground-truth availability, project-source attribution, optimization survival, short-name collision pressure, and Joern parseability. A green upstream build alone is not treated as sufficient qualification for DecBench corpus inclusion.",
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(args.output.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
