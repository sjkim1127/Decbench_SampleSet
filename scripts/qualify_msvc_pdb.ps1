param(
    [Parameter(Mandatory = $true)][string]$TargetName,
    [Parameter(Mandatory = $true)]
    [ValidateSet("O0", "O2", "O2-noinline")]
    [string]$Mode,
    [Parameter(Mandatory = $true)][string]$BinaryPath,
    [Parameter(Mandatory = $true)][string]$PdbPath,
    [Parameter(Mandatory = $true)][string[]]$ProjectSourceRoots,
    [Parameter(Mandatory = $true)][string]$EvidenceRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$BinaryPath = (Resolve-Path $BinaryPath).Path
$PdbPath = (Resolve-Path $PdbPath).Path
$EvidenceRoot = [System.IO.Path]::GetFullPath($EvidenceRoot)
New-Item -ItemType Directory -Force -Path $EvidenceRoot | Out-Null
$rawDir = Join-Path $EvidenceRoot "raw"
New-Item -ItemType Directory -Force -Path $rawDir | Out-Null

function Get-NativeTool {
    param([Parameter(Mandatory = $true)][string]$Name)
    $cmd = Get-Command $Name -CommandType Application -ErrorAction Stop | Select-Object -First 1
    return $cmd.Source
}

$llvmPdbutilExe = Get-NativeTool "llvm-pdbutil.exe"
$llvmReadobjExe = Get-NativeTool "llvm-readobj.exe"

$peHeaders = Join-Path $rawDir "pe-headers.txt"
$pdbSummary = Join-Path $rawDir "pdb-summary.txt"
$pdbModules = Join-Path $rawDir "pdb-modules-files.txt"
$pdbSymbols = Join-Path $rawDir "pdb-symbols.txt"

& $llvmReadobjExe --file-headers --coff-debug-directory $BinaryPath 2>&1 | Set-Content -Encoding utf8 $peHeaders
if ($LASTEXITCODE -ne 0) { throw "llvm-readobj failed for $BinaryPath" }
$peText = Get-Content -Raw $peHeaders
if ($peText -notmatch "IMAGE_FILE_MACHINE_AMD64") {
    throw "Linked PE is not AMD64: $BinaryPath"
}

& $llvmPdbutilExe dump -summary $PdbPath 2>&1 | Set-Content -Encoding utf8 $pdbSummary
if ($LASTEXITCODE -ne 0) { throw "llvm-pdbutil summary failed for $PdbPath" }
& $llvmPdbutilExe dump -modules -files $PdbPath 2>&1 | Set-Content -Encoding utf8 $pdbModules
if ($LASTEXITCODE -ne 0) { throw "llvm-pdbutil module/file dump failed for $PdbPath" }
& $llvmPdbutilExe dump -symbols $PdbPath 2>&1 | Set-Content -Encoding utf8 $pdbSymbols
if ($LASTEXITCODE -ne 0) { throw "llvm-pdbutil symbol dump failed for $PdbPath" }

# Build a project-owned object-name index from the selected source roots.  This is
# intentionally target-source based rather than "all PDB modules", so CRT/vendor
# compilands stay outside the project metric.  CMake/Ninja commonly names objects
# foo.cpp.obj while MSBuild commonly uses foo.obj, so retain both spellings.
$projectSources = [System.Collections.Generic.List[string]]::new()
$objectNeedles = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($rootInput in $ProjectSourceRoots) {
    $root = (Resolve-Path $rootInput).Path
    Get-ChildItem -Path $root -Recurse -File | Where-Object {
        $_.Extension -in @(".c", ".cc", ".cpp", ".cxx", ".c++")
    } | ForEach-Object {
        $projectSources.Add($_.FullName)
        [void]$objectNeedles.Add(($_.Name + ".obj"))
        [void]$objectNeedles.Add(($_.BaseName + ".obj"))
    }
}
if ($projectSources.Count -eq 0) {
    throw "No project source files found under: $($ProjectSourceRoots -join ', ')"
}

function Test-ProjectModule {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$ModuleName
    )
    if ([string]::IsNullOrWhiteSpace($ModuleName)) { return $false }
    $lower = $ModuleName.ToLowerInvariant()
    foreach ($needleValue in $objectNeedles) {
        $needle = $needleValue.ToLowerInvariant()
        if ($lower -eq $needle -or
            $lower.EndsWith("\$needle") -or
            $lower.EndsWith("/$needle") -or
            $lower.Contains("($needle)")) {
            return $true
        }
    }
    return $false
}

