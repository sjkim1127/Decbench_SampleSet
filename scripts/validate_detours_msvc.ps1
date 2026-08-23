param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("O0", "O2", "O2-noinline")]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$DetoursRoot,

    [Parameter(Mandatory = $true)]
    [string]$EvidenceRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$DetoursRoot = (Resolve-Path $DetoursRoot).Path
$EvidenceRoot = [System.IO.Path]::GetFullPath($EvidenceRoot)
New-Item -ItemType Directory -Force -Path $EvidenceRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $EvidenceRoot "raw") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $EvidenceRoot "binary") | Out-Null

$modeFlags = @{
    "O0"          = @("/Od", "/Ob0")
    "O2"          = @("/O2")
    "O2-noinline" = @("/O2", "/Ob0")
}

$srcBaseFlags = @(
    "/nologo", "/W4", "/WX", "/Zi", "/MT", "/Gy", "/Gm-", "/Zl",
    "/DWIN32_LEAN_AND_MEAN", "/D_WIN32_WINNT=0x501"
)
$sampleBaseFlags = @(
    "/nologo", "/W4", "/WX", "/Zi", "/MT", "/Gm-"
)

$srcFlagsArray = $srcBaseFlags + $modeFlags[$Mode]
$srcFlags = $srcFlagsArray -join " "
$includeDir = Join-Path $DetoursRoot "include"
$sampleFlagsArray = $sampleBaseFlags + $modeFlags[$Mode] + @("/I$includeDir")
$sampleFlags = $sampleFlagsArray -join " "
$linkFlags = @("/nologo", "/DEBUG:FULL", "/INCREMENTAL:NO", "/SUBSYSTEM:CONSOLE")

$buildLog = Join-Path $EvidenceRoot "build.log"
$commandLog = Join-Path $EvidenceRoot "commands.txt"

function Get-NativeTool {
    param([Parameter(Mandatory = $true)][string]$Name)
    $cmd = Get-Command $Name -CommandType Application -ErrorAction Stop | Select-Object -First 1
    return $cmd.Source
}

$clExe = Get-NativeTool "cl.exe"
$linkExe = Get-NativeTool "link.exe"
$nmakeExe = Get-NativeTool "nmake.exe"
$llvmPdbutilExe = Get-NativeTool "llvm-pdbutil.exe"
$llvmReadobjExe = Get-NativeTool "llvm-readobj.exe"

if ($clExe -notmatch "Microsoft Visual Studio") {
    throw "cl.exe did not resolve to Visual Studio: $clExe"
}
if ($linkExe -notmatch "Microsoft Visual Studio") {
    throw "link.exe did not resolve to Visual Studio: $linkExe"
}
if ($nmakeExe -notmatch "Microsoft Visual Studio") {
    throw "nmake.exe did not resolve to Visual Studio: $nmakeExe"
}

@(
    "mode=$Mode",
    "detours_root=detours",
    "cl=$clExe",
    "link=$linkExe",
    "nmake=$nmakeExe",
    "llvm_pdbutil=$llvmPdbutilExe",
    "llvm_readobj=$llvmReadobjExe",
    "src_cflags=$srcFlags",
    "sample_cflags=$sampleFlags",
    "link_flags=$($linkFlags -join ' ')"
) | Set-Content -Encoding utf8 $commandLog

function Invoke-Logged {
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Label
    )

    Add-Content -Encoding utf8 $buildLog "`n===== $Label ====="
    Add-Content -Encoding utf8 $buildLog ("$Exe " + ($Arguments -join " "))
    & $Exe @Arguments 2>&1 | Tee-Object -FilePath $buildLog -Append
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE"
    }
}

# Record the native MSVC toolchain selected by VsDevCmd.
$probeSource = Join-Path $EvidenceRoot "toolchain-probe.cpp"
$probeObj = Join-Path $EvidenceRoot "toolchain-probe.obj"
"int decbench_msvc_probe(void) { return 0; }" | Set-Content -Encoding ascii $probeSource
Invoke-Logged -Exe $clExe -Arguments @("/nologo", "/Bv", "/c", $probeSource, "/Fo$probeObj") -Label "MSVC toolchain"

# Build the upstream Detours static library with explicit mode flags, overriding
# the upstream src/Makefile default of /Od.
$srcDir = Join-Path $DetoursRoot "src"
Push-Location $srcDir
try {
    Invoke-Logged -Exe $nmakeExe -Arguments @(
        "/nologo",
        "DETOURS_TARGET_PROCESSOR=X64",
        "CFLAGS=$srcFlags",
        "all"
    ) -Label "Build Detours core library"
}
finally {
    Pop-Location
}

