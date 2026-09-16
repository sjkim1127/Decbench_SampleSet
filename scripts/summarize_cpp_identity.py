#!/usr/bin/env python3
"""Aggregate Tier A C++ identity characterization results."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def inum(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def row_from_result(data: dict[str, Any]) -> dict[str, Any]:
    selected = data.get("selected_binary") or {}
    features = data.get("source_features") or {}
    signals = features.get("signals") or {}
    short = selected.get("short_name") or {}
    qualified = selected.get("qualified_name") or {}
    linkage = selected.get("linkage_name") or {}
    role = selected.get("role")
    funcs = inum(selected.get("project_addressed_functions"))
    tus = inum(selected.get("project_translation_units"))
    linkage_cov = fnum(selected.get("linkage_name_coverage_pct"))
    short_collision = fnum(short.get("exposure_pct"))
    qualified_collision = fnum(qualified.get("exposure_pct"))
    linkage_collision = fnum(linkage.get("exposure_pct"))
    feature_count = inum(features.get("features_present"))

    if data.get("status") != "PASS":
        review_class = "failed"
    elif role == "test-like":
        review_class = "test-only-or-test-preferred"
    elif funcs < 20:
        review_class = "too-few-functions"
    elif tus < 2:
        review_class = "single-tu"
    elif linkage_cov < 25:
        review_class = "low-linkage-coverage"
    else:
        review_class = "deep-review-ready"

    if short_collision < 10:
        collision_band = "low"
    elif short_collision < 30:
        collision_band = "medium"
    else:
        collision_band = "high"

    return {
        "repo": data.get("repo"),
        "status": data.get("status"),
        "revision": data.get("requested_revision"),
        "build_system": data.get("build_system"),
        "selected_binary": selected.get("path"),
        "binary_role": role,
        "project_functions": funcs,
        "project_tus": tus,
        "ii_count": inum(data.get("ii_count")),
        "linkage_name_coverage_pct": round(linkage_cov, 3),
        "qualified_name_coverage_pct": round(fnum(selected.get("qualified_name_coverage_pct")), 3),
        "short_name_collision_pct": round(short_collision, 3),
        "qualified_name_collision_pct": round(qualified_collision, 3),
        "linkage_name_collision_pct": round(linkage_collision, 3),
        "source_features_present": feature_count,
        "templates": inum(signals.get("templates")),
        "inheritance": inum(signals.get("inheritance")),
        "virtual_dispatch": inum(signals.get("virtual_dispatch")),
        "exceptions": inum(signals.get("exceptions")),
        "rtti": inum(signals.get("rtti")),
        "lambdas": inum(signals.get("lambdas")),
        "operator_overload": inum(signals.get("operator_overload")),
        "smart_pointers": inum(signals.get("smart_pointers")),
        "constexpr": inum(signals.get("constexpr")),
        "concepts_requires": inum(signals.get("concepts_requires")),
        "coroutines": inum(signals.get("coroutines")),
        "collision_band": collision_band,
        "review_class": review_class,
        "failure_stage": data.get("failure_stage"),
    }


def load_expected(path: Path) -> list[str]:
    expected: list[str] = []
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            if row.get("tier") == "A" and row.get("repo"):
                expected.append(row["repo"])
    return expected


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--source-csv", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    src = Path(args.input)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    expected = load_expected(Path(args.source_csv))

    raw: dict[str, dict[str, Any]] = {}
    for path in sorted(src.glob("*.json")):
        try:
            data = json.loads(path.read_text())
        except Exception:
            continue
        repo = data.get("repo")
        if repo:
            raw[repo] = data

    rows = [row_from_result(raw[repo]) for repo in expected if repo in raw]
    missing = [repo for repo in expected if repo not in raw]
    rows.sort(key=lambda r: (r["review_class"] != "deep-review-ready", r["binary_role"] == "test-like", -r["source_features_present"], -r["project_functions"], r["repo"] or ""))

    fieldnames = list(rows[0].keys()) if rows else [
        "repo", "status", "revision", "build_system", "selected_binary", "binary_role",
        "project_functions", "project_tus", "ii_count", "linkage_name_coverage_pct",
        "qualified_name_coverage_pct", "short_name_collision_pct",
        "qualified_name_collision_pct", "linkage_name_collision_pct",
        "source_features_present", "collision_band", "review_class", "failure_stage",
    ]
    with (out / "identity-summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    payload = {
        "expected_tier_a": len(expected),
        "results_received": len(rows),
        "missing": missing,
        "pass": sum(r["status"] == "PASS" for r in rows),
        "deep_review_ready": sum(r["review_class"] == "deep-review-ready" for r in rows),
        "test_like_selected": sum(r["binary_role"] == "test-like" for r in rows),
        "collision_bands": {
            band: sum(r["collision_band"] == band and r["status"] == "PASS" for r in rows)
            for band in ("low", "medium", "high")
        },
        "rows": rows,
    }
    (out / "identity-summary.json").write_text(json.dumps(payload, indent=2) + "\n")

    buckets = {
        "deep_review_ready": [r["repo"] for r in rows if r["review_class"] == "deep-review-ready"],
        "collision_low": [r["repo"] for r in rows if r["status"] == "PASS" and r["collision_band"] == "low"],
        "collision_medium": [r["repo"] for r in rows if r["status"] == "PASS" and r["collision_band"] == "medium"],
        "collision_high": [r["repo"] for r in rows if r["status"] == "PASS" and r["collision_band"] == "high"],
        "test_like_selected": [r["repo"] for r in rows if r["binary_role"] == "test-like"],
        "low_linkage_coverage": [r["repo"] for r in rows if r["status"] == "PASS" and fnum(r["linkage_name_coverage_pct"]) < 25],
        "too_few_functions": [r["repo"] for r in rows if r["review_class"] == "too-few-functions"],
    }
    (out / "review-buckets.json").write_text(json.dumps(buckets, indent=2) + "\n")

    top_collision = sorted([r for r in rows if r["status"] == "PASS"], key=lambda r: (-fnum(r["short_name_collision_pct"]), -(r["project_functions"] or 0)))[:10]
    top_features = sorted([r for r in rows if r["status"] == "PASS"], key=lambda r: (-(r["source_features_present"] or 0), -(r["project_functions"] or 0)))[:10]

    md = [
        "# C++ identity characterization", "",
        "This report is a diagnostic follow-up to the Tier A corpus funnel. It does not",
        "promote targets into the benchmark by itself.", "",
        "## Coverage", "",
        f"- Expected Tier A repositories: **{len(expected)}**",
        f"- Result records received: **{len(rows)}**",
        f"- Characterization PASS: **{sum(r['status'] == 'PASS' for r in rows)}**",
        f"- Deep-review-ready by mechanical gates: **{sum(r['review_class'] == 'deep-review-ready' for r in rows)}**",
        f"- Selected artifact is test-like: **{sum(r['binary_role'] == 'test-like' for r in rows)}**",
        f"- Missing result records: **{len(missing)}**", "",
        "Mechanical `deep-review-ready` means: characterization PASS, selected binary is",
        "not test-like, at least 20 project-owned addressed functions, at least 2 project",
        "translation units, and at least 25% `DW_AT_linkage_name` coverage. It is a review",
        "gate, not a benchmark-quality score.", "",
        "## Short-name collision bands", "",
        f"- low (<10%): **{payload['collision_bands']['low']}**",
        f"- medium (10-30%): **{payload['collision_bands']['medium']}**",
        f"- high (>=30%): **{payload['collision_bands']['high']}**", "",
        "## Highest short-name collision exposure", "",
        "| Repository | Functions | TUs | Linkage coverage | Short-name collision |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in top_collision:
        md.append(f"| `{r['repo']}` | {r['project_functions']} | {r['project_tus']} | {r['linkage_name_coverage_pct']:.1f}% | {r['short_name_collision_pct']:.1f}% |")
    md += ["", "## Broadest source feature signals", "", "| Repository | Feature categories | Functions | Short-name collision |", "|---|---:|---:|---:|"]
    for r in top_features:
        md.append(f"| `{r['repo']}` | {r['source_features_present']} | {r['project_functions']} | {r['short_name_collision_pct']:.1f}% |")
    if missing:
        md += ["", "## Missing", "", *[f"- `{repo}`" for repo in missing]]
    md += [
        "", "See `identity-summary.csv` for the full table and `review-buckets.json` for",
        "mechanical follow-up groups.", "", "### Method caveats", "",
        "- Project ownership is conservatively inferred from DWARF declaration paths under",
        "  the checked-out repository while excluding common vendored/build directories.",
        "- The representative binary is selected from real DWARF-bearing project artifacts;",
        "  non-test artifacts are preferred over test/example binaries.",
        "- Source feature counts are regex-based signals, not semantic ground truth.",
        "- Collision exposure is computed over distinct project-owned function addresses in",
        "  the selected binary and is intended to diagnose the current short-name identity model.",
    ]
    (out / "README.md").write_text("\n".join(md) + "\n")
    print(json.dumps({k: payload[k] for k in ("expected_tier_a", "results_received", "pass", "deep_review_ready")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
