#!/usr/bin/env bash
set -euo pipefail
base=/work/staged/qualification-v2
src=/work/sources/ssdb
revision="${SSDB_REVISION:?set SSDB_REVISION}"
test "$(git -C "$src" rev-parse HEAD)" = "$revision"
for mode in O0 O2 O2-noinline; do
  case "$mode" in O0) opt='-O0' ;; O2) opt='-O2' ;; O2-noinline) opt='-O2 -fno-inline' ;; esac
  work="/work/builds/linux/ssdb/$mode/source"
  out="$base/linux/arm64/$mode/ssdb"
  mkdir -p "$work" "$out"
  git -C "$src" archive HEAD | tar -x -C "$work"
  cd "$work"
  sh build.sh > "$out/build.log" 2>&1
  flags="$opt -g -fno-builtin -save-temps=obj -std=c++11 -DNDEBUG -D__STDC_FORMAT_MACROS -DNEW_MAC -Wall -Wno-sign-compare -I$work/deps/leveldb-1.20/include -I$work/deps/jemalloc-4.1.0/include"
  printf '%s\n' "make CFLAGS=$flags CXXFLAGS=$flags" > "$out/commands.txt"
  for component in deps/leveldb-1.20 src/util src/net src/client src/ssdb src; do
    CXXFLAGS="$flags" make -C "$work/$component" -j3 "CFLAGS=$flags" >> "$out/build.log" 2>&1
  done
  cp ssdb-server "$out/ssdb-server"
  cp build_config.mk "$out/generated-build-config.mk"
  find src -name '*.ii' -print0 | tar --null -czf "$out/preprocessed.tar.gz" -T -
  MODE="$mode" FLAGS="$flags" REVISION="$revision" OUTPUT="$out" python3 - <<'PY'
import os,json,hashlib,subprocess
from pathlib import Path
p=Path(os.environ['OUTPUT']);binary=p/'ssdb-server';s={'state':'artifact-built','project':'ssdb','platform':'linux','architecture':'aarch64','optimization':os.environ['MODE'],'source_repository':'ideawu/ssdb','source_revision':os.environ['REVISION'],'binary':str(binary.relative_to('/work/staged/qualification-v2')),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'effective_flags':os.environ['FLAGS'],'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],'scoring_ready':False,'remaining_gates':['input strip/code parity','source-owned function index','full C++ type scoring policy']};(p/'status.json').write_text(json.dumps(s,indent=2));print(json.dumps(s),flush=True)
PY
 done
