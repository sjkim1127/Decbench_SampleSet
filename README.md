# DecBench C++ Target Qualification

> **Disclaimer:** Unofficial DecBench target-qualification workspace; not an official Noelo-Lab repository.

Artifact-backed qualification workspace for candidate C++ targets for a future
DecBench multi-language corpus.

This repository does **not** claim that all six candidates are benchmark-ready.
It records a deliberately small target shortlist, the exact release pins used,
DecBench-shaped build configurations, local validation evidence, and the current
C++ function-identity collision profile observed under DecBench's own DWARF
source-function model.

The current state is:

- **3 GCC/DWARF targets runtime-validated** through DecBench's real compile path;
- **3 Windows/MSVC/PDB targets statically qualified but runtime-blocked** because
  the validation host does not currently provide Wine/MSVC/Windows SDK tooling;
- all GCC validation results are backed by committed machine-readable evidence.

The workspace is intended as a research/engineering handoff: a maintainer should
be able to see what was actually executed, what was only reviewed statically,
which measurements are trustworthy, and what remains before upstream inclusion.

---

## Current status

| Target | Track | O0 | O2 | O2-noinline | Linked image | Ground truth | Project collision rate | Status |
|---|---|---|---|---|---|---|---|---|
| **Snappy 1.2.2** | GCC / DWARF | PASS | PASS | PASS | `libsnappy.so.1.2.2` | DWARF + `.ii` | 52.87% / 53.16% / 51.97% | **VALIDATED** |
| **double-conversion v3.3.1** | GCC / DWARF | PASS | PASS | PASS | `libdouble-conversion.so.3.3.0` | DWARF + `.ii` | 7.87% / 15.58% / 8.06% | **VALIDATED** |
| **Ninja v1.13.1** | GCC / DWARF | PASS | PASS | PASS | `ninja` | DWARF + `.ii` | 26.70% / 30.42% / 26.70% | **VALIDATED WITH CAVEATS** |
| **Microsoft Detours v4.0.1** | MSVC / PDB | — | — | — | expected PE sample/tool | PDB / CodeView | not measured | **BLOCKED** |
| **Microsoft DirectXTex may2026** | MSVC / PDB | — | — | — | expected `DirectXTex.dll` | PDB / CodeView | not measured | **BLOCKED** |
| **WinSparkle v0.9.4** | MSVC / PDB | — | — | — | expected `WinSparkle.dll` | PDB / CodeView | not measured | **BLOCKED** |

Collision-rate order above is `O0 / O2 / O2-noinline` and refers to the
**project-source function set**, not every concrete subprogram emitted into the
binary.

The authoritative aggregate report is [`results/summary.md`](results/summary.md).
Raw compile/collision evidence is preserved under [`results/evidence/`](results/evidence/).

---

## What was actually executed

The GCC/DWARF candidates were not accepted from source inspection alone. They were
compiled locally through the actual DecBench compile workflow using the pinned
DecBench revision:

```text
d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f
```

Validation environment:

```text
Host OS:        macOS 26.5.1 arm64
Docker:         29.4.0
Container:      Ubuntu 24.04 aarch64
Compiler:       GCC/G++ 13.3.0
pyelftools:     0.33
DecBench image: decbench-compile, built from docker/compile.Dockerfile
```

The committed environment record is
[`results/evidence/environment.txt`](results/evidence/environment.txt).

The compile command used the real DecBench driver rather than a parallel custom
build harness:

```bash
docker run --rm \
  -v "$PWD":/workspace \
  -w /workspace \
  -e PYTHONPATH=/workspace \
  decbench-compile \
  python3 scripts/compile_all.py results/cpp_local 3 \
  snappy double-conversion ninja
```

All **9 GCC target/mode combinations** completed successfully. The final compile
report records one intended linked binary for every mode and no compile errors:

```text
results/evidence/compile_report.json
```

The three optimization modes are:

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

The validation also checked `DW_AT_producer` metadata for unexpected LTO/IPO,
profile-guided optimization, or whole-program optimization. None was observed in
the validated GCC binaries.

---

## Why C++ target qualification needs more than a successful build

