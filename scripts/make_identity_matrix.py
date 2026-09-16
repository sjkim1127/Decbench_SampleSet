#!/usr/bin/env python3
"""Emit a GitHub Actions matrix for Tier A corpus targets."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tier", default="A")
    ap.add_argument("--expected", type=int)
    args = ap.parse_args()

    rows = []
    with Path(args.csv).open(newline="") as f:
        for row in csv.DictReader(f):
            if row.get("tier") != args.tier:
                continue
            repo = row.get("repo")
            revision = row.get("revision")
            if not repo or not revision:
                continue
            rows.append({"repo": repo, "revision": revision, "rank": int(row.get("rank") or 0)})

    if args.expected is not None and len(rows) != args.expected:
        raise SystemExit(f"expected {args.expected} tier-{args.tier} targets, got {len(rows)}")

    payload = {"include": rows}
    Path(args.out).write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    print(json.dumps({"tier": args.tier, "count": len(rows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
