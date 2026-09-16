#!/usr/bin/env python3
"""Classify completed C++ corpus probes into actionable DecBench tiers.

Tier A: linked project ELF + DWARF + saved preprocessed C++ (.ii).
Tier B: linked project ELF + DWARF, but .ii needs regeneration/replay.
Tier C: clone/configure/build reached the project but needs a small build adapter.
Tier D: unsuitable/failed before producing a usable debug binary.

The final shortlist prefers A, then B, and ranks by approximate DWARF function
coverage plus number of usable debug images. Tier C is reported but never used
to fill the final 50 because it has not actually produced a qualified binary.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def artifact_score(row: dict[str, Any]) -> float:
    a = row.get("artifacts") or {}
    funcs = int(a.get("dwarf_subprogram_count_sample") or 0)
    bins = int(a.get("dwarf_elf_count") or 0)
    ii = int(a.get("ii_count") or 0)
    return min(funcs, 5000) + min(bins, 30) * 30 + min(ii, 200) * 5


def classify(row: dict[str, Any]) -> tuple[str, str]:
    a = row.get("artifacts") or {}
    linked = int(a.get("linked_elf_count") or 0)
    dwarf = int(a.get("dwarf_elf_count") or 0)
    ii = int(a.get("ii_count") or 0)
    if linked > 0 and dwarf > 0 and ii > 0:
        return "A", "oracle-ready: ELF + DWARF + .ii"
    if linked > 0 and dwarf > 0:
        return "B", "build+DWARF ready; regenerate .ii from compile commands"

    clone_ok = int((row.get("clone") or {}).get("returncode", 1)) == 0
    stage = row.get("failure_stage")
    if clone_ok and stage in {"build", "artifact_oracle"}:
        return "C", f"adapter candidate ({stage})"
    return "D", f"rejected ({stage or 'unknown'})"


def load_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for p in sorted(root.rglob("*.json")):
        try:
            row = json.loads(p.read_text())
        except Exception:
            continue
        if not isinstance(row, dict) or "repo" not in row:
            continue
        repo = str(row["repo"])
        if repo in seen:
            continue
        seen.add(repo)
        tier, reason = classify(row)
        row["tier"] = tier
        row["tier_reason"] = reason
        row["selection_score"] = artifact_score(row)
        rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probes", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = load_rows(Path(args.probes))
    rows.sort(key=lambda r: (r["tier"], -r["selection_score"], r["repo"].lower()))

    tier_a = [r for r in rows if r["tier"] == "A"]
    tier_b = [r for r in rows if r["tier"] == "B"]
    tier_c = [r for r in rows if r["tier"] == "C"]
    tier_d = [r for r in rows if r["tier"] == "D"]
    final = (tier_a + tier_b)[: args.limit]

    (out / "all-probes-classified.json").write_text(json.dumps(rows, indent=2) + "\n")
    (out / "tier-a-oracle-ready.json").write_text(json.dumps(tier_a, indent=2) + "\n")
    (out / "tier-b-build-dwarf.json").write_text(json.dumps(tier_b, indent=2) + "\n")
    (out / "tier-c-adapter.json").write_text(json.dumps(tier_c, indent=2) + "\n")
    (out / "final-50.json").write_text(json.dumps(final, indent=2) + "\n")

    fields = ["rank", "repo", "tier", "selection_score", "linked_elf", "dwarf_elf", "ii", "dwarf_subprogram_sample", "revision", "build_system", "reason"]
    with (out / "final-50.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, r in enumerate(final, 1):
            a = r.get("artifacts") or {}
            w.writerow({
                "rank": i,
                "repo": r["repo"],
                "tier": r["tier"],
                "selection_score": r["selection_score"],
                "linked_elf": a.get("linked_elf_count", 0),
                "dwarf_elf": a.get("dwarf_elf_count", 0),
                "ii": a.get("ii_count", 0),
                "dwarf_subprogram_sample": a.get("dwarf_subprogram_count_sample", 0),
                "revision": r.get("revision"),
                "build_system": r.get("build_system"),
                "reason": r["tier_reason"],
            })

    summary = {
        "attempted_available": len(rows),
        "tier_a_oracle_ready": len(tier_a),
        "tier_b_build_dwarf": len(tier_b),
        "tier_c_adapter": len(tier_c),
        "tier_d_rejected": len(tier_d),
        "build_qualified_a_plus_b": len(tier_a) + len(tier_b),
        "final_selected": len(final),
        "final_repos": [r["repo"] for r in final],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    lines = [
        "# DecBench C++ corpus funnel — build qualification summary",
        "",
        f"- completed probe artifacts available: **{len(rows)}**",
        f"- Tier A (ELF + DWARF + `.ii`): **{len(tier_a)}**",
        f"- Tier B (ELF + DWARF; `.ii` replay needed): **{len(tier_b)}**",
        f"- Tier C (small build adapter needed): **{len(tier_c)}**",
        f"- Tier D (rejected): **{len(tier_d)}**",
        f"- actual build-qualified (A+B): **{len(tier_a)+len(tier_b)}**",
        f"- selected: **{len(final)}**",
        "",
        "## Selected build-qualified targets",
        "",
        "| # | repository | tier | DWARF ELF | `.ii` | sampled DWARF subprograms |",
        "|---:|---|:---:|---:|---:|---:|",
    ]
    for i, r in enumerate(final, 1):
        a = r.get("artifacts") or {}
        lines.append(
            f"| {i} | `{r['repo']}` | {r['tier']} | {a.get('dwarf_elf_count',0)} | {a.get('ii_count',0)} | {a.get('dwarf_subprogram_count_sample',0)} |"
        )
    lines += ["", "## Tier C — adapter candidates", ""]
    for r in tier_c[:30]:
        lines.append(f"- `{r['repo']}` — {r['tier_reason']}")
    (out / "summary.md").write_text("\n".join(lines) + "\n")

    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
