# DecBench C++ corpus qualification — 2026-09-16

This report records the corrected v2 corpus funnel run for C++ target discovery.

## Funnel

- GitHub C++ candidates collected: **500**
- Static eligibility after metadata/build-system checks: **339**
- Static preflight set: **200**
- O0 build qualification was initially run on the top 100, then expanded to the full preflight 200 after v1 was found to count CMake compiler/ABI probe binaries as false positives.
- Probe result records produced: **198 / 200**
- Tier A (`ELF + DWARF + .ii`, oracle-ready): **44**
- Tier B (`ELF + DWARF`, `.ii` replay/source-oracle follow-up required): **4**
- Tier C (adapter/build work required): **147**
- Tier D (rejected): **3**
- Final build-qualified shortlist (A+B): **48**

## Qualification v2 correction

The v2 probe excludes toolchain-generated artifacts such as CMake `CompilerId*`, `CMakeDetermineCompilerABI`, `CMakeScratch`, Meson private/log artifacts, and `conftest`. A Tier A pass therefore requires a real project-linked ELF with DWARF plus non-toolchain preprocessed `.ii` output.

## Incomplete probes

Two members of the 200-repository preflight set did not emit a result JSON and are kept separate from rejected targets:

- `WasmEdge/WasmEdge`
- `raulmur/ORB_SLAM2`

## Tier B follow-up

These four built usable DWARF ELF artifacts but did not preserve qualifying `.ii` output in this generic probe:

- `linyacool/WebServer`
- `async-profiler/async-profiler`
- `chenshuo/muduo`
- `tiny-dnn/tiny-dnn`

The full ranked shortlist is in `final-48.csv`. Tier A should be used as the strict DecBench-style oracle-ready subset; Tier B is retained only as a near-ready follow-up pool.

## Workflow provenance

- Branch: `automation/cpp-corpus-funnel`
- Corrected first-half run: `35085121652`
- Completed first-half aggregation run: `35085714981`
- Second-half + combined aggregation run: `35085910610`

Individual matrix jobs are allowed to fail because build incompatibility is itself a qualification outcome. The combined artifact was still generated successfully.
