# C++ qualification v2 staging

This is an unofficial, versioned curation pipeline. Raw corpus files remain unchanged.
A staged binary is not automatically a qualified target, a scored function, or an official ranking entry.

## Initial matrix

The counting unit is **project × platform**. There are 15 planned cells, 10 unique projects and 45 planned linked images.

| Platform | Project and selected target |
|---|---|
| Linux arm64 | The Powder Toy `powder`; Snappy `libsnappy.so.1.2.2`; LevelDB `libleveldb.so.1.23.0`; SSDB `ssdb-server`; mergerfs `mergerfs`; OpenCC `opencc` |
| Windows x86_64 | Detours `withdll.exe`; WinSparkle `WinSparkle.dll`; Ninja `ninja.exe`; Snappy `snappy.dll`; OpenCC `opencc.exe`; Tracy `tracy-profiler.exe` |
| macOS arm64 | Ninja `ninja`; Snappy `libsnappy.dylib`; OpenCC `opencc` |

All cells use O0, O2 and O2-noinline. Platform/compiler/architecture are separate fields. These modes are controlled compiler profiles, not promises of identical transformations across compilers.
The initial matrix contains userspace systems software, a server, a GUI application, CLI programs and libraries. It does not contain a kernel or driver target. Future expansion should fill that gap.

## Stage and qualification contract

1. A candidate plan records exact repository revisions and linked target names.
2. Packaging checks verify files, hashes, debug identities, unchanged executable code and isolated debug-free inputs.
3. Oracle checks retain original sources, preprocessed TUs, build commands and concrete project function identities.
4. Complete qualification additionally requires missing provenance/ownership gates to pass.
5. Scoring requires platform-native identity/type adapters and an agreed C++ type policy. No score is assigned merely because a gate cannot run.

`scoring_ready=false` and `qualified=false` remain explicit in the preview. Inherited raw artifacts may lack full per-TU compiler/link command evidence.
The DWARF evidence exporter reuses the pinned DecBench reader at `8eeceb82088e97ace88d15a592db1ee76ab37384`. Its legacy variable summaries are **not** a complete source-level C++ type model. Original source and full debug information remain available for future policies.
Source CU ownership in inherited raw evidence is weaker than full per-declaration ownership; do not count its header-defined dependency functions as a proven project-only population.

## Observed packaging defects

- Hub qualification revision `d211137b0471b6534ccebef08677dcd947e0a6a4` has 24 files. Its legacy manifest has 1,086 paths, including PDB/object files in the binaries array; 1,065 referenced paths are absent. This legacy manifest cannot establish corpus completeness.
- Ninja upstream enables Release LTO after a global IPO setting. An initially empty dSYM passed `dwarfdump --verify`; a native source function count exposed the problem. The macOS recipe uses a custom Qualification build configuration, preserving the upstream source tree.
- Inherited SSDB O0 DWARF described optimized LevelDB dependency code, with no confirmed SSDB core functions. The SSDB recipe controls its actual CFLAGS and builds only the selected server and required libraries.
- Windows PE/PDB imports match CodeView GUID and Age, and preserve executable section bytes in isolated inputs. Native PDB coordinates retain section/offset evidence; they are not borrowed from DWARF names.

## Reproduce

Use Python 3.12 with `huggingface_hub`, `pyelftools` and `lief`; CMake; LLVM tools; Xcode for native macOS builds.
Set `PYTHONPATH` to a checkout of the pinned DecBench evaluator for the DWARF exporter.

```sh
python scripts/prepare_qualification_sources.py --root /path/to/work --plan targets/qualification-v2/pilot.json
python scripts/build_qualification_macos.py --root /path/to/work --plan targets/qualification-v2/pilot.json
python scripts/stage_qualification_v2.py --root /path/to/work --plan targets/qualification-v2/pilot.json --raw-manifest /path/to/frozen/raw/manifest.json --local-raw /path/to/raw/cpp-compiled
python scripts/import_qualification_msvc.py --root /path/to/work --plan targets/qualification-v2/pilot.json
python scripts/verify_qualification_inputs.py --root /path/to/work
python scripts/inspect_qualification_dwarf.py /path/to/status.json --stage /path/to/work/staged/qualification-v2 --sources /path/to/work/sources
python scripts/seal_qualification_v2.py --root /path/to/work --plan targets/qualification-v2/pilot.json
```

The existing Windows evidence importer expects the artifact layout of GitHub Actions run `38208011147`. The new Windows workflow is dispatch-only and was prepared for the four missing projects; it has not been executed in this staging request.
`build_qualification_windows.ps1` and `preprocess_qualification_msvc.py` require native Windows/MSVC. Preparing them on macOS is not an execution gate.
Docker recipes `build_qualification_tpt.sh` and `build_qualification_ssdb.sh` require the pinned revisions through environment variables and the workspace mounted at `/work`.

## Independent claims

- Successful builds do not establish runtime parity.
- LLVM debug verification does not establish project ownership or full debug completeness.
- File/hash checks do not establish metric readiness.
- No new Fission production changes or decompiler scores are part of this curation task.
