# DecBench C++ target validation result

> Copy this file to `results/<target>.md` and replace every `TBD` with measured data. Do not infer or estimate collision statistics.

## Target metadata

| Field | Value |
|---|---|
| Target | TBD |
| Upstream | TBD |
| Release/tag | TBD |
| Resolved commit | TBD |
| Track | GCC/DWARF or MSVC/PDB |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Validation date | TBD |
| Host | TBD |
| Container / OS | TBD |
| Compiler | TBD |
| Linker | TBD |
| Windows SDK | N/A or TBD |
| Wine/msvc-wine | N/A or TBD |

## Build and ground-truth summary

| Mode | Build | Linked image(s) | `.ii` count | Ground truth | Source-owned function addresses | Unique short names | Collision groups | Collision addresses | Collision rate |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| O0 | TBD | TBD | TBD / N/A | DWARF/PDB: TBD | TBD | TBD | TBD | TBD | TBD |
| O2 | TBD | TBD | TBD / N/A | DWARF/PDB: TBD | TBD | TBD | TBD | TBD | TBD |
| O2-noinline | TBD | TBD | TBD / N/A | DWARF/PDB: TBD | TBD | TBD | TBD | TBD | TBD |

Collision rate is:

```text
collision_addresses / source_owned_function_addresses
```

where `collision_addresses` counts distinct source-owned addresses/RVAs belonging to a short-name group with more than one distinct address.

## Optimization control

Record the actual final compile/link flags, not only the intended configuration.

### O0

```text
compile: TBD
link:    TBD
```

### O2

```text
compile: TBD
link:    TBD
```

### O2-noinline

```text
compile: TBD
link:    TBD
```

Unexpected optimization/LTO/IPO/inlining behavior:

```text
TBD
```

## Linked images

### O0

```text
TBD
```

### O2

```text
TBD
```

### O2-noinline

```text
TBD
```

For PE targets, record the exact PE ↔ PDB pair.

## Source ownership filter

Included project-owned paths/compilands:

```text
TBD
```

Excluded tests/vendor/compiler-probe/generated paths:

```text
TBD
```

Any uncertain ownership cases:

```text
TBD
```

## Short-name collision details

List the highest-impact collision groups. Keep qualified names and addresses/RVAs so the result can be re-audited.

| Short name | Distinct addresses/RVAs | Example qualified names | Notes |
|---|---:|---|---|
| TBD | TBD | TBD | TBD |

## Preprocessed source / oracle notes

For GCC/DWARF targets:

- `.ii` preservation: TBD
- DWARF `DW_AT_specification` handling checked: TBD
- DWARF `DW_AT_abstract_origin` handling checked: TBD

For MSVC/PDB targets:

- PDB generated for exact image: TBD
- source/compiland information available: TBD
- procedure/RVA extraction method: TBD

## Final status

Choose one:

```text
SELECTED      # source/build shape reviewed, measurements incomplete
VALIDATED     # all required local build + oracle + collision checks completed
CONFIRMED     # accepted as a clean/appropriate initial corpus target after review
REJECTED      # unsuitable; explain why below
```

Status: **TBD**

Decision rationale:

```text
TBD
```

Remaining blockers:

```text
TBD
```