$detoursLib = Join-Path $DetoursRoot "lib.X64\detours.lib"
if (-not (Test-Path $detoursLib)) {
    throw "Detours library not produced: $detoursLib"
}
if (-not (Test-Path (Join-Path $includeDir "detours.h"))) {
    throw "Detours public header was not staged"
}

# Build one deterministic linked PE around the upstream withdll sample.  The
# wrapper is compiled manually so it does not inherit samples/common.mak /Od.
$binDir = Join-Path $EvidenceRoot "binary"
$obj = Join-Path $binDir "withdll.obj"
$compilerPdb = Join-Path $binDir "withdll-compile.pdb"
$exe = Join-Path $binDir "withdll.exe"
$pdb = Join-Path $binDir "withdll.pdb"
$source = Join-Path $DetoursRoot "samples\withdll\withdll.cpp"

$compileArgs = $sampleFlagsArray + @(
    "/c", $source, "/Fo$obj", "/Fd$compilerPdb"
)
Invoke-Logged -Exe $clExe -Arguments $compileArgs -Label "Compile withdll.cpp"

$linkArgs = $linkFlags + @(
    "/OUT:$exe", "/PDB:$pdb", $obj, $detoursLib, "kernel32.lib"
)
Invoke-Logged -Exe $linkExe -Arguments $linkArgs -Label "Link withdll.exe"

foreach ($required in @($exe, $pdb)) {
    if (-not (Test-Path $required)) {
        throw "Required output missing: $required"
    }
}

# Audit the actual commands emitted/executed, not just the requested mode table.
$buildText = Get-Content -Raw $buildLog
switch ($Mode) {
    "O0" {
        if ($buildText -notmatch '/Od' -or $buildText -notmatch '/Ob0') {
            throw "O0 command log does not contain /Od and /Ob0"
        }
    }
    "O2" {
        if ($buildText -notmatch '/O2') {
            throw "O2 command log does not contain /O2"
        }
    }
    "O2-noinline" {
        if ($buildText -notmatch '/O2' -or $buildText -notmatch '/Ob0') {
            throw "O2-noinline command log does not contain /O2 and /Ob0"
        }
    }
}

$rawDir = Join-Path $EvidenceRoot "raw"
$peHeaders = Join-Path $rawDir "pe-headers.txt"
$pdbSummary = Join-Path $rawDir "pdb-summary.txt"
$pdbModules = Join-Path $rawDir "pdb-modules-files.txt"
$pdbSymbols = Join-Path $rawDir "pdb-symbols.txt"

& $llvmReadobjExe --file-headers --coff-debug-directory $exe 2>&1 | Set-Content -Encoding utf8 $peHeaders
if ($LASTEXITCODE -ne 0) { throw "llvm-readobj failed" }
$peText = Get-Content -Raw $peHeaders
if ($peText -notmatch "IMAGE_FILE_MACHINE_AMD64") {
    throw "Linked PE is not AMD64"
}

& $llvmPdbutilExe dump -summary $pdb 2>&1 | Set-Content -Encoding utf8 $pdbSummary
if ($LASTEXITCODE -ne 0) { throw "llvm-pdbutil summary failed" }
& $llvmPdbutilExe dump -modules -files $pdb 2>&1 | Set-Content -Encoding utf8 $pdbModules
if ($LASTEXITCODE -ne 0) { throw "llvm-pdbutil module/file dump failed" }
& $llvmPdbutilExe dump -symbols $pdb 2>&1 | Set-Content -Encoding utf8 $pdbSymbols
if ($LASTEXITCODE -ne 0) { throw "llvm-pdbutil symbol dump failed" }

$moduleText = Get-Content -Raw $pdbModules
$symbolLines = Get-Content $pdbSymbols

$coreObjects = @(
    "detours.obj", "modules.obj", "disasm.obj", "image.obj", "creatwth.obj",
    "disolx86.obj", "disolx64.obj", "disolia64.obj", "disolarm.obj", "disolarm64.obj"
)
$coreSources = @("detours.cpp", "modules.cpp", "disasm.cpp", "image.cpp", "creatwth.cpp")
$selectedObjects = $coreObjects + @("withdll.obj")

