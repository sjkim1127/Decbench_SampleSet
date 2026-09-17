# DecBench C++ Target Qualification

> **Disclaimer:** Unofficial DecBench target-qualification workspace; not an official Noelo-Lab repository.

Artifact-backed qualification workspace for candidate C++ targets for a future
DecBench multi-language corpus.

This repository deliberately separates:

- successful project builds;
- target/oracle qualification;
- function-identity diagnostics and validation;
- corpus-scale candidate discovery;
- full end-to-end DecBench scoring.

A target marked as qualified here has artifact-backed build/oracle evidence. It
does **not** mean GED, type matching, byte matching, and every decompiler have
already been run end-to-end on that target.

## Current status

The workspace now has three complementary tracks:

1. an original six-target, deeply inspected reference set across GCC/DWARF and
   native MSVC/PDB;
2. a corpus-scale Linux/GCC discovery funnel used to search hundreds of C++
   repositories and identify a much larger source-backed candidate pool;
3. a C++ function-identity validation track in the DecBench fork, exercising the
   collision-safe identity model across real decompilers, optimization levels,
   ARM/Thumb, serialization, and scoring behavior.

### Corpus-scale funnel

The corrected 2026-09-16 funnel produced:

| Stage | Count |
|---|---:|
| GitHub C++ repositories collected | **500** |
| Static eligibility checks passed | **339** |
| Selected for preflight | **200** |
| Build-probe result records produced | **198 / 200** |
| Tier A: project ELF + DWARF + qualifying `.ii` | **44** |
| Tier B: project ELF + DWARF; `.ii` follow-up required | **4** |
| Final build-qualified shortlist (A + B) | **48** |

Full report and ranked shortlist:

- [`results/cpp-corpus-2026-09-16/README.md`](results/cpp-corpus-2026-09-16/README.md)
- [`results/cpp-corpus-2026-09-16/final-48.csv`](results/cpp-corpus-2026-09-16/final-48.csv)

**Tier A** is the strict DecBench-style oracle-ready subset from this generic
probe: a real project-linked ELF with DWARF plus non-toolchain preprocessed `.ii`
output.

**Tier B** contains four near-ready projects that produced usable project ELF +
DWARF artifacts but need source/preprocessor replay work before they can be
considered equivalent to Tier A:

- `linyacool/WebServer`
- `async-profiler/async-profiler`
- `chenshuo/muduo`
- `tiny-dnn/tiny-dnn`

Two of the 200 preflight members did not emit a result JSON and remain explicitly
separate from rejected targets:

- `WasmEdge/WasmEdge`
- `raulmur/ORB_SLAM2`

### Qualification-v2 correction

The first generic build probe exposed an important false-positive class: CMake
compiler/ABI test binaries could be mistaken for project artifacts.

The corrected v2 qualification excludes toolchain-generated artifacts and paths
including:

- `CompilerId*`;
- `CMakeDetermineCompilerABI`;
- `CMakeScratch`;
- Meson private/log artifacts;
- `conftest`.

The 44 Tier A results above are from the corrected definition, not from the
initial loose probe.

### Function-identity validation

The target funnel exposed a separate benchmark correctness problem: C++ functions
cannot be keyed globally by unqualified source name. Overloads, repeated method
names, namespaces, templates, and ABI-generated variants can all produce distinct
concrete functions with the same `DW_AT_name`.

The current DecBench fork therefore uses a binary-global DWARF identity model:

```text
primary identity:  (binary, DWARF low_pc)
human name:        DW_AT_name
optional join key: DW_AT_linkage_name
storage key:       name                  if unique in the target universe
                   name@0x<low_pc>       if the source name is ambiguous
```

