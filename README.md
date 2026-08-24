# DecBench C++ Target Qualification

> **Disclaimer:** Unofficial DecBench target-qualification workspace; not an official Noelo-Lab repository.

Artifact-backed qualification workspace for candidate C++ targets for a future
DecBench multi-language corpus.

This repository does **not** claim that every shortlisted project is benchmark-ready.
It records exact source pins, DecBench-shaped target configurations, runtime build
qualification, ground-truth/oracle checks, and C++ function-identity diagnostics.

The current state is:

- **3 GCC/DWARF targets** validated through DecBench's real compile path on both
  local aarch64 and GitHub-hosted x86_64 Linux;
- **Microsoft Detours v4.0.1** validated on a native Windows x86_64 MSVC/PDB path;
- **Microsoft DirectXTex may2026** validated on a native Windows x86_64 MSVC/PDB
  path after an artifact-backed PDB module-matcher fix;
- **WinSparkle v0.9.4** remains pending native MSVC/PDB runtime qualification;
- compact machine-readable summaries are committed so the conclusions do not
  depend on expiring GitHub Actions artifacts.

---

## Current status

| Target | Track | O0 | O2 | O2-noinline | Linked image | Ground truth | Current identity diagnostic | Status |
|---|---|---|---|---|---|---|---|---|
| **Snappy 1.2.2** | GCC / DWARF | PASS | PASS | PASS | `libsnappy.so.1.2.2` | DWARF + `.ii` | x86_64 project collision: 52.87% / 53.16% / 51.97% | **VALIDATED** |
| **double-conversion v3.3.1** | GCC / DWARF | PASS | PASS | PASS | `libdouble-conversion.so.3.3.0` | DWARF + `.ii` | x86_64 project collision: 7.87% / 15.58% / 8.06% | **VALIDATED** |
| **Ninja v1.13.1** | GCC / DWARF | PASS | PASS | PASS | `ninja` | DWARF + `.ii` | x86_64 project collision: 26.70% / 32.38% / 27.55% | **VALIDATED WITH CAVEATS** |
| **Microsoft Detours v4.0.1** | native MSVC / PDB | PASS | PASS | PASS | `withdll.exe` | PDB / CodeView | PDB raw-name diagnostic: 5.88% / 5.88% / 5.88% | **VALIDATED** |
| **Microsoft DirectXTex may2026** | native MSVC / PDB | PASS | PASS | PASS | `DirectXTex.dll` | PDB / CodeView | PDB raw-name diagnostic: 12.92% / 17.65% / 13.27% | **VALIDATED** |
| **WinSparkle v0.9.4** | native MSVC / PDB | — | — | — | expected `WinSparkle.dll` | PDB / CodeView | not measured | **PENDING** |

The three values in each row are ordered `O0 / O2 / O2-noinline`.

The GCC values are DecBench-aligned project-source `DW_AT_name` collision exposure.
The Detours and DirectXTex values are **separate PDB/CodeView raw-name diagnostics**
and must not be interpreted as numerically equivalent to the DWARF metric.

The aggregate report is [`results/summary.md`](results/summary.md).

---

## Validation tracks

### GCC / DWARF / `.ii`

Pinned DecBench revision:

```text
d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f
```

The three GCC targets were first qualified locally with the real DecBench compile
path inside the repository's `decbench-compile` Docker image, then independently
re-qualified on GitHub-hosted x86_64 Linux.

The DecBench-controlled modes are:

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

The x86_64 CI artifact records:

```text
workflow run: 32632337105
artifact id:  9491409143
artifact sha256:
60fef5ba7bb9a252e0d8155cd7b775a54679ed2ff4b92b2d6152e7e54f01ccc2
workflow commit:
3c48841470ed64370b4541a721c12fc1df430dd3
```

Environment from the artifact:

```text
Runner:           Ubuntu x86_64
Container arch:   x86_64
Compiler:         GCC/G++ 13.3.0
DecBench revision d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f
```

All **9 target/mode combinations** pass. Every entry has exactly one intended
linked image, no recorded compile errors, and the expected preprocessed unit count:

| Target | `.ii` units per mode | Linked images per mode |
|---|---:|---:|
| Snappy | 4 | 1 |
| double-conversion | 8 | 1 |
| Ninja | 33 | 1 |

The x86_64 producer audit also confirms `EM_X86_64`, the expected optimization
flags, and no `-flto`, `-fltrans`, `-fwpa`, or `-fwhole-program` markers in any of
the nine final binaries.

Compact evidence:

```text
results/evidence/x86_64/qualification-summary.json
```

