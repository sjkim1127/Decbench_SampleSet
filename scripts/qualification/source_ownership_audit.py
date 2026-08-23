#!/usr/bin/env python3
"""Use DecBench's own DWARF helpers to estimate project-owned function survival.

The audit mirrors the source-attribution idea in scripts/run_benchmark.py without
importing the full decompiler stack.  A function counts as project-owned when its
DWARF decl_file maps to one of the captured .ii translation-unit stems.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def linked_image(path: Path) -> bool:
    try:
        with path.open('rb') as f:
            magic = f.read(4)
            if magic == b'\x7fELF':
                return True
            if magic[:2] != b'MZ':
                return False
            f.seek(0x3C)
            off = int.from_bytes(f.read(4), 'little')
            f.seek(off)
            return f.read(4) == b'PE\0\0'
    except OSError:
        return False


def audit_binary(binary: Path, source_stems: set[str], binfmt, build_stem_index, strip_source_ext) -> dict:
    try:
        dw = binfmt.dwarf_info(binary)
    except Exception as exc:
        return {'binary': binary.name, 'functions': [], 'error': f'{type(exc).__name__}: {exc}'}
    if dw is None:
        return {'binary': binary.name, 'functions': [], 'error': 'no usable DWARF'}

    stem_index = build_stem_index(source_stems)
    file_tables: dict[int, list] = {}
    functions = []
    try:
        for cu in dw.iter_CUs():
            for die in cu.iter_DIEs():
                if die.tag != 'DW_TAG_subprogram' or 'DW_AT_low_pc' not in die.attributes:
                    continue
                name = binfmt.die_str_attr(die, 'DW_AT_name')
                if not name:
                    continue
                linkage = binfmt.die_str_attr(die, 'DW_AT_linkage_name') or binfmt.die_str_attr(die, 'DW_AT_MIPS_linkage_name')
                fi, owner = binfmt.die_attr_owner(die, 'DW_AT_decl_file')
                if fi is None or owner is None:
                    continue
                files = binfmt.cu_file_table(dw, owner.cu, file_tables)
                if not (0 <= fi.value < len(files)) or files[fi.value] is None:
                    continue
                decl_file = os.path.basename(files[fi.value])
                stem = strip_source_ext(decl_file)
                matched = stem_index.get(stem)
                if matched is None:
                    for norm, original in stem_index.items():
                        if norm.endswith('-' + stem) or norm.endswith('_' + stem):
                            matched = original
                            break
                if matched is None:
                    continue
                functions.append({
                    'address': int(die.attributes['DW_AT_low_pc'].value),
                    'name': name,
                    'linkage_name': linkage,
                    'decl_file': decl_file,
                    'translation_unit': matched,
                })
    except Exception as exc:
        return {'binary': binary.name, 'functions': functions, 'error': f'{type(exc).__name__}: {exc}'}
    return {'binary': binary.name, 'functions': functions}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    ap.add_argument('--decbench-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()

    sys.path.insert(0, str(args.decbench_root.resolve()))
    from decbench.utils import binfmt
    from decbench.utils.langs import build_stem_index, strip_source_ext

    root = args.root.resolve()
    per_opt = {}
    for opt_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name in {'O0', 'O2', 'O2-noinline'}):
        ii_files = sorted(opt_dir.rglob('*.ii'))
        source_stems = {p.stem for p in ii_files}
        binaries = sorted(p for p in opt_dir.rglob('*') if p.is_file() and linked_image(p))
        audited = [audit_binary(p, source_stems, binfmt, build_stem_index, strip_source_ext) for p in binaries]
        identities = set()
        short_names = set()
        total = 0
        for item in audited:
            for fn in item.get('functions', []):
                total += 1
                short_names.add(fn['name'])
                identities.add(fn.get('linkage_name') or f"{fn['translation_unit']}::{fn['name']}@{fn['address']:x}")
        per_opt[opt_dir.name] = {
            'ii_files': len(ii_files),
            'source_stems': len(source_stems),
            'binary_count': len(binaries),
            'project_owned_function_records': total,
            'unique_short_names': len(short_names),
            'identity_set': sorted(identities),
            'binaries': audited,
        }

    baseline = set(per_opt.get('O0', {}).get('identity_set', []))
    survival = {}
    for opt, data in per_opt.items():
        identities = set(data.get('identity_set', []))
        common = baseline & identities
        survival[opt] = {
            'identities': len(identities),
            'survive_from_O0': len(common),
            'survival_rate_vs_O0': round(len(common) / len(baseline), 6) if baseline else 0.0,
        }

    serializable = json.loads(json.dumps(per_opt))
    for data in serializable.values():
        data.pop('identity_set', None)
    out = {
        'root': str(root),
        'per_optimization': serializable,
        'optimization_survival': survival,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2), encoding='utf-8')
    print(json.dumps({
        'per_optimization': {
            k: {x: v for x, v in d.items() if x != 'binaries'}
            for k, d in serializable.items()
        },
        'optimization_survival': survival,
    }, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