DecBench's experimental C++ path has a specific identity problem: multiple C++
functions can share the same unqualified `DW_AT_name`.

Examples include:

- overloads with different parameter types;
- methods with the same name in unrelated classes;
- const/non-const overload pairs;
- constructor variants;
- ABI destructor variants such as GCC D1/D2 forms;
- template specializations that collapse to the same visible name depending on
  the DWARF representation.

A target can therefore compile perfectly while still being a poor fit for the
current benchmark identity model.

For that reason, the qualification gate used here is:

1. build all requested optimization modes;
2. collect at least one intended linked image per mode;
3. preserve preprocessed `.ii` translation units;
4. confirm usable DWARF;
5. confirm DecBench controls optimization rather than inheriting an upstream
   Release/LTO preset;
6. measure short-name collision exposure on DecBench's own project-source function
   scope;
7. preserve the measurement as machine-readable evidence.

---

## Collision measurement: DecBench-aligned methodology

[`scripts/measure_collisions.py`](scripts/measure_collisions.py) mirrors the
relevant DecBench ground-truth behavior for the current validated targets.

### Identity key

Each concrete `DW_TAG_subprogram` is keyed by resolved `DW_AT_name`.

For C++ out-of-line definitions, the resolver follows the same
`DW_AT_specification` / `DW_AT_abstract_origin` chain used by DecBench's
`utils.binfmt.die_attr_owner()` logic.

Demangled `DW_AT_linkage_name` is retained only for diagnostics and human review;
it is **not** used as the collision identity key.

### Project-source scope

DecBench does not treat every concrete function emitted into an ELF as a project
source function. It uses the preprocessed translation units as the source scope.

The measurement therefore:

1. collects `*.i` / `*.ii` translation-unit stems from the compiled directory;
2. normalizes source extensions with DecBench-style `strip_source_ext()` logic;
3. resolves each function's `DW_AT_decl_file`;
4. compares the declaration basename stem against the compiled source-stem index;
5. applies DecBench's object-prefix fallback (`-stem` / `_stem`) when needed.

This deliberately excludes header-defined helpers and standard-library/template
bodies that are concrete in the final binary but are outside the benchmark's own
translation-unit function set.

### Metric

```text
collision_rate = number of project-source addresses belonging to a duplicated name
                 ---------------------------------------------------------------
                 total project-source function addresses
```

Both **project** and **raw** metrics are preserved. The raw metric is useful for
understanding emitted binary complexity; the project metric is the relevant one
for current DecBench function identity.

### Evidence files

Nine collision reports are committed:

```text
results/evidence/collision/snappy_O0.json
results/evidence/collision/snappy_O2.json
results/evidence/collision/snappy_O2-noinline.json

results/evidence/collision/double-conversion_O0.json
results/evidence/collision/double-conversion_O2.json
results/evidence/collision/double-conversion_O2-noinline.json

results/evidence/collision/ninja_O0.json
results/evidence/collision/ninja_O2.json
results/evidence/collision/ninja_O2-noinline.json
```

Each report contains the selected source stems, linked image path, address counts,
name counts, collision groups, collision addresses, rates, and representative
qualified/demangled names.

---

# GCC / DWARF validated targets

## 1. Google Snappy 1.2.2

```text
upstream: google/snappy
release:  1.2.2
commit:   6af9287fbdb913f0794d0148c6aa43b58e63c8e3
config:   targets/snappy.toml
role:     small compression/library baseline
```

Snappy is intentionally retained even though its current name-collision rate is
high. It is a small, dependency-light real C++ library with a straightforward
CMake build and a compact source surface, which makes the identity problem easy to
inspect.

### Build result

| Mode | Linked image | `.ii` units | Project functions | Project collision |
|---|---|---:|---:|---:|
| O0 | `libsnappy.so.1.2.2` | 4 | 157 | **52.87%** |
| O2 | `libsnappy.so.1.2.2` | 4 | 79 | **53.16%** |
| O2-noinline | `libsnappy.so.1.2.2` | 4 | 152 | **51.97%** |

The four source translation units are:

```text
snappy.cc
snappy-c.cc
snappy-sinksource.cc
snappy-stubs-internal.cc
```

### What the collisions show

