# DecBench C++ Target Qualification

> **Disclaimer:** Unofficial DecBench target-qualification workspace; not an official Noelo-Lab repository.

Artifact-backed qualification workspace for candidate C++ targets for a future
DecBench multi-language corpus.

This repository deliberately separates:

- successful project builds;
- target/oracle qualification;
- function-identity diagnostics;
- full end-to-end DecBench scoring.

A target marked **VALIDATED** here has artifact-backed build/oracle evidence. It
does **not** mean GED, type matching, byte matching, and every decompiler have
already been run end-to-end on that target.

## Current status

All six shortlisted C++ targets now have runtime qualification evidence.

| Target | Track | O0 | O2 | O2-noinline | Linked image | Ground truth | Current identity diagnostic | Status |
|---|---|---|---|---|---|---|---|---|
| **Snappy 1.2.2** | GCC / DWARF | PASS | PASS | PASS | `libsnappy.so.1.2.2` | DWARF + `.ii` | project `DW_AT_name`: 52.87% / 53.16% / 51.97% | **VALIDATED** |
| **double-conversion v3.3.1** | GCC / DWARF | PASS | PASS | PASS | `libdouble-conversion.so.3.3.0` | DWARF + `.ii` | project `DW_AT_name`: 7.87% / 15.58% / 8.06% | **VALIDATED** |
| **Ninja v1.13.1** | GCC / DWARF | PASS | PASS | PASS | `ninja` | DWARF + `.ii` | project `DW_AT_name`: 26.70% / 32.38% / 27.55% | **VALIDATED WITH CAVEATS** |
| **Microsoft Detours v4.0.1** | native MSVC / PDB | PASS | PASS | PASS | `withdll.exe` | PDB / CodeView | PDB raw-name: 5.88% / 5.88% / 5.88% | **VALIDATED** |
| **Microsoft DirectXTex may2026** | native MSVC / PDB | PASS | PASS | PASS | `DirectXTex.dll` | PDB / CodeView | PDB raw-name: 12.92% / 17.65% / 13.27% | **VALIDATED** |
| **WinSparkle v0.9.4** | native MSVC / PDB | PASS | PASS | PASS | `WinSparkle.dll` | PDB / CodeView | PDB raw-name: 18.26% / 14.79% / 18.84% | **VALIDATED** |

Values are ordered `O0 / O2 / O2-noinline`.

The GCC values are DecBench-aligned project-source `DW_AT_name` collision exposure.
The MSVC values are **separate PDB/CodeView procedure-name diagnostics** and must
not be treated as numerically equivalent to the DWARF metric.

Detailed aggregate report: [`results/summary.md`](results/summary.md)

---

## Historical candidate funnel

The repository started with a much wider, Windows-heavy candidate pool before
converging on the current three GCC/DWARF + three native MSVC/PDB targets. The
entries below are preserved to make that selection process reviewable.

**Important:** "not in the final six" does not necessarily mean a target failed
to build or is unsuitable for DecBench. Several candidates built successfully
and were later **deferred, superseded, or kept as reserve/stress targets** because
the first qualification batch was narrowed around integration cost, source/oracle
quality, dependency contamination, and controllable optimization.

Historical snapshots:

- [initial four-target Windows CI probe](https://github.com/sjkim1127/Decbench_SampleSet/commit/09a91305f45157afbb7bc666ae54c4511dbfc43d);
- [early candidate summary](https://github.com/sjkim1127/Decbench_SampleSet/commit/4152c1ad2d1317af459b447f014a3ede5cb7ad92);
- [small / medium / large tier exploration](https://github.com/sjkim1127/Decbench_SampleSet/commit/12c28f6b56bdb01902bd3594779c2484e9802747);
- [five-target shortlist refocus](https://github.com/sjkim1127/Decbench_SampleSet/commit/b289181406742dc8d3da2110f2988262482813de).

### Probed or shortlisted, then dropped/deferred

| Candidate | Earlier evidence / role | Why it did not remain in the final six | Disposition |
|---|---|---|---|
| **TrafficMonitor Lite** | Native MSVC x64 Release CI **PASS**; compact Win32/MFC utility; ~1.94 MB EXE, ~19.85 MB PDB, raw `PROC32` 5,297 | No build rejection is recorded. It was superseded when the workspace moved from a Windows-heavy probe list to a smaller cross-track qualification set with explicit O0/O2/O2-noinline oracle evidence. | **Superseded, not failed** |
| **OpenLoco** | Native MSVC x64 Release CI **PASS**; substantial real-world C++ game/simulation; ~9.67 MB EXE, ~26.48 MB PDB, raw `PROC32` 10,777 | Clean build cost was about 1,656 s on the early Windows CI, making it expensive for a first-pass multi-mode corpus. | **Deferred on cost / scale** |
| **x64dbg** | Native MSVC x64 Release CI **PASS** for core outputs such as `x64gui.dll`, `x64dbg.dll`, and `x64bridge.dll` | Explicitly classified as a stress/complexity target: heavy dependency/submodule graph, and the Release PDB set was not yet treated as a complete source-level oracle. | **Deferred stress target** |
| **Windows Terminal / OpenConsole** | Very large Windows systems C++; early probe targeted `OpenConsole.exe` | Full-solution integration was considered too heavy for the initial corpus. The historical recommendation was to benchmark a component subset such as Host/conhost instead. | **Deferred; component subset preferred** |
| **The Powder Toy** | C++20 physics/simulation target; promoted from candidate to a proposed medium/application slot and received an MSVC validation workflow | Explicitly removed from the initial shortlist because its dependency footprint, GUI-style inheritance, repeated method names, and optimization/build behavior made it less attractive than the selected Windows targets for the first corpus. | **Dropped from first corpus** |
| **SpaceCadetPinball** | High-priority small dual-toolchain candidate; Visual Studio and MinGW paths made it attractive for compiler A/B comparison | No qualification failure is recorded. It remained a proposed target when the broader tier plan was retired and never advanced into the final evidence-backed six. | **Deferred / unqualified** |
| **Explorer++** | High-priority medium native-Windows application candidate | vcpkg dependency restore/build cost still needed measurement, and no MinGW path was assumed. It was not advanced before the shortlist refocus. | **Deferred / unqualified** |
| **Notepad++** | High-priority large Windows target with both MSVC and MinGW build paths | Static Scintilla/Lexilla code and vendored Boost regex complicate project-owned attribution; it stayed a promising but higher-integration-cost candidate. | **Deferred / unqualified** |

### Reserve candidates considered but not promoted

| Candidate | Historical role | Main caveat recorded during triage |
|---|---|---|
| **Nilesoft Shell** | Small native-Windows reserve | MSVC build path looked reproducible, but MinGW compatibility was not established. |
| **Rainmeter** | Medium native-Windows reserve | Full solution/install tooling could add noise; a benchmark would need to isolate core runtime binaries. |
| **nCine** | Medium dual-toolchain compatibility reserve | Broad graphics/audio/Lua/UI dependency set could increase build and source-attribution cost. |

The historical candidate work was exploratory. These dispositions should not be
read as permanent rejections: some may become better choices once DecBench's C++
qualified-name model, PDB ingestion, component-level targeting, or corpus budget
changes.

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

Pinned DecBench revision for the GCC qualification path:

```text
d9f4f8af6097d7c42c4965cfc3f197dcf76f0a4f
```

---

## GCC / DWARF qualification

The GCC targets were qualified through DecBench's real compile path locally on
aarch64 and independently on GitHub-hosted x86_64 Linux.

```text
O0:          -O0 -g -fno-builtin -save-temps=obj
O2:          -O2 -g -fno-builtin -save-temps=obj
O2-noinline: -O2 -fno-inline -g -fno-builtin -save-temps=obj
```

x86_64 evidence:

```text
workflow run: 32632337105
artifact id:  9491409143
artifact sha256:
60fef5ba7bb9a252e0d8155cd7b775a54679ed2ff4b92b2d6152e7e54f01ccc2
workflow commit:
3c48841470ed64370b4541a721c12fc1df430dd3
compiler: GCC/G++ 13.3.0
```

All 9 target/mode combinations build and link successfully. The final images are
`EM_X86_64`, producer metadata contains the expected mode flags, and no `-flto`,
`-fltrans`, `-fwpa`, or `-fwhole-program` markers were observed.

| Target | `.ii` units/mode | Project funcs O0/O2/O2-noinline | Collision O0/O2/O2-noinline |
|---|---:|---|---|
| Snappy | 4 | 157 / 79 / 152 | 52.87% / 53.16% / 51.97% |
| double-conversion | 8 | 127 / 77 / 124 | 7.87% / 15.58% / 8.06% |
| Ninja | 33 | 412 / 210 / 265 | 26.70% / 32.38% / 27.55% |

Permanent evidence:

```text
results/evidence/x86_64/qualification-summary.json
```

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

`FRAMEPROC OptimizedForSpeed` is diagnostic only and is not the optimization-mode
oracle.

### Detours v4.0.1

```text
image: withdll.exe
O0:          /Od /Ob0 /Zi
O2:          /O2 /Zi
O2-noinline: /O2 /Ob0 /Zi
```

All three modes contain 5 selected `S_COMPILE3` records, 0 selected LTCG records,
and 136 project procedures. Raw PDB-name collision is 5.88% in every mode.

Permanent evidence:

```text
results/evidence/msvc/detours/qualification-summary.json
```

Detailed report: [`results/detours.md`](results/detours.md)

### DirectXTex may2026

```text
workflow run:    32684847948
workflow commit: 040e7dfc3a08ed94179b3a15746296d8be3d0dbe
image:           DirectXTex.dll
runner image:    win25-vs2026 / 20260818.207.1
```

```text
O0:          /Od /Ob0 /Zi /GL-
O2:          /O2 /Zi /GL-
O2-noinline: /O2 /Ob0 /Zi /GL-
link:        /DEBUG:FULL /INCREMENTAL:NO /LTCG:OFF
```

| Mode | Artifact id | SHA-256 |
|---|---:|---|
| O0 | `9505320922` | `dd6fadd530a765a8ab5e38c1fd31bce0d3481805272ca7acd59a40e5dabab8c5` |
| O2 | `9505325453` | `1b1ad3fa76324aa577bb2b8f29adac27d011e3b84111b3540c0b1cd281ce5d62` |
| O2-noinline | `9505325181` | `8448cf1c351a373d1b53f385705c7928e97eb96625ad8fff1dcb8d92cb5381c5` |

The initial DirectXTex blocker was a module-name matcher bug, not a build failure.
CMake/Ninja emits full Windows PDB module paths ending in names such as
`BC.cpp.obj`; commit `7f227d52ea9fdc7295dd7560f3f0827417d2938c` corrected the Windows separator
suffix check while preserving the ownership gate.

All three modes select 17 project compilands, 17 `S_COMPILE3` records, and 0 LTCG
records. Project procedure counts are 766 / 221 / 746 and raw-name diagnostics are
12.92% / 17.65% / 13.27%.

Permanent evidence:

```text
results/evidence/msvc/directxtex/qualification-summary.json
```

Detailed report: [`results/directxtex.md`](results/directxtex.md)

### WinSparkle v0.9.4

```text
workflow run:    32686141551
workflow commit: 1325beadad2886496b6bd7c2f69a36d8bb4aa9de
image:           WinSparkle.dll
runner image:    win25-vs2026 / 20260818.207.1
```

```text
O0:          /Od /Ob0 /Zi /GL-
O2:          /O2 /Zi /GL-
O2-noinline: /O2 /Ob0 /Zi /GL-
link:        /DEBUG:FULL /INCREMENTAL:NO /LTCG:OFF
```

| Mode | Artifact id | SHA-256 |
|---|---:|---|
| O0 | `9505927922` | `46f3a77c53395821c390a3da3cbe085ec1c3d4b7d8386daef369980f02aacb93` |
| O2 | `9505868200` | `1e085f08a0873f0929ee5c63febcefb7d52607411f4c338c0b69557a81b9dc00` |
| O2-noinline | `9505923377` | `575239975dd9001d31b71ad34306b11bd75cbf654d3353c694146f125d9a855c` |

The old basename-based ownership matcher exposed a real false positive: WinSparkle
and wxWidgets both contain `settings.cpp`, so `WinSparkle_wx/settings.obj` was
incorrectly selected as project-owned. Commit
`1325beadad2886496b6bd7c2f69a36d8bb4aa9de` changed the generic analyzer to use
exact `llvm-pdbutil dump -modules -files` provenance first, with object-name
matching only as a fallback.

The authoritative run reports 12 project source files, 12 provenance-selected
project compilands, 12 selected `S_COMPILE3` records, and 0 selected LTCG records
in every mode. Project procedure counts are 2267 / 1048 / 2160 and raw PDB-name
diagnostics are 18.26% / 14.79% / 18.84%.

The matrix qualification jobs all succeeded. The initial aggregate evidence
publisher failed only because another workflow advanced `main` before its push.
The evidence was recovered directly from the successful artifacts. The publisher
now uses full history plus `fetch`/`rebase`/bounded push retries, and the status
probe is read-only instead of committing transient snapshots to `main`.

Permanent evidence:

```text
results/evidence/msvc/winsparkle/qualification-summary.json
```

Detailed report: [`results/winsparkle.md`](results/winsparkle.md)

---

## Why successful compilation is not enough

For the GCC path, qualification additionally requires preserved `.ii` units,
usable DWARF, controlled optimization, project-source ownership, and measurement
of short-name collision exposure.

For the MSVC path, qualification requires exact PE/PDB pairing, CodeView provenance,
controlled optimization and LTCG state, project compiland filtering, and PDB
procedure diagnostics.

In both tracks, **build success is necessary but not sufficient**.

---

## C++ identity caveat

The current GCC experiment exposes a real C++ identity issue: different concrete
functions can share the same unqualified `DW_AT_name` because of overloads,
repeated class-local names, constructor/destructor variants, templates, and ABI
variants.

The PDB track measures a different namespace: raw CodeView procedure names over
project-owned linked compilands. Those values are useful diagnostics but are not an
apples-to-apples replacement for DecBench's current DWARF identity metric.

A future qualified-name/signature-aware ground-truth design may change both target
difficulty and appropriate corpus composition.

---

## Evidence inventory

```text
# Local aarch64 GCC qualification
results/evidence/environment.txt
results/evidence/compile_report.json
results/evidence/collision/*.json

# GitHub-hosted x86_64 GCC qualification
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

Large ELF/PE/PDB/build-tree artifacts are intentionally not committed. Permanent
Git evidence is compact and machine-readable; the workflows can regenerate the
full artifacts.

---

## Current recommendation for DecBench

The six evidence-backed candidates offer complementary roles:

- **double-conversion v3.3.1** — clean numerical GCC/DWARF baseline;
- **Ninja v1.13.1** — real executable with architecture-sensitive optimized output;
- **Snappy 1.2.2** — compact collision-heavy GCC/DWARF stress/control target;
- **Microsoft Detours v4.0.1** — native Windows systems target;
- **Microsoft DirectXTex may2026** — graphics/image-processing rich-C++ target;
- **WinSparkle v0.9.4** — updater/networking/threading/UI-oriented Windows target.

This repository should still be treated as **candidate research and qualification
evidence**, not an implicit request to merge every target. The remaining upstream
decisions are corpus selection, PDB/CodeView ingestion, and C++ function-identity
design before claiming a complete multi-language DecBench benchmark run.
