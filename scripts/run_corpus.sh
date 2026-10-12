#!/usr/bin/env bash
# Usage: run_corpus.sh <final-48.csv> <outdir> [jobs]
# Builds every Tier A repo at O0/O2/O2-noinline in the decbench-cpp-build image.
# Resumable: skips (repo,opt) pairs that already have result.json.
set -u
CSV=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); OUT=$(mkdir -p "$2" && cd "$2" && pwd); JOBS=${3:-3}
HERE=$(cd "$(dirname "$0")" && pwd)
docker image inspect decbench-cpp-build >/dev/null 2>&1 || docker build -t decbench-cpp-build "$HERE/docker"
job() {
  repo=$1; rev=$2; opt=$3; proj=${repo#*/}
  [ -f "$OUT/$opt/$proj/result.json" ] && return 0
  timeout 1500 docker run --rm -v "$HERE":/scripts:ro -v "$OUT":/out -w /scripts decbench-cpp-build \
    python3 build_multi_opt.py --repo "$repo" --revision "$rev" --opt "$opt" --out /out \
    >"$OUT/$opt-$proj.log" 2>&1
  [ -f "$OUT/$opt/$proj/result.json" ] || { mkdir -p "$OUT/$opt/$proj"; \
    echo "{\"repo\":\"$repo\",\"opt\":\"$opt\",\"ok\":false,\"failure_stage\":\"timeout_or_crash\"}" > "$OUT/$opt/$proj/result.json"; }
}
export -f job; export OUT HERE
python3 - "$CSV" <<'E' | xargs -P "$JOBS" -L1 bash -c 'job "$@"' _
import csv, sys
for r in csv.DictReader(open(sys.argv[1])):
    if r["tier"] == "A":
        for opt in ("O0", "O2", "O2-noinline"):
            print(r["repo"], r["revision"], opt)
E