Snappy exposes several classes of ambiguity that are directly relevant to
DecBench's current C++ identity model:

- overloaded public APIs such as `Compress`, `Uncompress`, and `RawCompress`;
- repeated interface method names across source/sink implementations;
- GCC destructor variants that produce distinct concrete addresses under the same
  visible `DW_AT_name`.

The rate is stable across all three modes, so this is not merely an O0 template
noise artifact. Snappy is therefore useful as a **small collision-stress/control
target**, not as the cleanest target.

Detailed report: [`results/snappy.md`](results/snappy.md)

---

## 2. Google double-conversion v3.3.1

```text
upstream: google/double-conversion
release:  v3.3.1
commit:   ae0dbfeb9744efd216c95b30555049d75d47116a
config:   targets/double-conversion.toml
role:     numeric / floating-point / algorithmic baseline
```

double-conversion is the cleanest currently validated target in this shortlist.
It has a compact source tree, little dependency burden, no broad virtual UI-style
hierarchy, and a workload that is substantially different from Snappy.

### Build result

| Mode | Linked image | `.ii` units | Project functions | Project collision |
|---|---|---:|---:|---:|
| O0 | `libdouble-conversion.so.3.3.0` | 8 | 127 | **7.87%** |
| O2 | `libdouble-conversion.so.3.3.0` | 8 | 77 | **15.58%** |
| O2-noinline | `libdouble-conversion.so.3.3.0` | 8 | 124 | **8.06%** |

The project translation units are:

```text
bignum-dtoa.cc
bignum.cc
cached-powers.cc
double-to-string.cc
fast-dtoa.cc
fixed-dtoa.cc
string-to-double.cc
strtod.cc
```

### Why the final rate is much lower than the raw rate

Header-defined helper functions can be emitted into multiple object files. If every
concrete DWARF subprogram is counted, these multi-TU helpers create many duplicate
names. DecBench's project-source oracle does not treat those header bodies as source
translation-unit functions, so the source-stem filter removes them from the
project metric.

Final project collision exposure is only **8–16%**, making double-conversion a
strong clean baseline for an initial C++ corpus.

Detailed report:
[`results/double-conversion.md`](results/double-conversion.md)

---

## 3. Ninja v1.13.1

```text
upstream: ninja-build/ninja
release:  v1.13.1
commit:   79feac0f3e3bc9da9effc586cd5fea41e7550051
config:   targets/ninja.toml
role:     system / tooling executable
```

Ninja supplies a different workload class from the two libraries: parser logic,
dependency graphs, state/log handling, filesystem operations, subprocess control,
and build scheduling in a real executable.

### Build result

| Mode | Linked image | `.ii` units | Project functions | Project collision |
|---|---|---:|---:|---:|
| O0 | `ninja` | 33 | 412 | **26.70%** |
| O2 | `ninja` | 33 | 355 | **30.42%** |
| O2-noinline | `ninja` | 33 | 412 | **26.70%** |

### LTO / build-system control

Ninja's upstream Release configuration can enable IPO/LTO. The target therefore:

- leaves `CMAKE_BUILD_TYPE` empty;
- injects DecBench's `CFLAGS` into C++ compilation;
- builds only the `ninja` target;
- removes CMake internal probe directories after the build.

`DW_AT_producer` confirms that the final O2 binary uses the expected `-O2` path
without `-flto` or whole-program optimization.

### CMake `boo` artifact

An early validation run exposed a CMake internal `_CMakeLTOTest-CXX` test binary
named `boo`. It was not a real benchmark output. The target config was corrected,
and the final compile evidence now records exactly **one linked image** for Ninja
in every mode.

### Collision profile

Ninja's project collision exposure is 27–30%. Examples include repeated method
names such as `LoadDyndeps`, `Dump`, `AddTarget`, `Parse`, `Load`, `Reset`, and
other class-local operations that collapse when only the unqualified
`DW_AT_name` is retained.

At O0 and O2-noinline the **raw** binary contains thousands of concrete libstdc++
template functions, producing raw collision rates of roughly 66–71%. DecBench's
source-stem filter correctly removes that emitted-library noise from the project
metric.