function Test-ObjectModule {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$ModuleName,
        [Parameter(Mandatory = $true)][string[]]$ObjectNames
    )

    if ([string]::IsNullOrWhiteSpace($ModuleName)) {
        return $false
    }

    $lower = $ModuleName.ToLowerInvariant()
    foreach ($objName in $ObjectNames) {
        $needle = $objName.ToLowerInvariant()
        if ($lower.EndsWith($needle) -or $lower.Contains("($needle)")) {
            return $true
        }
    }
    return $false
}

$moduleHits = @()
foreach ($objName in $coreObjects) {
    if ($moduleText -match [regex]::Escape($objName)) {
        $moduleHits += $objName
    }
}
$sourceHits = @()
foreach ($sourceName in $coreSources) {
    if ($moduleText -match [regex]::Escape($sourceName)) {
        $sourceHits += $sourceName
    }
}

if ($moduleHits.Count -eq 0) {
    throw "PDB contains no Detours-owned core compilands"
}
if ($sourceHits.Count -eq 0) {
    throw "PDB contains no Detours-owned source provenance"
}
if ($moduleText -notmatch "withdll\.obj") {
    throw "PDB does not contain the selected wrapper compiland"
}

# Parse per-compiland procedures and CodeView diagnostic flags.  FRAMEPROC
# OptimizedForSpeed is intentionally diagnostic only: a linked PDB can contain
# optimized CRT/library modules even when the selected target units were /Od,
# and LLVM defines it as a per-frame option rather than a compilation-mode bit.
$currentModule = ""
$pendingProc = $null
$awaitingCompile3Flags = $false
$procedures = [System.Collections.Generic.List[object]]::new()
$globalCompile3Count = 0
$selectedCompile3Count = 0
$selectedLtcgCompile3Count = 0
$globalOptSpeedFrameCount = 0
$selectedOptSpeedFrameCount = 0

foreach ($line in $symbolLines) {
    if ($line -match '^\s*Mod\s+\d+\s+\|\s+`([^`]+)`') {
        $currentModule = $Matches[1]
        $pendingProc = $null
        $awaitingCompile3Flags = $false
        continue
    }

    $isSelectedModule = Test-ObjectModule -ModuleName $currentModule -ObjectNames $selectedObjects
    $isCoreModule = Test-ObjectModule -ModuleName $currentModule -ObjectNames $coreObjects

    if ($line -match 'S_COMPILE3') {
        $globalCompile3Count++
        if ($isSelectedModule) {
            $selectedCompile3Count++
        }
        $awaitingCompile3Flags = $true
        continue
    }

    if ($awaitingCompile3Flags -and $line -match 'flags\s*=\s*(.*)$') {
        if ($isSelectedModule -and $Matches[1] -match '(?i)ltcg') {
            $selectedLtcgCompile3Count++
        }
        $awaitingCompile3Flags = $false
    }

    if ($line -match 'flags\s*=.*opt speed') {
        $globalOptSpeedFrameCount++
        if ($isSelectedModule) {
            $selectedOptSpeedFrameCount++
        }
    }

    if ($line -match 'S_[A-Z0-9_]*PROC32(?:_ID)?\s+\[.*\]\s+`([^`]+)`') {
        $pendingProc = $Matches[1]
        continue
    }

    if ($null -ne $pendingProc -and $line -match 'addr\s*=\s*([0-9A-Fa-f]+):([0-9A-Fa-f]+),\s*code size\s*=\s*([0-9]+)') {
        $moduleBase = [System.IO.Path]::GetFileName($currentModule).ToLowerInvariant()
        $name = [string]$pendingProc
        $leaf = $name
        if ($leaf.Contains("::")) {
            $leaf = $leaf.Substring($leaf.LastIndexOf("::") + 2)
        }
        if ($leaf.Contains("(")) {
            $leaf = $leaf.Substring(0, $leaf.IndexOf("("))
        }

        $procedures.Add([pscustomobject]@{
            module = $currentModule
            module_basename = $moduleBase
            project_owned = $isCoreModule
            raw_name = $name
            leaf_name = $leaf
            address = ($Matches[1] + ":" + $Matches[2])
            code_size = [int]$Matches[3]
        })
        $pendingProc = $null
    }
}

if ($globalCompile3Count -eq 0) {
    throw "No S_COMPILE3 records found in linked PDB"
}
if ($selectedCompile3Count -eq 0) {
    throw "No S_COMPILE3 records found for selected Detours/wrapper compilands"
}
if ($selectedLtcgCompile3Count -ne 0) {
    throw "Selected Detours/wrapper compilands unexpectedly report LTCG"
}

