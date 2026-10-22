# Native source recollection

`cpp-evidence-recollection.yml` rebuilds pinned Detours and WinSparkle targets
in three modes on the existing Windows/MSVC runners. It reuses their native
PE/PDB validation and preserves the linked-image identity with each artifact.

Detours invocations come from the actual executed compiler log. WinSparkle
invocations come from MSBuild CL tracking logs; the exact tracking files are
retained. Compiler batch inputs are separated into per-TU replay commands
without reordering options. Preprocessing adds `/Y-` to retain complete text
rather than depending on an opaque precompiled-header cache; both original and
replay arguments are recorded separately.

Artifacts contain the original pinned source archive, submodule revisions,
actual modified build-project evidence, compile database, preprocessing maps
and `.ii` archive, logs, linked image and matching PDB. This is a collection
lane, not a qualification or score gate. `qualified` and `scoring_ready` remain
false. Dependency provenance and original/replay compilation equivalence still
need validation.

These are **new linked-image candidates**. They must not supply source/debug
or addresses for an earlier frozen binary merely because project/mode or symbol
names agree. Compare binary/code/debug identities explicitly, then publish any
changed images as a new immutable dataset revision with a new address plan.
Keep the existing 45-image pilot and its frozen requests intact.
### Compiler working directories

WinSparkle and its dependency projects use different compiler working directories.
An imported observation-only MSBuild target records `MSBuildProjectFullPath` and
`MSBuildProjectDirectory` beside each CL tracking log. The collector requires this
record and uses that project's directory for relative compiler options. It does
not infer a directory from the source basename or reuse the top-level project
directory for dependencies. Missing or inconsistent records fail collection.

The first Windows collection attempt built WinSparkle successfully but failed to
preprocess wxWidgets because the collector used the top-level directory. Those
failed artifacts are retained as diagnostic evidence, not complete TU bundles.
