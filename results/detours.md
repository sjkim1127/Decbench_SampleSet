# DecBench C++ target validation result — Microsoft Detours

## Status

**VALIDATED** on the native MSVC/PDB track.

Detours v4.0.1 is now backed by actual Windows x86_64 runtime evidence rather than
only static source/build review. The qualification harness builds the upstream
Detours static library with controlled optimization flags, compiles the upstream
`withdll.cpp` sample, links an AMD64 PE with a full PDB, and inspects CodeView
procedure/source/compiland metadata.

This is target/oracle qualification. It does **not** claim that DecBench's current
DWARF scoring pipeline can consume PDBs unchanged.

## Target metadata

| Field | Value |
|---|---|
| Target | Microsoft Detours |
| Upstream | `microsoft/Detours` |
| Release/tag | `v4.0.1` |
| Resolved commit | `e4bfd6b03e50de46b47abfbd1e46b384f0c5f833` |
| Track | native MSVC / PE / PDB / CodeView |
| Validation date | 2026-08-23 |
| Runner OS | Windows Server 2025 x64 |
| Runner image | `windows-2025-vs2026` / `win25-vs2026` |
| Image version | `20260818.207.1` |
| Visual Studio | Visual Studio 2026 Developer Command Prompt v18.9.1 |
| MSVC compiler | 19.51.36256.0 |
| MSVC linker | 14.51.36256.0 |
| MSVC toolset path | 14.51.36231 |
| PDB tool | `llvm-pdbutil` |
| PE tool | `llvm-readobj` |
| Linked image | `withdll.exe` |
| Ground truth | matching full PDB / CodeView |

The harness resolves and records the exact Visual Studio `cl.exe`, `link.exe`, and
`nmake.exe` paths. This matters because the Windows runner also exposes an unrelated
Git `link.exe`; the qualification explicitly rejects that accidental tool
selection.

## Optimization control

The upstream Detours makefiles default to `/Od`, so benchmark qualification must
override optimization explicitly rather than trusting the upstream defaults.

Validated core/sample modes:

```text
O0:          /Od /Ob0 /Zi
O2:          /O2 /Zi
O2-noinline: /O2 /Ob0 /Zi
```

Link flags:

```text
/DEBUG:FULL /INCREMENTAL:NO /SUBSYSTEM:CONSOLE
```

The core build retains the upstream project flags that are orthogonal to this mode
mapping, including `/MT`, `/Gy`, `/Zl`, and the required Win32 defines.

## Build and PDB result

| Mode | Build | PE | PDB | Selected `S_COMPILE3` | Selected LTCG | Project procedures | Raw-name collision |
|---|---|---|---|---:|---:|---:|---:|
| O0 | PASS | AMD64 | full / usable | 5 | 0 | 136 | **8 / 136 = 5.88%** |
| O2 | PASS | AMD64 | full / usable | 5 | 0 | 136 | **8 / 136 = 5.88%** |
| O2-noinline | PASS | AMD64 | full / usable | 5 | 0 | 136 | **8 / 136 = 5.88%** |

For all three modes, `llvm-readobj` identifies the linked PE as
`IMAGE_FILE_MACHINE_AMD64`.

The corresponding PDB summaries report:

- debug info present;
- types present;
- IDs present;
- globals present;
- publics present;
- not stripped;
- not incrementally linked.

PDB stream/block counts vary normally between the optimization modes, but the
substantive qualification gates remain stable.

## Source/compiland ownership

The concrete `withdll.exe` link pulls the following Detours-owned core object files
into the final image:

```text
detours.obj
modules.obj
disasm.obj
creatwth.obj
```

The linked PDB also contains corresponding source provenance:

```text
detours.cpp
modules.cpp
disasm.cpp
creatwth.cpp
```

`withdll.obj` is separately tracked as the selected upstream wrapper/sample
compiland.

Detours is a static library, so source files whose object files are not needed by
`withdll.exe` are not pulled into this particular PE and therefore do not appear in
its measured project procedure set. For example, this result should not be read as
coverage of every object produced by the Detours core-library build.

## CodeView optimization evidence

Each mode contains 5 `S_COMPILE3` records for the selected Detours/wrapper
compilands and **0 selected LTCG-marked `S_COMPILE3` records**.

The PDB also contains `FRAMEPROC` records with `opt speed` markers. Those counts are
preserved only as diagnostics: `FRAMEPROC OptimizedForSpeed` is a per-frame flag
and a linked PDB may contain library/runtime code with optimization properties that
do not represent the requested benchmark mode.

The optimization oracle is therefore the explicit build command plus selected
compiland/LTCG audit, not a global `FRAMEPROC` assertion.

## Procedure identity diagnostic

For Detours-owned procedures with non-zero code size in the linked PDB:

```text
procedure records:      136
unique addresses:       136
unique raw PDB names:   132
collision groups:         4
collision addresses:      8
collision rate:         5.88%
```

The four duplicated raw-name groups are:

```text
StringCopyWorkerA
StringLengthWorkerA
StringValidateDestA
StringValidateDestAndLengthA
```

The same 5.88% diagnostic appears in O0, O2, and O2-noinline for this linked sample.

This metric is intentionally labelled **PDB raw-name collision**. It is not claimed
to be an apples-to-apples equivalent of DecBench's GCC/DWARF project-source
`DW_AT_name` collision metric.

## Artifact provenance

The native MSVC workflow initially produced complete PE/PDB artifacts but stopped
later in the validation script because the PDB symbol dump contains preamble lines
before the first `Mod ...` record. `Test-ObjectModule` rejected the initial empty
module name.

The parser was fixed in:

```text
aaad01ce4c45dd42c189151c6bc473d209223ce9
fix(ci): tolerate preamble lines before first PDB module
```

That change only alters empty-module preamble handling; it does not alter the
Detours build, link, PE, PDB, or requested optimization flags.

The complete raw artifacts used for independent re-analysis were emitted by run
`32633376778`:

| Mode | Artifact ID | SHA-256 |
|---|---:|---|
| O0 | `9491652051` | `5dec773675da8b7206e12fa7061829e0ed6cb4b7a92f368f756157e9225bf369` |
| O2 | `9491652923` | `8510b3d6f35d914e02ce28eea1eda2126c87236ea15879ecc043af80991700a8` |
| O2-noinline | `9491654177` | `052c784b545cc3b8a9eadff29adf4ebd53cf81f3edebf19bc12da5827240932f` |

Re-analysis with the final parser passes the substantive gates listed above, and
the subsequent post-fix CI run also passes all three matrix modes.

The compact machine-readable result retained in Git is:

```text
results/evidence/msvc/detours/qualification-summary.json
```

Large PE/PDB/raw symbol dumps remain CI artifacts rather than repository blobs.

## Qualification decision

Detours is **VALIDATED** and recommended as the current native Windows/MSVC systems
candidate because:

- the source revision is exactly pinned;
- real Visual Studio MSVC tools are used on Windows x86_64;
- all three benchmark optimization modes build;
- the resulting executable is AMD64 PE;
- a matching full PDB is produced and inspectable;
- project source/compiland provenance is available;
- selected compilands do not report LTCG;
- PDB procedure extraction succeeds;
- the observed name-collision diagnostic is measured rather than assumed.

## Remaining caveats

1. This is one concrete linked upstream sample, `withdll.exe`, not exhaustive
   coverage of every Detours sample/tool or every static-library object.
2. The PDB collision diagnostic is not equivalent to the current DecBench
   GCC/DWARF identity metric.
3. This result does not itself implement the upstream DecBench PDB scoring path or
   run GED/type/byte/decompiler scoring end-to-end.