Detailed report: [`results/ninja.md`](results/ninja.md)

---

# Windows / MSVC / PDB shortlist

The Windows targets were chosen for the native MSVC/PDB direction, not for the
current GCC/DWARF production path.

DecBench PR #36 has already demonstrated the broader feasibility of real MSVC
`cl.exe` under Wine with PE + PDB output, but this local host did not have that
toolchain available during qualification.

Therefore the Windows status is intentionally **BLOCKED**, not FAIL and not PASS.
Only source/build/config review has been completed here.

## 4. Microsoft Detours v4.0.1

```text
upstream: microsoft/Detours
release:  v4.0.1
commit:   e4bfd6b03e50de46b47abfbd1e46b384f0c5f833
config:   targets/windows/detours.toml
role:     Windows instrumentation / PE manipulation / systems code
```

Why it remains on the shortlist:

- native Windows/Win32 project;
- highly characteristic instrumentation and PE-manipulation code;
- API names such as `DetourAttach` and `DetourFindFunction` are relatively
  distinctive compared with GUI-heavy class hierarchies;
- upstream sample/tools provide linked PE images even though the core Detours
  library is static.

Runtime qualification still needs:

```text
cl.exe + link.exe + nmake
Windows SDK
PE/PDB pairing
controlled /Od / /O2 / /O2 /Ob0 modes
PDB source/compiland filtering
PDB short-name collision measurement
```

Detailed report: [`results/detours.md`](results/detours.md)

---

## 5. Microsoft DirectXTex may2026

```text
upstream: microsoft/DirectXTex
release:  may2026
commit:   4feb3e11a020f35b796fc769a74216a555d4f5ef
config:   targets/windows/directxtex.toml
role:     Windows graphics / image-processing / rich-C++ stress target
```

DirectXTex was selected as the Windows computation-heavy target. It covers texture
formats, conversion, BC compression, DDS/WIC handling, mipmap generation, resize,
and related vector-heavy image processing.

It is explicitly a **stress candidate** for C++ identity because the API contains
many overload families. That risk is documented but must not be converted into a
number until a real MSVC/PDB build is measured.

Runtime qualification requires a working MSVC/CMake Windows environment and
actual PDB-derived collision evidence.

Detailed report: [`results/directxtex.md`](results/directxtex.md)

---

## 6. WinSparkle v0.9.4

```text
upstream: vslavik/winsparkle
release:  v0.9.4
commit:   a8986caf620262f7d4581b241436ceaa0cc9370f
config:   targets/windows/winsparkle.toml
role:     Windows updater / networking / threading / UI-oriented C++
```

WinSparkle adds an application-library style workload that differs from both
Detours and DirectXTex. Its project code covers updater behavior, networking,
signature verification, settings/registry handling, Win32 UI, and worker-thread
coordination.

Important runtime checks remain:

- Visual Studio/MSBuild availability;
- disabling/overriding upstream WholeProgramOptimization/LTCG;
- validating `/Od`, `/O2`, and `/O2 /Ob0` mappings;
- pairing the exact DLL with its PDB;
- excluding third-party compilands from the project ground-truth set;
- measuring repeated virtual names such as thread/update-check methods from the
  actual PDB.

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

Pins are deliberate: this workspace avoids HEAD-based target definitions so later
results can be reproduced against the same upstream source snapshot.

---

## Repository layout

```text
README.md

# DecBench-shaped GCC target configs
targets/
  snappy.toml
  double-conversion.toml
  ninja.toml

# Experimental Windows/MSVC qualification metadata
targets/windows/
  detours.toml
  directxtex.toml
  winsparkle.toml

# Validation procedure and record format
docs/
  local-validation.md
  result-template.md

# Collision analyzer
scripts/
  measure_collisions.py

# Human-readable target reports
results/
  summary.md
  snappy.md
  double-conversion.md
  ninja.md
  detours.md
  directxtex.md
  winsparkle.md

# Machine-readable evidence
results/evidence/
  environment.txt
  compile_report.json
  collision/
    snappy_O0.json
    snappy_O2.json
    snappy_O2-noinline.json
    double-conversion_O0.json
    double-conversion_O2.json
    double-conversion_O2-noinline.json
    ninja_O0.json
    ninja_O2.json
    ninja_O2-noinline.json
```