The implementation is under review as
[Noelo-Lab/decbench#91](https://github.com/Noelo-Lab/decbench/pull/91), on branch
[`fix/cpp-function-identity-clean`](https://github.com/sjkim1127/decbench/tree/fix/cpp-function-identity-clean).

The validation table below was measured against an earlier single-commit
candidate:

```text
d76561fbb7c32a80fd52aba551d990992bb2c0da
```

The branch under review carries roughly 990 lines more than that candidate — the
slice-invariance, end-to-end and ICF test work landed afterwards — so these
results describe the design, not that exact tree, and are being re-confirmed
against the PR head.

Validation performed against that design includes:

| Validation | Result |
|---|---|
| Real LevelDB 1.23 collision through **angr + Ghidra 12.0.4** | **PASS** |
| C++ fixture at **O0 / O2 / O2-noinline** | **PASS** |
| Real O2 inlined DWARF with `DW_TAG_inlined_subroutine` and abstract/specification references | **PASS** |
| ARM/Thumb with a real `gcc-arm-none-eabi` CI toolchain | **PASS** |
| JSON collision round-trip and legacy plain-name result loading | **PASS** |
| TOML collision-safe serialization | **PASS** |
| Partial-progress atomic pickle round-trip | **PASS** |
| Insertion-order determinism | **PASS** |
| GED abstention/shared-denominator regression | **PASS** |

The strongest cross-decompiler fixture currently uses the two LevelDB `Next`
functions:

```text
angr raw:      sub_4943c       sub_4e3f0
Ghidra raw:    FUN_0014943c    FUN_0014e3f0

canonical:
Next@0x4943c
Next@0x4e3f0
```

Both backends converge to the same canonical keys even though their recovered
raw names differ. This is the intended invariant: backend success and backend
naming do not define benchmark identity; the binary-global DWARF target universe
does.

A focused identity regression suite covering optimized DWARF, serialization,
backend relabeling, metrics, and progress recovery passed **28 / 28** tests in
CI. ARM/Thumb is exercised in a separate job with the actual cross compiler so
those tests do not silently degrade into skip-only coverage.

#### GED abstention policy

C++ source-CFG recovery can be ambiguous for some overloaded functions. Simply
removing those functions from one decompiler's denominator would make a system
look better by evaluating fewer hard functions.

The validated scoring path instead uses a shared measurable function universe for
headline aggregation. A fixture with normal functions plus ambiguous overloads
confirms that abstaining on the hard functions does not improve the aggregate
perfect-function percentage.

#### Same-address aliases / ICF

Address is intentionally the canonical binary identity primitive. That means
linker identical-code folding and other same-address aliases require an explicit
policy: multiple source descriptions that resolve to one machine-code address
cannot be treated as independent benchmark functions without introducing a
second identity dimension.

Current DWARF extraction deduplicates concrete identities by address, i.e. the
working policy is effectively **one binary address = one benchmark function**.
A real LLD `--icf=all` probe has been added to validate and make that policy
deterministic. This item is still under active validation and is **not** claimed
complete here.

#### PE / PDB scope

PE address normalization is also being exercised separately using real
MinGW-produced PE + DWARF binaries, where a backend RVA must be lifted by the PE
ImageBase to match the canonical DWARF address.

Native MSVC/PDB identity is a separate integration problem. The existing Windows
qualification data in this repository proves that native PE/PDB targets can be
built and inspected reproducibly, but the current DWARF function-identity patch
does not pretend to provide a PDB identity reader. That belongs in a follow-up
PDB-aware DecBench path.

---

## Original six-target reference set

Before the corpus-scale search, six targets were qualified much more deeply over
controlled optimization modes. They remain useful reference/stress targets for
validating future DecBench C++ support.

| Target | Track | O0 | O2 | O2-noinline | Linked image | Ground truth | Current identity diagnostic | Status |
|---|---|---|---|---|---|---|---|---|
| **Snappy 1.2.2** | GCC / DWARF | PASS | PASS | PASS | `libsnappy.so.1.2.2` | DWARF + `.ii` | project `DW_AT_name`: 52.87% / 53.16% / 51.97% | **VALIDATED** |
| **double-conversion v3.3.1** | GCC / DWARF | PASS | PASS | PASS | `libdouble-conversion.so.3.3.0` | DWARF + `.ii` | project `DW_AT_name`: 7.87% / 15.58% / 8.06% | **VALIDATED** |
| **Ninja v1.13.1** | GCC / DWARF | PASS | PASS | PASS | `ninja` | DWARF + `.ii` | project `DW_AT_name`: 26.70% / 32.38% / 27.55% | **VALIDATED WITH CAVEATS** |
| **Microsoft Detours v4.0.1** | native MSVC / PDB | PASS | PASS | PASS | `withdll.exe` | PDB / CodeView | PDB raw-name: 5.88% / 5.88% / 5.88% | **VALIDATED** |
| **Microsoft DirectXTex may2026** | native MSVC / PDB | PASS | PASS | PASS | `DirectXTex.dll` | PDB / CodeView | PDB raw-name: 12.92% / 17.65% / 13.27% | **VALIDATED** |
| **WinSparkle v0.9.4** | native MSVC / PDB | PASS | PASS | PASS | `WinSparkle.dll` | PDB / CodeView | PDB raw-name: 18.26% / 14.79% / 18.84% | **VALIDATED** |

Values are ordered `O0 / O2 / O2-noinline`.

The GCC values are DecBench-aligned project-source `DW_AT_name` collision
exposure. The MSVC values are separate PDB/CodeView procedure-name diagnostics
and must not be treated as numerically equivalent to the DWARF metric.

Detailed aggregate report: [`results/summary.md`](results/summary.md)

### Exact target pins

| Target | Stable tag/release | Resolved commit |
|---|---|---|
| Snappy | `1.2.2` | `6af9287fbdb913f0794d0148c6aa43b58e63c8e3` |
| double-conversion | `v3.3.1` | `ae0dbfeb9744efd216c95b30555049d75d47116a` |
| Ninja | `v1.13.1` | `79feac0f3e3bc9da9effc586cd5fea41e7550051` |
| Detours | `v4.0.1` | `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833` |
| DirectXTex | `may2026` | `4feb3e11a020f35b796fc769a74216a555d4f5ef` |
| WinSparkle | `v0.9.4` | `a8986caf620262f7d4581b241436ceaa0cc9370f` |

Pinned DecBench revision for the original GCC qualification path:

```text
d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f
```

---

## GCC / DWARF qualification model

The original GCC targets were qualified through DecBench's real compile path on
both local aarch64 and GitHub-hosted x86_64 Linux.

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

Qualification is stricter than successful compilation. The relevant evidence
includes:

- a real linked project ELF;
- usable DWARF;
- preserved `.ii` source units;
- controlled optimization and no LTO leakage;
- project-source ownership;
- function-identity collision diagnostics.

Original x86_64 evidence:

```text
workflow run: 32632337105
artifact id:  9491409143
compiler:     GCC/G++ 13.3.0
```

| Target | `.ii` units/mode | Project funcs O0/O2/O2-noinline | Collision O0/O2/O2-noinline |
|---|---:|---|---|
| Snappy | 4 | 157 / 79 / 152 | 52.87% / 53.16% / 51.97% |
| double-conversion | 8 | 127 / 77 / 124 | 7.87% / 15.58% / 8.06% |
| Ninja | 33 | 412 / 210 / 265 | 26.70% / 32.38% / 27.55% |

Detailed reports:

- [`results/snappy.md`](results/snappy.md)
- [`results/double-conversion.md`](results/double-conversion.md)
- [`results/ninja.md`](results/ninja.md)

---

## Native MSVC / PDB / CodeView qualification

The Windows track uses native Visual Studio/MSVC, exact PE/PDB pairs,
`llvm-readobj`, and `llvm-pdbutil`.

The common analyzer checks:

1. `IMAGE_FILE_MACHINE_AMD64`;
2. intended linked image and matching PDB;
3. controlled O0/O2/O2-noinline compiler switches;
4. PDB module/source provenance for project ownership;
5. selected `S_COMPILE3` records;
6. zero LTCG-marked selected `S_COMPILE3` records;
7. project-owned procedure extraction;
8. raw-name and leaf-name PDB collision diagnostics.

Detailed reports:

- [`results/detours.md`](results/detours.md)
- [`results/directxtex.md`](results/directxtex.md)
- [`results/winsparkle.md`](results/winsparkle.md)

---

## C++ function-identity model and remaining corpus work

C++ makes short-name function identity fundamentally unsafe for benchmarking.
Different concrete functions can share the same unqualified `DW_AT_name` because
of:

- overloads;
- repeated class-local method names;
- constructors/destructors;
- templates and specializations;
- namespaces;
- ABI-generated variants.

The original Snappy/double-conversion/Ninja results quantify this problem using
project-owned DWARF, and the identity validation above demonstrates a concrete
binary-address-based solution across real backends.

This resolves the **identity representation problem** much further than the
initial qualification stage, but it does not automatically promote the 44 Tier A
projects into benchmark targets. Corpus-wide selection still needs to characterize
and balance at least:

- `DW_AT_linkage_name` coverage;
- qualified/demangled identity coverage;
- translation-unit/source ownership;
- short-name collision exposure;
- function counts and size distributions;
- executable/library/test/example artifact roles;
- C++ feature diversity such as templates, STL usage, inheritance, virtual
  dispatch, exceptions, RTTI, lambdas, and operator overloading;
- same-address/ICF behavior where it appears in real targets.

The goal is therefore not to reduce the 48 candidates arbitrarily. The intended
next output is a broad validated pool plus a smaller balanced core set for
repeatable DecBench evaluation.

---

## Repository evidence

Important machine-readable evidence and workflow definitions include:

```text
# Corpus-scale discovery / qualification
results/cpp-corpus-2026-09-16/README.md
results/cpp-corpus-2026-09-16/final-48.csv
.github/workflows/cpp-corpus-funnel.yml
.github/workflows/cpp-corpus-funnel-second-half.yml
scripts/cpp_corpus_funnel.py

# Original GCC qualification
results/evidence/environment.txt
results/evidence/compile_report.json
results/evidence/collision/*.json
results/evidence/x86_64/qualification-summary.json
.github/workflows/cpp-x86_64-validation.yml

# Native MSVC/PDB qualification
results/evidence/msvc/detours/qualification-summary.json
results/evidence/msvc/directxtex/qualification-summary.json
results/evidence/msvc/winsparkle/qualification-summary.json
.github/workflows/msvc-detours-validation.yml
.github/workflows/msvc-directxtex-validation.yml
.github/workflows/msvc-winsparkle-validation.yml
scripts/qualify_msvc_pdb.ps1
```

Related DecBench identity implementation and validation:

- under review: [`Noelo-Lab/decbench#91`](https://github.com/Noelo-Lab/decbench/pull/91)
- branch: [`sjkim1127/decbench@fix/cpp-function-identity-clean`](https://github.com/sjkim1127/decbench/tree/fix/cpp-function-identity-clean)
- earlier single-commit candidate the validation table was measured against:
  `d76561fbb7c32a80fd52aba551d990992bb2c0da`

Large ELF/PE/PDB/build-tree artifacts are intentionally not committed. Permanent
Git evidence is kept compact and machine-readable; workflows regenerate the full
artifacts when required.

---

## What this repository establishes

This repository currently establishes that:

- a small cross-toolchain reference set can be reproduced with explicit
  source/debug oracles;
- C++ short-name identity collisions are large enough to require a richer
  DecBench identity model;
- a binary-address-based canonical identity can preserve same-name C++ functions
  and converge across real angr/Ghidra output on a LevelDB collision fixture;
- the identity model survives controlled optimization changes, real O2 inlined
  DWARF, ARM/Thumb normalization, serialization/progress recovery, and scoring
  abstention regressions;
- corpus-scale candidate discovery can be automated rather than selecting every
  target manually;
- at least **44** projects from the current search satisfy the strict generic
  Linux Tier A requirements, with another **4** near-ready Tier B projects.

It does **not** yet establish that all 48 projects should become DecBench targets,
that same-address ICF policy is fully closed, or that native MSVC/PDB identity is
implemented in DecBench. The remaining work is to finish those boundary cases,
characterize the broad candidate pool, select a diverse evaluation core without
throwing away the larger corpus, and then run the C++-aware evaluation path
end-to-end.