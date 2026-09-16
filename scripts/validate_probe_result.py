#!/usr/bin/env python3
"""Remove configure/compiler sanity artifacts from a corpus probe result."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

CMAKE_VERSION_DIR = re.compile(r'(?:^|/)CMakeFiles/\d+(?:\.\d+)+(?:/|$)')


def is_probe(path: str) -> bool:
    normalized = path.replace('\\', '/')
    return bool(
        CMAKE_VERSION_DIR.search(normalized)
        or 'CMakeDetermineCompilerABI' in normalized
        or 'CompilerIdC' in normalized
        or '/CMakeScratch/' in f'/{normalized}'
        or '/meson-private/' in f'/{normalized}'
        or '/meson-logs/' in f'/{normalized}'
        or Path(normalized).name.startswith('conftest')
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('result')
    args = ap.parse_args()
    path = Path(args.result)
    data = json.loads(path.read_text())
    a = data.get('artifacts')
    if not isinstance(a, dict):
        return 0

    sample_bins = list(a.get('sample_binaries') or [])
    sample_ii = list(a.get('sample_ii') or [])
    probe_bins = sum(is_probe(x) for x in sample_bins)
    probe_ii = sum(is_probe(x) for x in sample_ii)

    linked = max(0, int(a.get('linked_elf_count') or 0) - probe_bins)
    dwarf = max(0, int(a.get('dwarf_elf_count') or 0) - probe_bins)
    ii = max(0, int(a.get('ii_count') or 0) - probe_ii)
    funcs = max(0, int(a.get('dwarf_subprogram_count_sample') or 0) - probe_bins)

    a['toolchain_probe_binaries_removed'] = probe_bins
    a['toolchain_probe_ii_removed'] = probe_ii
    a['linked_elf_count'] = linked
    a['dwarf_elf_count'] = dwarf
    a['ii_count'] = ii
    a['dwarf_subprogram_count_sample'] = funcs
    a['sample_binaries'] = [x for x in sample_bins if not is_probe(x)]
    a['sample_ii'] = [x for x in sample_ii if not is_probe(x)]

    qualified = linked > 0 and dwarf > 0 and ii > 0
    data['qualification'] = qualified
    data['status'] = 'PASS' if qualified else 'FAIL'
    if not qualified and data.get('failure_stage') is None:
        data['failure_stage'] = 'artifact_oracle_after_probe_filter'
    path.write_text(json.dumps(data, indent=2) + '\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
