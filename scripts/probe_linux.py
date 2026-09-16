#!/usr/bin/env python3
"""Linux/GCC O0 qualifier for candidate DecBench C++ projects."""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import corpus_pipeline as cp

CMAKE_PROBE = re.compile(r'(?:^|/)CMakeFiles/(?:\d+(?:\.\d+)+|CMakeScratch)(?:/|$)')


def is_toolchain_probe(path: Path, search_root: Path) -> bool:
    try:
        rel = path.relative_to(search_root).as_posix()
    except ValueError:
        rel = path.as_posix()
    return bool(
        CMAKE_PROBE.search(rel)
        or 'CMakeDetermineCompilerABI' in rel
        or 'CompilerIdC' in rel
        or '/meson-private/' in f'/{rel}'
        or '/meson-logs/' in f'/{rel}'
        or path.name.startswith('conftest')
    )


def build(root: Path, system: str) -> tuple[bool, list[dict[str, Any]], Path]:
    env = os.environ.copy()
    env.update({'CC': 'gcc', 'CXX': 'g++', 'CFLAGS': cp.O0_FLAGS, 'CXXFLAGS': cp.O0_FLAGS})
    steps: list[dict[str, Any]] = []
    b = root / '_decbench_build'
    if system == 'cmake':
        cfg = [
            'cmake', '-S', '.', '-B', str(b), '-G', 'Ninja',
            '-DCMAKE_BUILD_TYPE=',
            '-DCMAKE_C_COMPILER=gcc', '-DCMAKE_CXX_COMPILER=g++',
            f'-DCMAKE_C_FLAGS={cp.O0_FLAGS}', f'-DCMAKE_CXX_FLAGS={cp.O0_FLAGS}',
            '-DBUILD_SHARED_LIBS=ON',
            *cp.COMMON_CMAKE_DISABLES,
        ]
        r = cp.run(cfg, root, env, 180)
        steps.append({'name': 'configure', **r})
        if r['returncode'] != 0:
            return False, steps, b
        r = cp.run(['cmake', '--build', str(b), '-j', '2'], root, env, 420)
        steps.append({'name': 'build', **r})
        return r['returncode'] == 0, steps, b
    if system == 'meson':
        r = cp.run(['meson', 'setup', str(b), '--buildtype=plain', '-Ddefault_library=shared'], root, env, 180)
        steps.append({'name': 'configure', **r})
        if r['returncode'] != 0:
            return False, steps, b
        r = cp.run(['meson', 'compile', '-C', str(b), '-j', '2'], root, env, 420)
        steps.append({'name': 'build', **r})
        return r['returncode'] == 0, steps, b
    if system == 'autotools':
        r = cp.run(['autoreconf', '-fi'], root, env, 120)
        steps.append({'name': 'autoreconf', **r})
        if r['returncode'] != 0:
            return False, steps, root
        configure = root / 'configure'
        if configure.exists():
            configure.chmod(configure.stat().st_mode | stat.S_IXUSR)
        r = cp.run(['./configure', '--disable-dependency-tracking', '--enable-shared'], root, env, 180)
        steps.append({'name': 'configure', **r})
        if r['returncode'] != 0:
            return False, steps, root
        r = cp.run(['make', '-j2'], root, env, 420)
        steps.append({'name': 'build', **r})
        return r['returncode'] == 0, steps, root
    if system == 'make':
        r = cp.run(['make', '-j2'], root, env, 420)
        steps.append({'name': 'build', **r})
        return r['returncode'] == 0, steps, root
    return False, [{'name': 'detect', 'returncode': 2, 'output': 'unsupported build system'}], root


def inspect(root: Path, search_root: Path) -> dict[str, Any]:
    ii = [p for p in search_root.rglob('*.ii') if p.is_file() and not is_toolchain_probe(p, search_root)]
    linked: list[Path] = []
    for p in search_root.rglob('*'):
        if not p.is_file() or p.is_symlink() or is_toolchain_probe(p, search_root):
            continue
        if '.git' in p.parts:
            continue
        try:
            if p.stat().st_size > 400 * 1024 * 1024:
                continue
        except OSError:
            continue
        if cp.is_elf_linked(p):
            linked.append(p)
    dwarf_bins = [p for p in linked if cp.dwarf_present(p)]
    funcs = 0
    for p in sorted(dwarf_bins, key=lambda q: q.stat().st_size)[:3]:
        funcs += cp.dwarf_subprogram_count(p)

    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(root))
        except ValueError:
            return str(p)

    return {
        'linked_elf_count': len(linked),
        'dwarf_elf_count': len(dwarf_bins),
        'ii_count': len(ii),
        'sample_binaries': [rel(p) for p in dwarf_bins[:8]],
        'sample_ii': [rel(p) for p in ii[:8]],
        'dwarf_subprogram_count_sample': funcs,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        'repo': args.repo,
        'status': 'FAIL',
        'qualification': False,
        'flags': cp.O0_FLAGS,
        'qualifier_version': 2,
    }
    with tempfile.TemporaryDirectory(prefix='decbench-cpp-') as td:
        root = Path(td) / 'src'
        clone = cp.run(
            ['git', 'clone', '--depth', '1', '--recurse-submodules', '--shallow-submodules', f'https://github.com/{args.repo}.git', str(root)],
            Path(td), os.environ.copy(), 150,
        )
        result['clone'] = clone
        if clone['returncode'] != 0:
            result['failure_stage'] = 'clone'
            out.write_text(json.dumps(result, indent=2) + '\n')
            return 0
        try:
            result['revision'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        except Exception:
            result['revision'] = None
        system = cp.detect_build_system(root)
        result['build_system'] = system
        if not system:
            result['failure_stage'] = 'build_system'
            out.write_text(json.dumps(result, indent=2) + '\n')
            return 0
        ok, steps, search_root = build(root, system)
        result['steps'] = steps
        if not ok:
            result['failure_stage'] = 'build'
            out.write_text(json.dumps(result, indent=2) + '\n')
            return 0
        artifacts = inspect(root, search_root if search_root.exists() else root)
        result['artifacts'] = artifacts
        qualified = artifacts['linked_elf_count'] > 0 and artifacts['dwarf_elf_count'] > 0 and artifacts['ii_count'] > 0
        result['qualification'] = qualified
        result['status'] = 'PASS' if qualified else 'FAIL'
        if not qualified:
            result['failure_stage'] = 'artifact_oracle'
    out.write_text(json.dumps(result, indent=2) + '\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