$symbolLines = Get-Content $pdbSymbols
$currentModule = ""
$pendingProc = $null
$awaitingCompile3Flags = $false
$procedures = [System.Collections.Generic.List[object]]::new()
$selectedModules = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
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
        if (Test-ProjectModule -ModuleName $currentModule) {
            [void]$selectedModules.Add($currentModule)
        }
        continue
    }

    $isProjectModule = Test-ProjectModule -ModuleName $currentModule

    if ($line -match 'S_COMPILE3') {
        $globalCompile3Count++
        if ($isProjectModule) { $selectedCompile3Count++ }
        $awaitingCompile3Flags = $true
        continue
    }

    if ($awaitingCompile3Flags -and $line -match 'flags\s*=\s*(.*)$') {
        if ($isProjectModule -and $Matches[1] -match '(?i)ltcg') {
            $selectedLtcgCompile3Count++
        }
        $awaitingCompile3Flags = $false
    }

    if ($line -match 'flags\s*=.*opt speed') {
        $globalOptSpeedFrameCount++
        if ($isProjectModule) { $selectedOptSpeedFrameCount++ }
    }

    if ($line -match 'S_[A-Z0-9_]*PROC32(?:_ID)?\s+\[.*\]\s+`([^`]+)`') {
        $pendingProc = $Matches[1]
        continue
    }

    if ($null -ne $pendingProc -and $line -match 'addr\s*=\s*([0-9A-Fa-f]+):([0-9A-Fa-f]+),\s*code size\s*=\s*([0-9]+)') {
        $name = [string]$pendingProc
        $leaf = $name
        if ($leaf.Contains("::")) { $leaf = $leaf.Substring($leaf.LastIndexOf("::") + 2) }
        if ($leaf.Contains("(")) { $leaf = $leaf.Substring(0, $leaf.IndexOf("(")) }

        $procedures.Add([pscustomobject]@{
            module = $currentModule
            project_owned = $isProjectModule
            raw_name = $name
            leaf_name = $leaf
            address = ($Matches[1] + ":" + $Matches[2])
            code_size = [int]$Matches[3]
        })
        $pendingProc = $null
    }
}

if ($selectedModules.Count -eq 0) {
    throw "No project-owned PDB modules matched the selected source roots"
}
if ($globalCompile3Count -eq 0) {
    throw "No S_COMPILE3 records found in linked PDB"
}
if ($selectedCompile3Count -eq 0) {
    throw "No S_COMPILE3 records found for project-owned compilands"
}
if ($selectedLtcgCompile3Count -ne 0) {
    throw "Project-owned compilands unexpectedly report LTCG"
}

$projectProcedures = @($procedures | Where-Object { $_.project_owned -and $_.code_size -gt 0 })
if ($projectProcedures.Count -eq 0) {
    throw "No project-owned procedure records were recovered from the PDB"
}

function Get-CollisionStats {
    param(
        [Parameter(Mandatory = $true)][object[]]$Rows,
        [Parameter(Mandatory = $true)][string]$Property
    )
    $groups = @($Rows | Group-Object -Property $Property)
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
    } else { 0.0 }

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
    schema = "decbench-native-msvc-pdb-qualification-v1"
    target = $TargetName
    optimization = $Mode
    architecture = "x86_64"
    linked_image = [System.IO.Path]::GetFileName($BinaryPath)
    pdb = [System.IO.Path]::GetFileName($PdbPath)
    ground_truth = "native MSVC PDB / CodeView"
    project_source_file_count = $projectSources.Count
    project_object_name_candidates = @($objectNeedles | Sort-Object)
    project_compiland_count = $selectedModules.Count
    project_compilands = @($selectedModules | Sort-Object)
    pdb_compile3_records_global = $globalCompile3Count
    pdb_compile3_records_selected = $selectedCompile3Count
    pdb_ltcg_compile3_records_selected = $selectedLtcgCompile3Count
    pdb_optimized_frame_records_global = $globalOptSpeedFrameCount
    pdb_optimized_frame_records_selected = $selectedOptSpeedFrameCount
    project_procedure_records = $projectProcedures.Count
    raw_pdb_name_collision = $rawStats
    leaf_name_collision_heuristic = $leafStats
    caveats = @(
        "The PDB raw-name collision metric is a CodeView diagnostic and is not asserted to be numerically equivalent to DecBench's DWARF DW_AT_name metric.",
        "Project ownership is determined from object-module names derived from the selected project source roots; CRT and unrelated vendor modules are excluded.",
        "FRAMEPROC OptimizedForSpeed counts are diagnostic only and are not used as the optimization-mode oracle.",
        "This is target/oracle qualification, not an end-to-end DecBench GED/type/byte benchmark run."
    )
}

$summary | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $EvidenceRoot "qualification.json")
$projectProcedures | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $EvidenceRoot "project-procedures.json")

Write-Host "PASS $TargetName $Mode native MSVC/PDB oracle qualification"
Write-Host "  project source files:      $($projectSources.Count)"
Write-Host "  project compilands:        $($selectedModules.Count)"
Write-Host "  project procedures:        $($projectProcedures.Count)"
Write-Host "  selected S_COMPILE3:       $selectedCompile3Count"
Write-Host "  selected LTCG S_COMPILE3:  $selectedLtcgCompile3Count"
Write-Host "  raw-name collision:        $($rawStats.collision_rate_pct)%"
Write-Host "  leaf-name heuristic:       $($leafStats.collision_rate_pct)%"
