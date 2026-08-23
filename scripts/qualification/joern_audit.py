#!/usr/bin/env python3
"""Measure DecBench/pyjoern parse coverage over captured C++ .ii files."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def _parse_one(args: tuple[str, str]) -> dict:
    source, decbench_root = args
    sys.path.insert(0, decbench_root)
    from decbench.utils.cfg import extract_cfgs_from_source

    path = Path(source)
    started = time.time()
    try:
        cfgs = extract_cfgs_from_source(path, raise_on_error=True) or {}
        names = sorted(cfgs)
        return {
            "file": source,
            "ok": True,
            "functions": len(names),
            "function_names": names,
            "seconds": round(time.time() - started, 3),
        }
    except Exception as exc:
        return {
            "file": source,
            "ok": False,
            "functions": 0,
            "function_names": [],
            "seconds": round(time.time() - started, 3),
            "error": f"{type(exc).__name__}: {exc}"[:2000],
        }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--decbench-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=max(1, min(4, os.cpu_count() or 1)))
    ap.add_argument("--max-files", type=int, default=0, help="0 means all .ii files")
    args = ap.parse_args()

    root = args.root.resolve()
    decbench_root = args.decbench_root.resolve()
    files = sorted(root.rglob("*.ii"))
    if args.max_files > 0:
        files = files[: args.max_files]

    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(_parse_one, (str(p), str(decbench_root))): p
            for p in files
        }
        for fut in as_completed(futs):
            result = fut.result()
            result["file"] = str(Path(result["file"]).relative_to(root))
            results.append(result)
            status = "OK" if result["ok"] else "FAIL"
            print(f"[{status}] {result['file']} funcs={result['functions']} {result['seconds']}s", flush=True)

    results.sort(key=lambda r: r["file"])
    parsed = sum(1 for r in results if r["ok"])
    nonempty = sum(1 for r in results if r["ok"] and r["functions"] > 0)
    name_counts = Counter(
        name
        for result in results
        if result["ok"]
        for name in result.get("function_names", [])
    )
    duplicate_names = {name: count for name, count in name_counts.items() if count > 1}
    out = {
        "root": str(root),
        "ii_files": len(files),
        "parsed_files": parsed,
        "nonempty_files": nonempty,
        "parse_rate": round(parsed / len(files), 6) if files else 0.0,
        "nonempty_rate": round(nonempty / len(files), 6) if files else 0.0,
        "functions_seen": sum(r["functions"] for r in results),
        "unique_joern_short_names": len(name_counts),
        "cross_tu_duplicate_short_names": len(duplicate_names),
        "top_cross_tu_duplicate_names": [
            {"name": name, "translation_units": count}
            for name, count in sorted(duplicate_names.items(), key=lambda kv: (-kv[1], kv[0]))[:25]
        ],
        "files": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k not in {"files", "top_cross_tu_duplicate_names"}}, indent=2))
    return 0 if parsed == len(files) else 2


if __name__ == "__main__":
    raise SystemExit(main())