### Native MSVC / PDB / CodeView

The Windows track uses native Visual Studio `cl.exe`/`link.exe`, PE validation via
`llvm-readobj`, and linked-PDB analysis via `llvm-pdbutil`.

The generic PDB analyzer:

- verifies `IMAGE_FILE_MACHINE_AMD64`;
- dumps PDB summary, module/file provenance, and module symbols;
- restricts project ownership to object names derived from selected source roots;
- checks project `S_COMPILE3` records and rejects selected LTCG compilands;
- extracts project-owned procedure records;
- records raw PDB-name and leaf-name collision diagnostics.

`FRAMEPROC OptimizedForSpeed` counts are diagnostic only and are not used as the
optimization oracle.

#### Detours v4.0.1

```text
commit: e4bfd6b03e50de46b47abfbd1e46b384f0c5f833
image:  withdll.exe
```

Validated modes:

```text
O0:          /Od /Ob0 /Zi
O2:          /O2 /Zi
O2-noinline: /O2 /Ob0 /Zi
link:        /DEBUG:FULL /INCREMENTAL:NO /SUBSYSTEM:CONSOLE
```

All three modes contain **5 selected `S_COMPILE3` records** and **0 selected
LTCG-marked `S_COMPILE3` records**.

Artifact-derived Detours procedure diagnostic, identical across all three modes:

```text
Detours-owned procedure records: 136
unique raw PDB names:            132
collision groups:                  4
collision addresses:               8
raw-name collision rate:        5.88%
```

Compact evidence:

```text
results/evidence/msvc/detours/qualification-summary.json
```

Detailed report: [`results/detours.md`](results/detours.md)

#### DirectXTex may2026

```text
commit:          4feb3e11a020f35b796fc769a74216a555d4f5ef
image:           DirectXTex.dll
workflow run:    32684847948
workflow commit: 040e7dfc3a08ed94179b3a15746296d8be3d0dbe
runner image:    win25-vs2026
image version:   20260818.207.1
```

Validated modes:

```text
O0:          /Od /Ob0 /Zi /GL-
O2:          /O2 /Zi /GL-
O2-noinline: /O2 /Ob0 /Zi /GL-
link:        /DEBUG:FULL /INCREMENTAL:NO /LTCG:OFF
```

Per-mode artifacts:

| Mode | Artifact id | SHA-256 |
|---|---:|---|
| O0 | `9505320922` | `dd6fadd530a765a8ab5e38c1fd31bce0d3481805272ca7acd59a40e5dabab8c5` |
| O2 | `9505325453` | `1b1ad3fa76324aa577bb2b8f29adac27d011e3b84111b3540c0b1cd281ce5d62` |
| O2-noinline | `9505325181` | `8448cf1c351a373d1b53f385705c7928e97eb96625ad8fff1dcb8d92cb5381c5` |

The previous DirectXTex failure was **not** a build failure. The DLL and PDB were
already produced; project ownership failed because the generic matcher was looking
for two literal Windows backslashes before an object-name suffix.

The raw artifact shows CMake/Ninja PDB module names such as:

```text
D:\a\Decbench_SampleSet\Decbench_SampleSet\msvc-evidence\directxtex\O0\build-tree\CMakeFiles\DirectXTex.dir\DirectXTex\BC.cpp.obj
```

Commit `7f227d52ea9fdc7295dd7560f3f0827417d2938c` corrected the suffix check to one
Windows path separator. The project-ownership gate remains enabled; CRT, Windows
SDK, and unrelated vendor modules stay outside the DirectXTex source-derived object
set.

All three modes pass:

| Gate / diagnostic | O0 | O2 | O2-noinline |
|---|---:|---:|---:|
| AMD64 PE | PASS | PASS | PASS |
| Project source files considered | 21 | 21 | 21 |
| Selected project compilands | 17 | 17 | 17 |
| Selected `S_COMPILE3` records | 17 | 17 | 17 |
| Selected LTCG `S_COMPILE3` records | 0 | 0 | 0 |
| Project procedure records | 766 | 221 | 746 |
| Unique raw PDB names | 705 | 201 | 685 |
| Collision groups | 38 | 19 | 38 |
| Collision addresses | 99 | 39 | 99 |
| Raw PDB-name collision diagnostic | 12.92% | 17.65% | 13.27% |
| Leaf-name heuristic | 41.25% | 27.60% | 41.15% |

Compact evidence:

```text
results/evidence/msvc/directxtex/qualification-summary.json
```

Detailed report: [`results/directxtex.md`](results/directxtex.md)