$projectProcedures = @($procedures | Where-Object { $_.project_owned -and $_.code_size -gt 0 })
if ($projectProcedures.Count -eq 0) {
    throw "No Detours-owned procedure records were recovered from the PDB"
}

function Get-CollisionStats {
    param(
        [Parameter(Mandatory = $true)][object[]]$Rows,
        [Parameter(Mandatory = $true)][string]$Property
    )

    $groups = $Rows | Group-Object -Property $Property
    $collisionGroups = @($groups | Where-Object {
        @($_.Group | Select-Object -ExpandProperty address -Unique).Count -gt 1
    })
    $collisionAddresses = 0
    foreach ($group in $collisionGroups) {
        $collisionAddresses += @($group.Group | Select-Object -ExpandProperty address -Unique).Count
    }
    $allAddresses = @($Rows | Select-Object -ExpandProperty address -Unique).Count
    $rate = if ($allAddresses -gt 0) {
        [math]::Round(100.0 * $collisionAddresses / $allAddresses, 2)
    } else {
        0.0
    }

    return [ordered]@{
        source_function_addresses = $allAddresses
        unique_names = $groups.Count
        collision_groups = $collisionGroups.Count
        collision_addresses = $collisionAddresses
        collision_rate_pct = $rate
    }
}

$rawStats = Get-CollisionStats -Rows $projectProcedures -Property "raw_name"
$leafStats = Get-CollisionStats -Rows $projectProcedures -Property "leaf_name"

$summary = [ordered]@{
    schema = "decbench-msvc-qualification-v2"
    target = "detours"
    target_version = "v4.0.1"
    resolved_commit = "e4bfd6b03e50de46b47abfbd1e46b384f0c5f833"
    optimization = $Mode
    architecture = "x86_64"
    compiler = "MSVC"
    tool_paths = [ordered]@{
        cl = $clExe
        link = $linkExe
        nmake = $nmakeExe
        llvm_pdbutil = $llvmPdbutilExe
        llvm_readobj = $llvmReadobjExe
    }
    linked_image = "withdll.exe"
    pdb = "withdll.pdb"
    compile_flags = $sampleFlagsArray
    core_compile_flags = $srcFlagsArray
    link_flags = $linkFlags
    project_compiland_hits = @($moduleHits | Sort-Object -Unique)
    project_source_hits = @($sourceHits | Sort-Object -Unique)
    pdb_compile3_records_global = $globalCompile3Count
    pdb_compile3_records_selected = $selectedCompile3Count
    pdb_ltcg_compile3_records_selected = $selectedLtcgCompile3Count
    pdb_optimized_frame_records_global = $globalOptSpeedFrameCount
    pdb_optimized_frame_records_selected = $selectedOptSpeedFrameCount
    project_procedure_records = $projectProcedures.Count
    raw_pdb_name_collision = $rawStats
    leaf_name_collision_heuristic = $leafStats
    caveats = @(
        "The linked target is the upstream withdll.cpp sample manually linked against the upstream Detours static library so optimization flags remain explicit.",
        "FRAMEPROC OptimizedForSpeed counts are diagnostic only and are not used as an optimization-mode oracle.",
        "The linked PDB can contain CRT/library compilands whose optimization state is independent of the selected Detours build mode.",
        "leaf_name_collision_heuristic is diagnostic only; it is not asserted to be equivalent to DecBench's DW_AT_name identity model.",
        "PDB/CodeView qualification is not the same as the current GCC/DWARF DecBench scoring path."
    )
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $EvidenceRoot "qualification.json")
$projectProcedures | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $EvidenceRoot "project-procedures.json")

Write-Host "PASS Detours $Mode native MSVC qualification"
Write-Host "  project compilands:       $(@($moduleHits | Sort-Object -Unique).Count)"
Write-Host "  project sources:          $(@($sourceHits | Sort-Object -Unique).Count)"
Write-Host "  project procedures:       $($projectProcedures.Count)"
Write-Host "  selected S_COMPILE3:      $selectedCompile3Count"
Write-Host "  selected LTCG S_COMPILE3: $selectedLtcgCompile3Count"
Write-Host "  selected opt-speed frames:$selectedOptSpeedFrameCount"
Write-Host "  global opt-speed frames:  $globalOptSpeedFrameCount"
Write-Host "  raw-name collision:       $($rawStats.collision_rate_pct)%"
Write-Host "  leaf heuristic:           $($leafStats.collision_rate_pct)%"