Large ELF/PDB/build-tree artifacts are intentionally not committed. The repository
keeps the target definitions, environment record, compile summary, and collision
measurements required to audit the qualification without turning Git into a binary
artifact store.

---

## Reproducing the GCC qualification

See [`docs/local-validation.md`](docs/local-validation.md) for the complete
procedure. The intended workflow is:

1. check out the pinned DecBench revision;
2. build DecBench's `docker/compile.Dockerfile` image;
3. copy/use the target TOMLs from this repository;
4. execute DecBench's real `scripts/compile_all.py` path for all three modes;
5. verify linked image count and `.ii` preservation;
6. inspect DWARF/producer flags;
7. run `scripts/measure_collisions.py` against each compiled target/mode;
8. compare the generated JSON with `results/evidence/collision/`.

A validation should be marked **PASS** only when execution evidence exists. Source
inspection alone is not enough.

---

## Interpretation of the current GCC results

The three validated targets occupy deliberately different points on the current
identity spectrum:

```text
double-conversion   8–16%   relatively clean C++ baseline
Ninja              27–30%   real executable / moderate identity pressure
Snappy             52–53%   compact but collision-heavy stress/control case
```

This is useful for corpus construction. A first multi-language C++ slice should not
contain only easy targets or only pathological ones.

The results also demonstrate why qualified C++ identity matters. Even ordinary,
well-maintained C++ projects expose significant ambiguity when namespaces, classes,
parameter types, and ABI distinctions are collapsed to an unqualified name.

---

## Known limitations

### Architecture

The runtime evidence in this repository is **aarch64**, not x86-64. Function counts,
inlining decisions, SIMD paths, emitted templates, and collision rates can change
with architecture/toolchain differences.

Before publishing a final corpus on x86-64, repeat the same validation there.

### This is target qualification, not a complete benchmark run

The GCC work validates target build/oracle suitability and measures current
short-name identity exposure. It does not claim that GED/type_match/byte_match have
all been run end-to-end for every function of these new projects.

### Windows runtime evidence is intentionally absent

Detours, DirectXTex, and WinSparkle have not been promoted to PASS. Their config and
source/build shapes were reviewed, but PE/PDB runtime evidence must come from a
real MSVC environment.

### C++ identity remains a benchmark design issue

The collision metric quantifies the current `DW_AT_name` problem; it does not solve
it. A future qualified/signature-aware identity scheme may change which targets are
considered easy or hard and may reduce the need for collision-driven filtering.

---

## Current recommendation for DecBench

For an initial discussion/upstream handoff:

### Recommend now

- **double-conversion v3.3.1** — strongest clean GCC/DWARF candidate;
- **Ninja v1.13.1** — valuable real executable with quantified caveats;
- **Snappy 1.2.2** — useful small collision-heavy baseline/stress case.

### Keep as Windows/MSVC shortlist, not yet confirmed

- **Microsoft Detours v4.0.1**;
- **Microsoft DirectXTex may2026**;
- **WinSparkle v0.9.4**.

The Windows candidates should remain marked **BLOCKED** until they are built with
real MSVC, paired with PDBs, and measured using PDB-based source/compiland ownership
and name-collision logic.

---

## Upstream handoff posture

This repository is best treated as **candidate research and qualification evidence**,
not as an implicit request to merge all six targets immediately.

A sensible upstream sequence is:

1. share the validated target findings in the existing DecBench C++ discussion;
2. let maintainers choose which targets fit the next corpus;
3. open a focused DecBench PR containing only the selected project configs and any
   minimal integration changes requested by the maintainers;
4. keep the broader qualification evidence here for reproducibility and review.

That separates the research result (which targets look useful and why) from the
upstream implementation decision (which targets DecBench should actually ship).

---

## Historical selection note

The Powder Toy was considered earlier and intentionally removed from the initial
shortlist. Its dependency footprint, UI-heavy inheritance, repeated callback names,
and build/optimization behavior made it a less controlled first target than the
current set. It may still be useful later as a larger C++ stress corpus once the
function-identity model is stronger.
