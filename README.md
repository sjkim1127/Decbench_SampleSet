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

## DecBench integration shape

`targets/snappy.toml` is shaped for the current DecBench project model. It keeps DecBench in control of optimization flags, enables a shared library so the linked-image collector has a benchmark target, disables Snappy tests and benchmarks, and preserves `-g -save-temps=obj` for DWARF and `.ii` collection.

The validation workflow pins DecBench to:

`d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f`

`.github/workflows/snappy-decbench-validation.yml` runs the real DecBench `scripts/compile_all.py` path and checks the first integration gate:

- all three optimization modes are attempted;
- at least one linked image is collected for each mode;
- at least one preprocessed `.ii` unit is collected for each mode.

Other candidates in this repository remain provisional until separately reviewed and confirmed.