---

## Why successful compilation is not enough for C++

DecBench's experimental C++ path has a function-identity problem: multiple concrete
C++ functions can share the same unqualified `DW_AT_name`.

Typical causes include overloads, methods with the same name in unrelated classes,
const/non-const pairs, constructor/destructor variants, templates, and ABI-specific
variants.

A useful GCC/DWARF target therefore needs more than a successful build:

1. all requested optimization modes build;
2. an intended linked image is selected;
3. preprocessed `.ii` translation units are preserved;
4. usable DWARF exists;
5. optimization is controlled by the benchmark rather than an upstream Release/LTO
   preset;
6. source ownership is restricted to DecBench's project translation-unit model;
7. short-name collision exposure is measured and preserved as evidence.

For native MSVC/PDB targets, the analogous gate is PE/PDB pairing, CodeView
source/compiland provenance, controlled MSVC optimization flags, LTCG auditing,
procedure extraction, and a clearly labelled PDB identity diagnostic.

---

## GCC collision methodology

[`scripts/measure_collisions.py`](scripts/measure_collisions.py) mirrors the
relevant DecBench C++ ground-truth behavior for the current GCC targets.

Identity key:

```text
resolved DW_AT_name
```

For C++ out-of-line definitions, resolution follows `DW_AT_specification` and
`DW_AT_abstract_origin`. Demangled linkage names are retained only for diagnosis.

Project scope is based on the compiled `.i`/`.ii` translation-unit stems and each
function's resolved `DW_AT_decl_file` basename, including DecBench's `-stem` /
`_stem` fallback behavior.

Metric:

```text
collision_rate = project-source addresses belonging to duplicated names
                 -----------------------------------------------------
                 all project-source function addresses
```

The broader raw metric is also preserved, but it includes concrete template,
header, and standard-library bodies that are not part of DecBench's project-source
oracle.

---

## x86_64 versus aarch64

The x86_64 requalification removes the previous "aarch64-only" limitation and also
shows why architecture-specific revalidation matters.

Snappy and double-conversion reproduce the local aarch64 project counts and
collision rates exactly. Ninja differs materially under optimization:

| Ninja mode | aarch64 project funcs / collision | x86_64 project funcs / collision |
|---|---:|---:|
| O0 | 412 / 26.70% | 412 / 26.70% |
| O2 | 355 / 30.42% | 210 / 32.38% |
| O2-noinline | 412 / 26.70% | 265 / 27.55% |

The x86_64 producer audit excludes LTO as the cause of this difference. The
remaining change is consistent with architecture/backend-dependent code generation,
inlining, and emitted-function selection.

---

# Qualified GCC / DWARF targets

## 1. Google Snappy 1.2.2

```text
commit: 6af9287fbdb913f0794d0148c6aa43b58e63c8e3
role:   compact compression/library collision-stress target
```

x86_64 project collision exposure:

```text
O0          157 funcs / 52.87%
O2           79 funcs / 53.16%
O2-noinline 152 funcs / 51.97%
```

Detailed report: [`results/snappy.md`](results/snappy.md)

## 2. Google double-conversion v3.3.1

```text
commit: ae0dbfeb9744efd216c95b30555049d75d47116a
role:   numeric / floating-point / algorithmic baseline
```

x86_64 project collision exposure:

```text
O0          127 funcs /  7.87%
O2           77 funcs / 15.58%
O2-noinline 124 funcs /  8.06%
```

Detailed report: [`results/double-conversion.md`](results/double-conversion.md)

## 3. Ninja v1.13.1

```text
commit: 79feac0f3e3bc9da9effc586cd5fea41e7550051
role:   real system/tooling executable
```

x86_64 project collision exposure:

```text
O0          412 funcs / 26.70%
O2          210 funcs / 32.38%
O2-noinline 265 funcs / 27.55%
```

Detailed report: [`results/ninja.md`](results/ninja.md)

---

# Windows / MSVC / PDB targets

## 4. Microsoft Detours v4.0.1 — validated

The selected linked image is the upstream `withdll.cpp` sample manually linked
against the upstream Detours static library so benchmark flags stay explicit.

The result is target/oracle qualification, not a claim that DecBench's existing
DWARF scorer can consume PDBs unchanged.

Detailed report: [`results/detours.md`](results/detours.md)

## 5. Microsoft DirectXTex may2026 — validated

```text
commit: 4feb3e11a020f35b796fc769a74216a555d4f5ef
role:   Windows graphics / image-processing / rich-C++ stress candidate
```

