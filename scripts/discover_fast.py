#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import corpus_pipeline as cp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    gh = cp.GH(os.environ.get('GITHUB_TOKEN'))
    repos = cp.repo_search(gh)
    if len(repos) < 450:
        raise RuntimeError(f'expected roughly 500 search results, got {len(repos)}')

    def inspect(pair):
        i, repo = pair
        systems, notes = cp.root_markers(gh, repo['full_name'], repo['default_branch'])
        score, reasons = cp.static_score(repo, systems, notes)
        return {
            'rank': i,
            'repo': repo['full_name'],
            'clone_url': repo['clone_url'],
            'default_branch': repo['default_branch'],
            'size_kib': repo.get('size', 0),
            'stars': repo.get('stargazers_count', 0),
            'license': (repo.get('license') or {}).get('spdx_id'),
            'build_systems': systems,
            'notes': notes,
            'static_score': score,
            'score_reasons': reasons,
        }

    with ThreadPoolExecutor(max_workers=6) as pool:
        records = list(pool.map(inspect, enumerate(repos, 1)))

    eligible = [r for r in records if r['build_systems'] and r['static_score'] > 0]
    eligible.sort(key=lambda r: (-r['static_score'], r['size_kib'], r['repo'].lower()))
    preflight = eligible[:cp.PREFLIGHT_LIMIT]
    build = preflight[:cp.BUILD_LIMIT]

    (out / 'candidates-500.json').write_text(json.dumps(records, indent=2) + '\n')
    (out / 'preflight-200.json').write_text(json.dumps(preflight, indent=2) + '\n')
    (out / 'build-100.json').write_text(json.dumps(build, indent=2) + '\n')
    (out / 'build-matrix.json').write_text(json.dumps({'repo': [r['repo'] for r in build]}, separators=(',', ':')) + '\n')
    summary = {
        'search_query': cp.SEARCH_QUERY,
        'collected': len(records),
        'eligible': len(eligible),
        'preflight': len(preflight),
        'build_matrix': len(build),
        'root_inspection_workers': 6,
    }
    (out / 'discovery-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
