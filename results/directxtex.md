# DecBench C++ target validation result — Microsoft DirectXTex

## Target metadata

| Field | Value |
|---|---|
| Target | Microsoft DirectXTex |
| Upstream | `microsoft/DirectXTex` |
| Release/tag | `may2026` |
| Resolved commit | `4feb3e11a020f35b796fc769a74216a555d4f5ef` |
| Track | MSVC/PDB |
| DecBench revision | `d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f` |
| Validation date | 2026-08-23 |
| Host | macOS 26.5.1, arm64 |
| Container / OS | N/A — Wine/MSVC not available on this host |
| Compiler | BLOCKED — cl.exe not found |
| Linker | BLOCKED — link.exe not found |
| Windows SDK | N/A — not installed |
| Wine/msvc-wine | N/A — wine not found on this host |

## Build and ground-truth summary

| Mode | Build | Linked image(s) | `.ii` count | Ground truth | Source-owned function addresses | Unique short names | Collision groups | Collision addresses | Collision rate |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| O0 | BLOCKED | — | N/A | PDB: BLOCKED | — | — | — | — | — |
| O2 | BLOCKED | — | N/A | PDB: BLOCKED | — | — | — | — | — |
| O2-noinline | BLOCKED | — | N/A | PDB: BLOCKED | — | — | — | — | — |

## Blocking reason

Same as for Detours: `cl.exe`, `link.exe`, and the Windows SDK are not available on
this macOS 26.5.1 arm64 host. Wine is also absent.

```text
Environment check:
  wine     : not found
  cl.exe   : not found
  link.exe : not found
  Windows SDK : not installed
```

## Static config validation

The TOML at `targets/windows/directxtex.toml` is well-formed:

- **Source commit** `4feb3e11a020f35b796fc769a74216a555d4f5ef` matches upstream tag
  `may2026` on `microsoft/DirectXTex`.
- **Preferred output** is `DirectXTex.dll` (built with `-DBUILD_SHARED_LIBS=ON`).
- **CMake flags** correctly disable sample builds (`-DBUILD_SAMPLE=OFF`) and DX11
  (`-DBUILD_DX11=OFF`) to reduce scope.
- **Source filter** restricts to `DirectXTex/*.cpp` and `DirectXTex/*.h`, excluding
  optional tools (`Texassemble/`, `Texconv/`, `Texdiag/`), Auxiliary material, and
  tests.
- **Optimization mode mapping** is correct:
  - O0 → `/Od /Ob0 /Zi` + `/DEBUG`
  - O2 → `/O2 /Zi` + `/DEBUG`
  - O2-noinline → `/O2 /Ob0 /Zi` + `/DEBUG`
- The config correctly warns against inheriting Release IPO/LTCG presets.
- `collision_note` correctly flags this as a stress target due to heavy overloading.

**No config errors found during static review.**

## Optimization control

Not measured (BLOCKED). Key risk when environment becomes available:

- DirectXTex's CMake presets may inject Release-level optimizations unless explicitly
  overridden. The benchmark adapter must inject flags directly via
  `CMAKE_CXX_FLAGS` or equivalent.
- Confirm that `/LTCG` is NOT active in any mode unless it is the intended mode.

## Linked images

Not measured (BLOCKED). Expected:

```text
O0:         DirectXTex.dll (+ DirectXTex.pdb)
O2:         DirectXTex.dll (+ DirectXTex.pdb)
O2-noinline: DirectXTex.dll (+ DirectXTex.pdb)
```

Optional: texconv.exe, texassemble.exe, texdiag.exe may be audited separately.

## Source ownership filter

Planned (not measured):

```text
Included: DirectXTex/*.cpp, DirectXTex/*.h
Excluded: Auxiliary/**, Texassemble/**, Texconv/**, Texdiag/**, Tests/**
```

## Short-name collision details

Not measured (BLOCKED).

Known high-risk names based on source inspection:
- `Compress` — multiple overloads (format, flags, threading variants)
- `CompressEx` — similar overload set
- `SaveToDDSFile` / `SaveToDDSMemory`
- `EvaluateImage` — multiple overloads
- `TransformImage` — multiple overloads
- `Resize`, `Convert`, `GenerateMipMaps`

DirectXTex is explicitly designated a **stress target** for short-name collision
measurement. The collision rate is expected to be meaningfully higher than Snappy
or double-conversion.

Must be measured from actual PDB, not inferred from source.

## Preprocessed source / oracle notes

For MSVC/PDB targets:

- PDB generated for exact image: BLOCKED
- source/compiland information available: BLOCKED
- procedure/RVA extraction method: pdbparse or llvm-pdbutil (when environment available)

## Final status

Status: **BLOCKED**

Decision rationale:

```text
No MSVC/Wine/Windows SDK environment available on the macOS arm64 validation host.
Runtime validation cannot proceed. Static config review passed.
This target is already flagged as a "stress target" for collision measurement;
that assessment is consistent with source-level inspection of the overload patterns.
```

Remaining blockers:

```text
1. Wine or native Windows environment with MSVC Build Tools
2. Windows SDK (DirectX SDK / Windows SDK with DX12 headers)
3. CMake for Windows (or equivalent MSVC CMake invocation in the adapter)
4. pdbparse / llvm-pdbutil for PDB ground-truth extraction
5. Overload collision measurement — must be done from real PDB, not source inspection
```
