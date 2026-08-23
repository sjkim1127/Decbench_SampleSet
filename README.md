# DecBench C++ Target Validation

Focused validation workspace for a future DecBench multi-language C++ corpus.

The current scope is intentionally narrow: **confirm one candidate at a time against DecBench's existing GCC/DWARF C++ path before expanding the corpus.**

## Confirmed target

### Google Snappy 1.2.2

**Status: confirmed for the C++ target shortlist.**

- upstream: `google/snappy`
- stable release: `1.2.2`
- resolved commit: `6af9287fbdb913f0794d0148c6aa43b58e63c8e3`
- language: C++11
- build: CMake + GCC
- DecBench modes: `O0`, `O2`, `O2-noinline`
- ground-truth path: DWARF + preprocessed `.ii`
- output: shared `libsnappy` linked image

Snappy is retained as the first confirmed target because it is a small real C++ library with a straightforward build, no mandatory third-party runtime dependency for the core library, and a relatively limited object-oriented hierarchy compared with larger C++ applications. It is therefore a useful baseline for DecBench's experimental C++ path before moving to more collision-heavy targets.

## Reviewed candidates

### Google double-conversion v3.3.1

**Status: reviewed candidate, suitable for next validation step.**

- upstream: `google/double-conversion`
- stable release: `v3.3.1`
- resolved commit: `ae0dbfeb9744efd216c95b30555049d75d47116a`
- language: C++
- build: CMake + GCC
- expected modes: `O0`, `O2`, `O2-noinline`
- ground-truth path: DWARF + preprocessed `.ii`

Reason for selection:

- compact but real C++ implementation;
- algorithm-heavy code (floating-point conversion, arithmetic, parsing);
- limited inheritance/virtual hierarchy compared with larger C++ applications;
- low dependency burden;
- good fit as a clean C++ baseline after Snappy.

It is intentionally kept separate from the confirmed target until the DecBench compile path validation is completed.

### Ninja

**Status: reviewed candidate, recommended for next validation step.**

- upstream: `ninja-build/ninja`
- language: C++
- build: CMake / bootstrap build
- expected modes: `O0`, `O2`, `O2-noinline`
- ground-truth path: DWARF + preprocessed `.ii`

Reason for selection:

- real-world C++ executable rather than only a library;
- build-system and dependency management code provide a different workload from Snappy and double-conversion;
- low external dependency burden;
- suitable size for initial DecBench C++ expansion;
- provides a system/tooling-oriented C++ target between small libraries and large applications.

Ninja is kept separate from confirmed targets until the DecBench compile path validation is completed.

### The Powder Toy v100.0.399

**Status: reviewed candidate for the larger application slot.**

- upstream: `The-Powder-Toy/The-Powder-Toy`
- stable release: `v100.0.399`
- resolved commit: `9c94feba3ed5eaa75a819ac000c0d29e4ce92570`
- language: C++
- build: Meson
- expected modes: `O0`, `O2`, `O2-noinline`
- intended role: medium-large application / simulation workload

Reason for selection:

- substantially larger and more application-like than the other shortlist entries;
- simulation, rendering, UI, state-management, and numerical code provide a different recovery workload;
- modern C++ codebase with enough structure to stress optimized decompilation beyond small libraries;
- useful complement to Snappy, double-conversion, and Ninja for corpus diversity;
- stable release pin is available and current.

Caveat: The Powder Toy has a significantly heavier dependency and build footprint than the other candidates, so it should be validated after the smaller targets rather than used as the first integration probe.

## Initial C++ target shortlist

1. **Snappy 1.2.2** — small C++ library baseline
2. **double-conversion v3.3.1** — numeric / algorithm-heavy C++ baseline
3. **Ninja** — system / tooling executable target
4. **The Powder Toy v100.0.399** — medium-large application / simulation target

## DecBench integration shape

`targets/snappy.toml` is shaped for the current DecBench project model. It keeps DecBench in control of optimization flags, enables a shared library so the linked-image collector has a benchmark target, disables Snappy tests and benchmarks, and preserves `-g -save-temps=obj` for DWARF and `.ii` collection.

The validation workflow pins DecBench to:

`d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`

`.github/workflows/snappy-decbench-validation.yml` runs the real DecBench `scripts/compile_all.py` path and checks the first integration gate:

- all three optimization modes are attempted;
- at least one linked image is collected for each mode;
- at least one preprocessed `.ii` unit is collected for each mode.

Other candidates in this repository remain provisional until separately reviewed and confirmed.
