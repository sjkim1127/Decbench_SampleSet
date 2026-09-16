#!/usr/bin/env python3
"""Automated C++ corpus funnel for DecBench target qualification.

Stages:
  discover  - collect 500 public C++ repositories from GitHub, inspect root build
              metadata, score static suitability, keep a 200-repo preflight set,
              and emit a 100-repo Linux/GCC build matrix.
  probe     - shallow-clone one repository, attempt a bounded O0 debug build,
              and verify linked ELF + DWARF + preprocessed .ii artifacts.
  finalize  - aggregate probe JSON files and choose up to 50 qualified targets.

This is intentionally a *qualification funnel*, not a benchmark run. A PASS means
that the repository produced at least one linked ELF carrying DWARF and at least
one C++ preprocessed translation unit under controlled O0 flags. Full DecBench
GED/type/byte scoring remains a separate stage.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SEARCH_QUERY = "language:C++ stars:>=100 archived:false fork:false"
SEARCH_PAGES = 5
SEARCH_PER_PAGE = 100
PREFLIGHT_LIMIT = 200
BUILD_LIMIT = 100
FINAL_LIMIT = 50

BAD_NAME_RE = re.compile(
    r"(?:leetcode|course|tutorial|primer|algorithm|interview|awesome|learning|"
    r"practice|examples?|samples?|cookbook|roadmap|handbook|guide|clrs|baekjoon)",
    re.I,
)
CROSS_ONLY_RE = re.compile(
    r"(?:arduino|esp32|firmware|autopilot|cuda|tensorrt|rocm|hip$|ndk)", re.I
)
BUILD_MARKERS = {
    "cmake": "CMakeLists.txt",
    "meson": "meson.build",
    "autotools": "configure.ac",
    "autotools_legacy": "configure.in",
    "make": "Makefile",
}

COMMON_CMAKE_DISABLES = [
    "-DBUILD_TESTING=OFF",
    "-DBUILD_TESTS=OFF",
    "-DBUILD_EXAMPLES=OFF",
    "-DBUILD_BENCHMARKS=OFF",
    "-DENABLE_TESTING=OFF",
    "-DENABLE_TESTS=OFF",
    "-DENABLE_EXAMPLES=OFF",
]
O0_FLAGS = "-O0 -g -fno-builtin -save-temps=obj"


class GH:
    def __init__(self, token: str | None):
        self.token = token

    def get(self, url: str) -> Any:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "decbench-cpp-corpus-funnel/1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        req = urllib.request.Request(url, headers=headers)
        last: Exception | None = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (403, 429) and attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError) as e:
                last = e
                if attempt < 3:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise RuntimeError(last)


def repo_search(gh: GH) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    for page in range(1, SEARCH_PAGES + 1):
        q = urllib.parse.quote_plus(SEARCH_QUERY)
        url = (
            f"https://api.github.com/search/repositories?q={q}"
            f"&sort=stars&order=desc&per_page={SEARCH_PER_PAGE}&page={page}"
        )
        data = gh.get(url)
        repos.extend(data.get("items", []))
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for r in repos:
        name = r["full_name"]
        if name not in seen:
            seen.add(name)
            unique.append(r)
    return unique[: SEARCH_PAGES * SEARCH_PER_PAGE]


def root_markers(gh: GH, full_name: str, default_branch: str) -> tuple[list[str], list[str]]:
    url = f"https://api.github.com/repos/{full_name}/contents?ref={urllib.parse.quote(default_branch, safe='')}"
    try:
        items = gh.get(url)
    except Exception:
        return [], ["root_contents_unavailable"]
    names = {item.get("name", "") for item in items if isinstance(item, dict)}
    systems: list[str] = []
    for system, marker in BUILD_MARKERS.items():
        if marker in names:
            systems.append("autotools" if system == "autotools_legacy" else system)
    systems = list(dict.fromkeys(systems))
    notes: list[str] = []
    if ".gitmodules" in names:
        notes.append("submodules")
    if "vcpkg.json" in names or "vcpkg-configuration.json" in names:
        notes.append("vcpkg")
    if "conanfile.py" in names or "conanfile.txt" in names:
        notes.append("conan")
    return systems, notes


def static_score(repo: dict[str, Any], systems: list[str], notes: list[str]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    name = repo["full_name"]
    size = int(repo.get("size") or 0)
    stars = int(repo.get("stargazers_count") or 0)

    if BAD_NAME_RE.search(name):
        score -= 80
        reasons.append("tutorial_or_collection_name")
    if CROSS_ONLY_RE.search(name):
        score -= 35
        reasons.append("likely_cross_or_accelerator_specific")

    if systems:
        score += 35
        reasons.append("root_build_system")
    if "cmake" in systems:
        score += 25
        reasons.append("cmake")
    elif "meson" in systems:
        score += 20
        reasons.append("meson")
    elif "autotools" in systems:
        score += 15
        reasons.append("autotools")
    elif "make" in systems:
        score += 10
        reasons.append("make")
    else:
        score -= 50
        reasons.append("no_supported_root_build_system")

    if 300 <= size <= 80_000:
        score += 25
        reasons.append("good_repo_size")
    elif 80_000 < size <= 200_000:
        score += 10
        reasons.append("medium_large_repo")
    elif size > 500_000:
        score -= 45
        reasons.append("very_large_repo")
    elif size > 200_000:
        score -= 20
        reasons.append("large_repo")
    elif size < 100:
        score -= 20
        reasons.append("very_small_repo")

    if "submodules" in notes:
        score -= 8
        reasons.append("submodules")
    if "vcpkg" in notes or "conan" in notes:
        score -= 8
        reasons.append("package_manager_dependency")

    if stars >= 10_000:
        score += 8
    elif stars >= 1_000:
        score += 5
    elif stars >= 100:
        score += 2

    return score, reasons


def discover(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    gh = GH(args.github_token or os.environ.get("GITHUB_TOKEN"))
    repos = repo_search(gh)
    if len(repos) < 450:
        raise RuntimeError(f"expected roughly 500 search results, got {len(repos)}")

    records: list[dict[str, Any]] = []
    for i, repo in enumerate(repos, 1):
        systems, notes = root_markers(gh, repo["full_name"], repo["default_branch"])
        score, reasons = static_score(repo, systems, notes)
        records.append(
            {
                "rank": i,
                "repo": repo["full_name"],
                "clone_url": repo["clone_url"],
                "default_branch": repo["default_branch"],
                "size_kib": repo.get("size", 0),
                "stars": repo.get("stargazers_count", 0),
                "license": (repo.get("license") or {}).get("spdx_id"),
                "build_systems": systems,
                "notes": notes,
                "static_score": score,
                "score_reasons": reasons,
            }
        )
        if i % 50 == 0:
            print(f"inspected {i}/{len(repos)} repositories", flush=True)

    eligible = [r for r in records if r["build_systems"] and r["static_score"] > 0]
    eligible.sort(key=lambda r: (-r["static_score"], r["size_kib"], r["repo"].lower()))
    preflight = eligible[:PREFLIGHT_LIMIT]
    build = preflight[:BUILD_LIMIT]

    (out / "candidates-500.json").write_text(json.dumps(records, indent=2) + "\n")
    (out / "preflight-200.json").write_text(json.dumps(preflight, indent=2) + "\n")
    (out / "build-100.json").write_text(json.dumps(build, indent=2) + "\n")
    matrix = {"repo": [r["repo"] for r in build]}
    (out / "build-matrix.json").write_text(json.dumps(matrix, separators=(",", ":")) + "\n")

    summary = {
        "search_query": SEARCH_QUERY,
        "collected": len(records),
        "eligible": len(eligible),
        "preflight": len(preflight),
        "build_matrix": len(build),
    }
    (out / "discovery-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))
    return 0


def run(cmd: list[str] | str, cwd: Path, env: dict[str, str], timeout: int, shell: bool = False) -> dict[str, Any]:
    started = time.monotonic()
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            shell=shell,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        return {
            "returncode": p.returncode,
            "seconds": round(time.monotonic() - started, 3),
            "output": p.stdout[-24_000:],
            "timeout": False,
        }
    except subprocess.TimeoutExpired as e:
        raw = e.stdout or ""
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", "replace")
        return {
            "returncode": 124,
            "seconds": round(time.monotonic() - started, 3),
            "output": raw[-24_000:],
            "timeout": True,
        }


def detect_build_system(root: Path) -> str | None:
    if (root / "CMakeLists.txt").exists():
        return "cmake"
    if (root / "meson.build").exists():
        return "meson"
    if (root / "configure.ac").exists() or (root / "configure.in").exists():
        return "autotools"
    if (root / "Makefile").exists():
        return "make"
    return None


def build_repo(root: Path, system: str) -> tuple[bool, list[dict[str, Any]], Path]:
    env = os.environ.copy()
    env.update({"CC": "gcc", "CXX": "g++", "CFLAGS": O0_FLAGS, "CXXFLAGS": O0_FLAGS})
    steps: list[dict[str, Any]] = []
    build_dir = root / "_decbench_build"

    if system == "cmake":
        cfg = [
            "cmake", "-S", ".", "-B", str(build_dir), "-G", "Ninja",
            "-DCMAKE_BUILD_TYPE=",
            "-DCMAKE_C_COMPILER=gcc", "-DCMAKE_CXX_COMPILER=g++",
            f"-DCMAKE_C_FLAGS={O0_FLAGS}", f"-DCMAKE_CXX_FLAGS={O0_FLAGS}",
            *COMMON_CMAKE_DISABLES,
        ]
        r = run(cfg, root, env, 180)
        steps.append({"name": "configure", **r})
        if r["returncode"] != 0:
            return False, steps, build_dir
        r = run(["cmake", "--build", str(build_dir), "-j", "2"], root, env, 420)
        steps.append({"name": "build", **r})
        return r["returncode"] == 0, steps, build_dir

    if system == "meson":
        r = run(["meson", "setup", str(build_dir), "--buildtype=plain"], root, env, 180)
        steps.append({"name": "configure", **r})
        if r["returncode"] != 0:
            return False, steps, build_dir
        r = run(["meson", "compile", "-C", str(build_dir), "-j", "2"], root, env, 420)
        steps.append({"name": "build", **r})
        return r["returncode"] == 0, steps, build_dir

    if system == "autotools":
        r = run(["autoreconf", "-fi"], root, env, 120)
        steps.append({"name": "autoreconf", **r})
        if r["returncode"] != 0:
            return False, steps, root
        configure = root / "configure"
        if configure.exists():
            configure.chmod(configure.stat().st_mode | stat.S_IXUSR)
        r = run(["./configure", "--disable-dependency-tracking"], root, env, 180)
        steps.append({"name": "configure", **r})
        if r["returncode"] != 0:
            return False, steps, root
        r = run(["make", "-j2"], root, env, 420)
        steps.append({"name": "build", **r})
        return r["returncode"] == 0, steps, root

    if system == "make":
        r = run(["make", "-j2"], root, env, 420)
        steps.append({"name": "build", **r})
        return r["returncode"] == 0, steps, root

    return False, [{"name": "detect", "returncode": 2, "output": "unsupported build system"}], root


def is_elf_linked(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            if f.read(4) != b"\x7fELF":
                return False
            f.seek(16)
            raw = f.read(2)
            if len(raw) != 2:
                return False
            e_type = int.from_bytes(raw, "little")
            return e_type in (2, 3)
    except OSError:
        return False


def dwarf_present(path: Path) -> bool:
    p = subprocess.run(["readelf", "-S", str(path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    return p.returncode == 0 and ".debug_info" in p.stdout


def dwarf_subprogram_count(path: Path) -> int:
    try:
        p = subprocess.run(
            ["readelf", "--debug-dump=info", str(path)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=90,
        )
        if p.returncode != 0:
            return 0
        return p.stdout.count("DW_TAG_subprogram")
    except subprocess.TimeoutExpired:
        return 0


def inspect_artifacts(root: Path, search_root: Path) -> dict[str, Any]:
    ii = [p for p in search_root.rglob("*.ii") if p.is_file()]
    linked: list[Path] = []
    for p in search_root.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        if ".git" in p.parts:
            continue
        try:
            if p.stat().st_size > 400 * 1024 * 1024:
                continue
        except OSError:
            continue
        if is_elf_linked(p):
            linked.append(p)
    dwarf_bins = [p for p in linked if dwarf_present(p)]
    function_count = 0
    for p in sorted(dwarf_bins, key=lambda q: q.stat().st_size)[:3]:
        function_count += dwarf_subprogram_count(p)

    def rel(p: Path) -> str:
        try:
            return str(p.relative_to(root))
        except ValueError:
            return str(p)

    return {
        "linked_elf_count": len(linked),
        "dwarf_elf_count": len(dwarf_bins),
        "ii_count": len(ii),
        "sample_binaries": [rel(p) for p in dwarf_bins[:8]],
        "sample_ii": [rel(p) for p in ii[:8]],
        "dwarf_subprogram_count_sample": function_count,
    }


def probe(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    repo = args.repo
    clone_url = f"https://github.com/{repo}.git"
    result: dict[str, Any] = {
        "repo": repo,
        "status": "FAIL",
        "qualification": False,
        "flags": O0_FLAGS,
    }
    with tempfile.TemporaryDirectory(prefix="decbench-cpp-") as td:
        root = Path(td) / "src"
        env = os.environ.copy()
        clone = run(
            ["git", "clone", "--depth", "1", "--recurse-submodules", "--shallow-submodules", clone_url, str(root)],
            Path(td), env, 150,
        )
        result["clone"] = clone
        if clone["returncode"] != 0:
            result["failure_stage"] = "clone"
            out.write_text(json.dumps(result, indent=2) + "\n")
            return 0
        try:
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        except Exception:
            sha = None
        result["revision"] = sha
        system = detect_build_system(root)
        result["build_system"] = system
        if not system:
            result["failure_stage"] = "build_system"
            out.write_text(json.dumps(result, indent=2) + "\n")
            return 0
        ok, steps, search_root = build_repo(root, system)
        result["steps"] = steps
        if not ok:
            result["failure_stage"] = "build"
            out.write_text(json.dumps(result, indent=2) + "\n")
            return 0
        artifacts = inspect_artifacts(root, search_root if search_root.exists() else root)
        result["artifacts"] = artifacts
        qualified = (
            artifacts["linked_elf_count"] > 0
            and artifacts["dwarf_elf_count"] > 0
            and artifacts["ii_count"] > 0
        )
        result["qualification"] = qualified
        result["status"] = "PASS" if qualified else "FAIL"
        if not qualified:
            result["failure_stage"] = "artifact_oracle"
    out.write_text(json.dumps(result, indent=2) + "\n")
    return 0


def final_score(r: dict[str, Any]) -> float:
    a = r.get("artifacts") or {}
    funcs = int(a.get("dwarf_subprogram_count_sample") or 0)
    ii = int(a.get("ii_count") or 0)
    bins = int(a.get("dwarf_elf_count") or 0)
    return min(funcs, 4000) * 1.0 + min(ii, 150) * 8.0 + min(bins, 20) * 20.0


def finalize(args: argparse.Namespace) -> int:
    root = Path(args.probes)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for p in root.rglob("*.json"):
        try:
            r = json.loads(p.read_text())
        except Exception:
            continue
        if isinstance(r, dict) and "repo" in r and "qualification" in r:
            r["final_score"] = final_score(r) if r.get("qualification") else 0
            rows.append(r)
    rows.sort(key=lambda r: (-float(r.get("final_score", 0)), r["repo"].lower()))
    passed = [r for r in rows if r.get("qualification")]
    final = passed[:FINAL_LIMIT]
    (out / "build-results.json").write_text(json.dumps(rows, indent=2) + "\n")
    (out / "qualified.json").write_text(json.dumps(passed, indent=2) + "\n")
    (out / "final-50.json").write_text(json.dumps(final, indent=2) + "\n")
    summary = {
        "attempted": len(rows),
        "qualified": len(passed),
        "final_selected": len(final),
        "final_repos": [r["repo"] for r in final],
    }
    (out / "qualification-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover")
    d.add_argument("--out", required=True)
    d.add_argument("--github-token")
    d.set_defaults(func=discover)

    p = sub.add_parser("probe")
    p.add_argument("--repo", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(func=probe)

    f = sub.add_parser("finalize")
    f.add_argument("--probes", required=True)
    f.add_argument("--out", required=True)
    f.set_defaults(func=finalize)
    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
