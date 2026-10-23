"""Compile frozen original TUs and unchanged producer bodies; never execute them."""

from pathlib import Path
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import urllib.request


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv, log):
    try:
        result = subprocess.run(argv, capture_output=True, timeout=90)
        log.write_bytes(result.stdout + result.stderr)
        return {"argv": argv, "exit_code": result.returncode, "timeout": False}
    except subprocess.TimeoutExpired as error:
        log.write_bytes((error.stdout or b"") + (error.stderr or b""))
        return {"argv": argv, "exit_code": None, "timeout": True}


bundle = Path("targets/qualification-controls/mixed-msvc.json.gz")
plan = json.loads(gzip.decompress(bundle.read_bytes()))
output = Path("_qualification/mixed-msvc").resolve()
output.mkdir(parents=True, exist_ok=True)
compiler = shutil.which("cl.exe")
linker = shutil.which("link.exe")
if compiler is None or linker is None:
    raise RuntimeError("native MSVC environment missing")
version_run = subprocess.run([compiler], capture_output=True)
version_text = (version_run.stdout + version_run.stderr).decode("utf-8", "replace")
(output / "compiler-version.log").write_text(version_text)
version_match = re.search(r"Version\s+([\d.]+)", version_text)
version = version_match[1] if version_match else None
sdk = os.environ.get("WindowsSDKVersion", "").rstrip("\\/")
supported = version == plan["compiler_version"] and sdk == plan["sdk_version"]
report = {
    "schema": plan["schema"], "bundle_sha256": digest(bundle),
    "workflow_commit": os.environ.get("GITHUB_SHA"),
    "compiler": compiler, "compiler_version": version,
    "compiler_sha256": digest(Path(compiler)), "linker_sha256": digest(Path(linker)),
    "sdk_version": sdk,
    "runner_image": {key: os.environ.get(key) for key in ("ImageOS", "ImageVersion", "RUNNER_OS", "RUNNER_ARCH")},
    "toolchain_supported": supported, "rows": [], "original_commands": [],
    "official_score": False, "execution_parity": False,
}
for name in ("c1.dll", "c1xx.dll", "c2.dll", "mspdbcore.dll"):
    path = Path(compiler).parent / name
    if path.exists():
        report.setdefault("compiler_components", {})[name] = digest(path)
if supported:
    with urllib.request.urlopen(plan["original_tu_url"], timeout=120) as response:
        archive_bytes = response.read()
    if hashlib.sha256(archive_bytes).hexdigest() != plan["original_tu_sha256"]:
        raise RuntimeError("frozen TU archive hash mismatch")
    original = output / "original-control"
    original.mkdir(exist_ok=True)
    objects = []
    with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
        for index, member in enumerate(plan["members"]):
            stream = archive.extractfile(member)
            if stream is None:
                raise RuntimeError("missing frozen TU")
            source = original / f"{index:02d}.ii"
            source.write_bytes(stream.read())
            obj = original / f"{index:02d}.obj"
            argv = [compiler, *plan["original_flags"], "/c", str(source), f"/Fo{obj}", f"/Fd{original / 'compile.pdb'}"]
            command = run(argv, original / f"compile-{index:02d}.log")
            report["original_commands"].append({**command, "source_sha256": digest(source)})
            objects.append(str(obj))
    if all(row["exit_code"] == 0 for row in report["original_commands"]):
        argv = [linker, "/NOLOGO", "/DLL", "/DEBUG:FULL", "/INCREMENTAL:NO", "/OPT:NOREF", "/OPT:NOICF", *objects, f"/OUT:{original / 'control.dll'}", f"/PDB:{original / 'control.pdb'}"]
        report["original_commands"].append(run(argv, original / "link.log"))
for row in plan["rows"]:
    directory = output / "recovered" / row["id"]
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "recovered.c"
    source.write_bytes(row["source"].encode())
    if digest(source) != row["source_sha256"]:
        raise RuntimeError("producer source hash mismatch")
    if supported:
        command = run([compiler, *plan["recovered_flags"], "/c", str(source), f"/Fo{directory / 'recovered.obj'}"], directory / "compile.log")
    else:
        command = {"exit_code": None, "timeout": False, "environment_error": "exact compiler/SDK unavailable"}
    report["rows"].append({**{key: value for key, value in row.items() if key != "source"}, **command})
(output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"toolchain_supported": supported, "compiler_version": version, "sdk_version": sdk, "requested": len(report["rows"]), "compiled": sum(row["exit_code"] == 0 for row in report["rows"])}))
