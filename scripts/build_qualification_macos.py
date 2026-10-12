#!/usr/bin/env python3
"""Build the pinned macOS pilot cells; preserve commands, .ii, dSYM and inputs."""

import argparse, hashlib, json, shutil, subprocess, tarfile, time
from pathlib import Path


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(cmd, cwd, log):
    log.write(json.dumps({"command": cmd, "cwd": str(cwd)}) + "\n")
    log.flush()
    subprocess.run(cmd, cwd=cwd, stdout=log, stderr=log, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True)
    a = ap.parse_args()
    root = a.root.resolve()
    plan = json.loads(a.plan.read_text())
    base = root / "staged/qualification-v2"
    for c in plan["cells"]:
        if c["platform"] != "macos":
            continue
        src = root / "sources" / c["project"]
        assert (
            subprocess.check_output(
                ["git", "-C", str(src), "rev-parse", "HEAD"], text=True
            ).strip()
            == c["source_revision"]
        )
        owned = base / "sources" / c["project"]
        owned.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(src),
                "archive",
                "--format=tar.gz",
                "--output",
                str(owned / "original.tar.gz"),
                "HEAD",
            ],
            check=True,
        )
        for mode, opt in [
            ("O0", "-O0"),
            ("O2", "-O2"),
            ("O2-noinline", "-O2 -fno-inline"),
        ]:
            build = root / "builds/macos" / c["project"] / mode
            out = base / "macos/arm64" / mode / c["project"]
            out.mkdir(parents=True, exist_ok=True)
            build.mkdir(parents=True, exist_ok=True)
            status = {
                "project": c["project"],
                "platform": "macos",
                "optimization": mode,
                "source_revision": c["source_revision"],
                "state": "building",
                "scoring_ready": False,
            }
            started = time.monotonic()
            try:
                flags = opt + " -g -fno-builtin -save-temps=obj"
                configure = [
                    "cmake",
                    "-S",
                    str(src),
                    "-B",
                    str(build),
                    "-G",
                    "Unix Makefiles",
                    "--fresh",
                    "-DCMAKE_BUILD_TYPE=Qualification",
                    "-DCMAKE_C_FLAGS=" + flags,
                    "-DCMAKE_CXX_FLAGS=" + flags,
                    "-DCMAKE_C_FLAGS_QUALIFICATION=-DNDEBUG",
                    "-DCMAKE_CXX_FLAGS_QUALIFICATION=-DNDEBUG",
                    "-DCMAKE_OSX_ARCHITECTURES=arm64",
                    "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
                    "-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF",
                    "-DBUILD_TESTING=OFF",
                ]
                if c["project"] == "snappy":
                    configure += [
                        "-DBUILD_SHARED_LIBS=ON",
                        "-DSNAPPY_BUILD_TESTS=OFF",
                        "-DSNAPPY_BUILD_BENCHMARKS=OFF",
                    ]
                    target = "snappy"
                    image = build / "libsnappy.dylib"
                elif c["project"] == "ninja":
                    target = "ninja"
                    image = build / "ninja"
                else:
                    configure += [
                        "-DBUILD_SHARED_LIBS=OFF",
                        "-DENABLE_GTEST=OFF",
                        "-DENABLE_BENCHMARK=OFF",
                        "-DBUILD_PYTHON=OFF",
                        "-DBUILD_OPENCC_JIEBA_PLUGIN=OFF",
                    ]
                    target = "opencc"
                    image = build / "src/tools/opencc"
                with (out / "build.log").open("w") as log:
                    run(configure, src, log)
                    run(
                        [
                            "cmake",
                            "--build",
                            str(build),
                            "--target",
                            target,
                            "--parallel",
                            "3",
                        ],
                        src,
                        log,
                    )
                    if not image.exists():
                        options = [
                            p
                            for p in build.rglob("opencc")
                            if p.is_file() and not p.is_symlink()
                        ]
                        assert len(options) == 1, options
                        image = options[0]
                    binary = out / image.name
                    shutil.copy2(image, binary)
                    run(
                        [
                            "xcrun",
                            "dsymutil",
                            str(image),
                            "-o",
                            str(out / (image.name + ".dSYM")),
                        ],
                        src,
                        log,
                    )
                    run(
                        [
                            "xcrun",
                            "dwarfdump",
                            "--verify",
                            str(out / (image.name + ".dSYM")),
                        ],
                        src,
                        log,
                    )
                    with (out / "debug-uuid.txt").open("w") as uuid:
                        subprocess.run(
                            [
                                "xcrun",
                                "dwarfdump",
                                "--uuid",
                                str(binary),
                                str(out / (image.name + ".dSYM")),
                            ],
                            stdout=uuid,
                            check=True,
                        )
                    stripped = out / (image.name + ".stripped")
                    shutil.copy2(binary, stripped)
                    run(["llvm-strip", "--strip-all", str(stripped)], src, log)
                    for path, label in [(binary, "original"), (stripped, "stripped")]:
                        with (out / (label + "-sections.txt")).open("w") as dest:
                            subprocess.run(
                                [
                                    "llvm-readobj",
                                    "--file-headers",
                                    "--sections",
                                    str(path),
                                ],
                                stdout=dest,
                                check=True,
                            )
                shutil.copy2(
                    build / "compile_commands.json", out / "compile_commands.json"
                )
                preprocessed = out / "preprocessed.tar.gz"
                iis = [
                    p
                    for p in build.rglob("*.ii")
                    if "CompilerId" not in str(p) and "CMakeScratch" not in str(p)
                ]
                assert iis, "No preprocessed TUs"
                with tarfile.open(preprocessed, "w:gz") as tar:
                    for p in sorted(iis):
                        tar.add(p, arcname=str(p.relative_to(build)))
                status.update(
                    state="artifact-built-debug-verified",
                    binary=str(binary.relative_to(base)),
                    binary_sha256=sha(binary),
                    stripped=str(stripped.relative_to(base)),
                    stripped_sha256=sha(stripped),
                    preprocessed_tus=len(iis),
                    compiler=subprocess.check_output(
                        ["xcrun", "clang++", "--version"], text=True
                    ).splitlines()[0],
                    effective_flags=flags + " -DNDEBUG",
                    remaining_gates=[
                        "source-owned function identity extraction",
                        "source/ABI type ground truth adapter",
                        "code-section parity and no-debug input verification",
                    ],
                )
            except Exception as e:
                status.update(state="failed", error=str(e))
            status["elapsed_seconds"] = time.monotonic() - started
            (out / "status.json").write_text(json.dumps(status, indent=2))
            print(json.dumps(status), flush=True)


if __name__ == "__main__":
    main()
