# Local validation procedure

This document replaces GitHub Actions as the primary validation path while the private-repository Actions allowance is unavailable.

The validation is intentionally split into two tracks:

1. GCC / DWARF / `.ii`: Snappy, double-conversion, Ninja.
2. MSVC / PE / PDB: Detours, DirectXTex, WinSparkle.

Do not merge the two toolchains into one result. The Windows track is experimental and follows the direction demonstrated by DecBench PR #36 rather than the current generic GCC/DWARF project pipeline.

## Pinned DecBench revision

Use:

```text
d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f
```

Record any later revision explicitly in the result file instead of silently updating the pin.

## 1. GCC / DWARF track

### Prepare the checkout

```bash
git clone https://github.com/Noelo-Lab/decbench.git
cd decbench
git checkout d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f

mkdir -p projects/cpp
cp /path/to/Decbench_SampleSet/targets/snappy.toml projects/cpp/
cp /path/to/Decbench_SampleSet/targets/double-conversion.toml projects/cpp/
cp /path/to/Decbench_SampleSet/targets/ninja.toml projects/cpp/
```

### Build the same compile image used by DecBench

From the DecBench repository root:

```bash
docker build -f docker/compile.Dockerfile -t decbench-compile .
```

The pinned compile image is Ubuntu 24.04 and already contains GCC/G++, CMake, Meson, Ninja, pyelftools and the light compile-path dependencies.

### Run the real DecBench compile driver

```bash
docker run --rm \
  -v "$PWD":/workspace \
  -w /workspace \
  -e PYTHONPATH=/workspace \
  decbench-compile \
  python3 scripts/compile_all.py results/cpp_local 3 \
  snappy double-conversion ninja
```

`scripts/compile_all.py` only builds optimization levels declared in each TOML and writes:

```text
results/cpp_local/compile_report.json
results/cpp_local/O0/<target>/compiled/
results/cpp_local/O2/<target>/compiled/
results/cpp_local/O2-noinline/<target>/compiled/
```

For every target/mode, the first gate is:

- build finishes without a project-level exception;
- at least one linked ELF image exists;
- at least one C++ preprocessed `.ii` file exists;
- DWARF is present in the benchmark image.

Do not treat `compile_results > 0` alone as success. The linked-image count is the build gate used by `compile_all.py`.

### Optimization modes

The GCC configs intentionally leave `CMAKE_BUILD_TYPE` empty and inject DecBench's flags through `$CFLAGS`.

Expected modes:

```text
O0           -> DecBench O0 + base flags
O2           -> DecBench O2 + base flags
O2-noinline  -> DecBench O2-noinline + base flags
base         -> -g -fno-builtin -save-temps=obj
```

Check the actual compiler command line if a project build system adds its own optimization, LTO/IPO, or inlining policy.

## 2. DWARF short-name collision audit

The current C++ benchmark identity issue is not just buildability. A candidate must also be checked for ambiguity when qualified C++ names collapse to the current short-name identity.

For each linked image and optimization mode:

1. Enumerate source-owned concrete DWARF subprograms with an address/range.
2. Resolve names through `DW_AT_specification` and `DW_AT_abstract_origin` when necessary.
3. Exclude compiler probes, tests, vendored dependencies and other non-project compilation units.
4. Preserve the fully qualified name for the audit, then derive the same unqualified/short name used by the current DecBench matching path.
5. Group distinct function addresses by short name.
6. A collision group is a short name associated with more than one distinct source-owned address.

Record:

```text
source_function_addresses
unique_short_names
collision_groups
collision_addresses
collision_rate = collision_addresses / source_function_addresses
```

The important number is the percentage of source-owned addresses exposed to ambiguity, not simply the number of duplicate strings.

Do not claim a target has a low collision rate until this is measured from the produced debug information.

## 3. MSVC / PE / PDB track

The current `docker/compile.Dockerfile` is not the validation environment for these targets. Use the real MSVC/Windows SDK environment from the DecBench PR #36 direction (for example `cl.exe` under Wine/msvc-wine), or a native Windows MSVC environment that can reproduce equivalent PE/PDB artifacts.

Candidate metadata lives in:

```text
targets/windows/detours.toml
targets/windows/directxtex.toml
targets/windows/winsparkle.toml
```

These files are validation metadata, not current `Project.from_toml` inputs.

### Required mode mapping

Use the following candidate mapping and record the exact final compiler/linker command lines:

```text
O0           -> /Od /Ob0 /Zi        + /DEBUG
O2           -> /O2      /Zi        + /DEBUG
O2-noinline  -> /O2 /Ob0 /Zi        + /DEBUG
```

This is an MSVC analogue for the experiment, not a claim that MSVC `/O2` is semantically identical to GCC `-O2`.

For controlled results:

- disable inherited whole-program optimization/LTCG unless it is explicitly part of the mode;
- ensure the PDB corresponds to the exact PE image being measured;
- record toolchain and Windows SDK versions;
- preserve PE and PDB together;
- record whether the build ran natively or through Wine.

### Per-target notes

**Detours**

- upstream core output is a static library;
- retain only explicitly selected linked PE sample/tool images;
- override the upstream `/Od` default per benchmark mode.

**DirectXTex**

- prefer the project-owned DLL as the clean linked image;
- optional command-line tools may be audited separately;
- expect overload-driven short-name collisions and measure them explicitly.

**WinSparkle**

- filter PDB compilands to project-owned `src/`/`include/` sources;
- exclude vendored `3rdparty/` code;
- disable stock Release LTCG/whole-program settings when producing controlled benchmark modes.

## 4. PDB short-name collision audit

Apply the same identity test to PDB/CodeView ground truth:

1. Extract source-owned procedures with concrete RVA/address information.
2. Use compiland/source information to exclude vendored and unrelated units.
3. Keep the qualified procedure name and derive the current short-name form.
4. Group distinct RVAs by short name.
5. Record total source procedure addresses, unique short names, collision groups, collision addresses and collision rate.

Do not use the raw PDB PROC32 count as a proxy for source-function count without source/compiland filtering.

## 5. Result recording

Copy `docs/result-template.md` to one file per target, for example:

```text
results/snappy.md
results/double-conversion.md
results/ninja.md
results/detours.md
results/directxtex.md
results/winsparkle.md
```

Only promote a target from `selected` to `validated` or `confirmed` after the relevant build, ground-truth and collision fields are populated with measured results.
