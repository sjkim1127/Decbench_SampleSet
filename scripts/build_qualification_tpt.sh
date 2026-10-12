#!/usr/bin/env bash
set -euo pipefail
# External build recipe only; the upstream No-AI source tree is never edited.
revision="${TPT_REVISION:?set TPT_REVISION to the pinned upstream commit}"
apt-get update -qq
apt-get install -y -qq libsdl2-dev libfftw3-dev libluajit-5.1-dev libjsoncpp-dev >/dev/null
mkdir -p /work/sources/the-powder-toy
src=/work/sources/the-powder-toy
if [ ! -d "$src/.git" ]; then
  git init -q "$src"
  git -C "$src" remote add origin https://github.com/The-Powder-Toy/The-Powder-Toy.git
  git -C "$src" fetch -q --depth 1 origin "$revision"
  git -C "$src" checkout -q FETCH_HEAD
fi
test "$(git -C "$src" rev-parse HEAD)" = "$revision"
base=/work/staged/qualification-v2
mkdir -p "$base/sources/the-powder-toy"
git -C "$src" archive --format=tar.gz --output "$base/sources/the-powder-toy/original.tar.gz" HEAD
for mode in O0 O2 O2-noinline; do
  case "$mode" in
    O0) opt='-O0' ;;
    O2) opt='-O2' ;;
    O2-noinline) opt='-O2 -fno-inline' ;;
  esac
  flags="$opt -g -fno-builtin -save-temps=obj"
  build="/work/builds/linux/the-powder-toy/$mode"
  out="$base/linux/arm64/$mode/the-powder-toy"
  mkdir -p "$out"
  if [ ! -f "$build/build.ninja" ]; then
    meson setup "$build" "$src" -Dbuildtype=plain -Db_ndebug=true -Db_lto=false "-Dc_args=$flags" "-Dcpp_args=$flags" > "$out/build.log" 2>&1
  fi
  meson compile -C "$build" -j 3 >> "$out/build.log" 2>&1
  cp "$build/powder" "$out/powder"
  cp "$build/compile_commands.json" "$out/compile_commands.json"
  find "$build" -name '*.ii' -print0 | tar --null -czf "$out/preprocessed.tar.gz" -T -
  REVISION="$revision" FLAGS="$flags" MODE="$mode" OUTPUT="$out" python3 - <<'PY'
import os,json,hashlib,subprocess
from pathlib import Path
p=Path(os.environ['OUTPUT']);binary=p/'powder'
s={'state':'artifact-built','project':'the-powder-toy','platform':'linux','architecture':'aarch64','optimization':os.environ['MODE'],'source_repository':'The-Powder-Toy/The-Powder-Toy','source_revision':os.environ['REVISION'],'binary':str(binary.relative_to('/work/staged/qualification-v2')),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'effective_flags':os.environ['FLAGS'],'compiler':subprocess.check_output(['g++','--version'],text=True).splitlines()[0],'upstream_source_modified':False,'scoring_ready':False,'remaining_gates':['input strip/code parity','source-owned function index','full C++ type scoring policy']}
(p/'status.json').write_text(json.dumps(s,indent=2));print(json.dumps(s),flush=True)
PY
 done
test -z "$(git -C "$src" status --porcelain --untracked-files=no)"