DirectXTex now has native x86_64 MSVC build, PE/PDB, project-compiland, non-LTCG,
procedure, and PDB identity evidence for all three optimization modes.

Detailed report: [`results/directxtex.md`](results/directxtex.md)

## 6. WinSparkle v0.9.4 — pending

```text
commit: a8986caf620262f7d4581b241436ceaa0cc9370f
role:   Windows updater / networking / threading / UI-oriented C++
```

WinSparkle still needs a completed native MSBuild/MSVC three-mode run with explicit
WholeProgramOptimization/LTCG control, exact DLL/PDB pairing, vendor-compiland
filtering, and PDB identity measurement before it can be marked validated.

Detailed report: [`results/winsparkle.md`](results/winsparkle.md)

---

## Exact target pins

| Target | Stable tag/release | Resolved commit |
|---|---|---|
| Snappy | `1.2.2` | `6af9287fbdb913f0794d0148c6aa43b58e63c8e3` |
| double-conversion | `v3.3.1` | `ae0dbfeb9744efd216c95b30555049d75d47116a` |
| Ninja | `v1.13.1` | `79feac0f3e3bc9da9effc586cd5fea41e7550051` |
| Detours | `v4.0.1` | `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833` |
| DirectXTex | `may2026` | `4feb3e11a020f35b796fc769a74216a555d4f5ef` |
| WinSparkle | `v0.9.4` | `a8986caf620262f7d4581b241436ceaa0cc9370f` |

---

## Evidence inventory

```text
# Local aarch64 GCC qualification
results/evidence/environment.txt
results/evidence/compile_report.json
results/evidence/collision/*.json

# GitHub Actions x86_64 GCC qualification
results/evidence/x86_64/qualification-summary.json
.github/workflows/cpp-x86_64-validation.yml

# Native MSVC/PDB Detours qualification
results/evidence/msvc/detours/qualification-summary.json
.github/workflows/msvc-detours-validation.yml
scripts/validate_detours_msvc.ps1

# Native MSVC/PDB DirectXTex qualification
results/evidence/msvc/directxtex/qualification-summary.json
.github/workflows/msvc-directxtex-validation.yml
scripts/validate_directxtex_msvc.ps1

# Shared native MSVC/PDB analyzer
scripts/qualify_msvc_pdb.ps1
```

Large ELF/PE/PDB/build-tree artifacts are intentionally not committed. Git keeps
compact machine-readable summaries, while the CI workflows remain capable of
regenerating the full runtime artifacts.

---

## Known limitations

### Target qualification is not a complete benchmark run

These results validate build/oracle suitability and function-identity exposure.
They do **not** claim that GED, type matching, byte matching, and every decompiler
have been run end-to-end on every function in these new targets.

### C++ identity remains a benchmark-design issue

The GCC collision metric quantifies the current unqualified `DW_AT_name` problem;
it does not solve it. A future qualified/signature-aware identity model may change
both target difficulty and appropriate corpus composition.

### PDB and DWARF identity metrics are different

Detours and DirectXTex PDB values are procedure-name diagnostics over project-owned
linked compilands. They are deliberately **not** presented as apples-to-apples
equivalents of the GCC/DWARF project-source collision metric.

### Detours validates one concrete linked sample

The core Detours library is static. `withdll.exe` pulls only the objects actually
needed by that sample, so unreferenced core object files are outside this linked
PDB's measured procedure set.

### One Windows target still lacks completed runtime evidence

WinSparkle remains a candidate, not a validated target, until its native MSVC/PDB
workflow completes and the resulting artifacts are audited.

---

## Current recommendation for DecBench

For an initial upstream discussion, the strongest evidence-backed candidates are:

- **double-conversion v3.3.1** — clean GCC/DWARF numerical baseline;
- **Ninja v1.13.1** — real executable with moderate identity pressure and observed
  architecture sensitivity;
- **Snappy 1.2.2** — compact collision-heavy GCC/DWARF stress/control case;
- **Microsoft Detours v4.0.1** — native Windows/MSVC/PDB systems target with actual
  PE/PDB qualification evidence;
- **Microsoft DirectXTex may2026** — native Windows graphics/image-processing DLL
  with actual three-mode PE/PDB qualification evidence.

WinSparkle should remain a second-stage Windows shortlist item until equivalent
runtime evidence exists.

This repository is best treated as **candidate research and qualification evidence**,
not as an implicit request to merge every target. A sensible upstream sequence is
to share the findings, let maintainers choose the desired corpus slice, and then
prepare a focused DecBench PR containing only the selected targets and the minimal
integration work they require.
