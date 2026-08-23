#!/usr/bin/env python3
"""Compare binary hashes across repeated clean qualification builds."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path, help="directory containing downloaded replicate artifacts")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    reports = sorted(args.root.rglob("dwarf-audit.json"))
    by_binary: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    replicates = set()
    for report in reports:
        data = json.loads(report.read_text(encoding="utf-8"))
        rep = report.parts[-3] if len(report.parts) >= 3 else report.parent.name
        replicates.add(rep)
        for binary in data.get("binaries", []):
            path = binary.get("path", "")
            sha = binary.get("sha256")
            if sha:
                by_binary[path][rep].add(sha)

    comparisons = []
    all_repro = True
    for path, per_rep in sorted(by_binary.items()):
        hashes = sorted({h for hs in per_rep.values() for h in hs})
        reproducible = len(hashes) == 1 and len(per_rep) == len(replicates)
        all_repro &= reproducible
        comparisons.append({
            "binary": path,
            "reproducible": reproducible,
            "unique_hashes": hashes,
            "replicates_present": sorted(per_rep),
        })

    out = {
        "replicate_reports": len(reports),
        "replicates": sorted(replicates),
        "binary_keys": len(comparisons),
        "all_binary_hashes_reproducible": all_repro if comparisons else False,
        "comparisons": comparisons,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")

    md = args.output.with_suffix(".md")
    lines = [
        "# Clean-build reproducibility",
        "",
        f"Replicates found: **{len(replicates)}**",
        f"All binary hashes reproducible: **{'YES' if out['all_binary_hashes_reproducible'] else 'NO'}**",
        "",
        "| Binary | Reproducible | Unique SHA-256 count |",
        "| --- | --- | ---: |",
    ]
    for row in comparisons:
        lines.append(f"| `{row['binary']}` | {'YES' if row['reproducible'] else 'NO'} | {len(row['unique_hashes'])} |")
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(md.read_text(encoding="utf-8"))
    # Nondeterminism is a qualification result, not an infrastructure failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
