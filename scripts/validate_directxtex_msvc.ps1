param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("O0", "O2", "O2-noinline")]
    [string]$Mode,
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [Parameter(Mandatory = $true)][string]$EvidenceRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$SourceRoot = (Resolve-Path $SourceRoot).Path
$EvidenceRoot = [System.IO.Path]::GetFullPath($EvidenceRoot)
New-Item -ItemType Directory -Force -Path $EvidenceRoot | Out-Null
$binaryEvidence = Join-Path $EvidenceRoot "binary"
New-Item -ItemType Directory -Force -Path $binaryEvidence | Out-Null

$modeFlags = @{
    "O0"          = @("/Od", "/Ob0", "/Zi")
    "O2"          = @("/O2", "/Zi")
    "O2-noinline" = @("/O2", "/Ob0", "/Zi")
}
$compileFlags = @("/nologo", "/EHsc", "/GL-") + $modeFlags[$Mode]
$linkFlags = @("/DEBUG:FULL", "/INCREMENTAL:NO", "/LTCG:OFF")

function Get-NativeTool {
    param([Parameter(Mandatory = $true)][string]$Name)
    $cmd = Get-Command $Name -CommandType Application -ErrorAction Stop | Select-Object -First 1
    return $cmd.Source
}
function Invoke-Logged {
    param(
        [Parameter(Mandatory = $true)][string]$Exe,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][string]$LogPath
    )
    Add-Content -Encoding utf8 $LogPath "`n===== $Label ====="
    Add-Content -Encoding utf8 $LogPath ("$Exe " + ($Arguments -join " "))
    & $Exe @Arguments 2>&1 | Tee-Object -FilePath $LogPath -Append
    if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE" }
}

$clExe = Get-NativeTool "cl.exe"
$linkExe = Get-NativeTool "link.exe"
$cmakeExe = Get-NativeTool "cmake.exe"
$ninjaExe = Get-NativeTool "ninja.exe"
$llvmPdbutilExe = Get-NativeTool "llvm-pdbutil.exe"
$llvmReadobjExe = Get-NativeTool "llvm-readobj.exe"
if ($clExe -notmatch "Microsoft Visual Studio") { throw "cl.exe did not resolve to Visual Studio: $clExe" }
if ($linkExe -notmatch "Microsoft Visual Studio") { throw "link.exe did not resolve to Visual Studio: $linkExe" }

$buildLog = Join-Path $EvidenceRoot "build.log"
$commandLog = Join-Path $EvidenceRoot "commands.txt"
$buildDir = Join-Path $EvidenceRoot "build-tree"
if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }

@(
    "target=Microsoft DirectXTex may2026",
    "mode=$Mode",
    "source_revision=4feb3e11a020f35b796fc769a74216a555d4f5ef",
    "cl=$clExe",
    "link=$linkExe",
    "cmake=$cmakeExe",
    "ninja=$ninjaExe",
    "llvm_pdbutil=$llvmPdbutilExe",
    "llvm_readobj=$llvmReadobjExe",
    "compile_flags=$($compileFlags -join ' ')",
    "link_flags=$($linkFlags -join ' ')"
) | Set-Content -Encoding utf8 $commandLog

$configureArgs = @(
    "-S", $SourceRoot,
    "-B", $buildDir,
    "-G", "Ninja",
    "-DCMAKE_BUILD_TYPE=DecBench",
    "-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF",
    "-DCMAKE_CXX_FLAGS=$($compileFlags -join ' ')",
    "-DCMAKE_SHARED_LINKER_FLAGS=$($linkFlags -join ' ')",
    "-DBUILD_SHARED_LIBS=ON",
    "-DBUILD_TOOLS=OFF",
    "-DBUILD_SAMPLE=OFF",
    "-DBUILD_DX11=OFF",
    "-DBUILD_DX12=OFF",
    "-DBC_USE_OPENMP=OFF",
    "-DENABLE_OPENEXR_SUPPORT=OFF",
    "-DENABLE_LIBJPEG_SUPPORT=OFF",
    "-DENABLE_LIBPNG_SUPPORT=OFF"
)
Invoke-Logged -Exe $cmakeExe -Arguments $configureArgs -Label "Configure DirectXTex" -LogPath $buildLog
Invoke-Logged -Exe $cmakeExe -Arguments @("--build", $buildDir, "--target", "DirectXTex", "--verbose") -Label "Build DirectXTex" -LogPath $buildLog

$buildText = Get-Content -Raw $buildLog
switch ($Mode) {
    "O0" {
        if ($buildText -notmatch '(?i)/Od' -or $buildText -notmatch '(?i)/Ob0') {
            throw "O0 build log does not contain /Od and /Ob0"
        }
    }
    "O2" {
        if ($buildText -notmatch '(?i)/O2') { throw "O2 build log does not contain /O2" }
    }
    "O2-noinline" {
        if ($buildText -notmatch '(?i)/O2' -or $buildText -notmatch '(?i)/Ob0') {
            throw "O2-noinline build log does not contain /O2 and /Ob0"
        }
    }
}

# Verbose CMake/MSVC logs can mention both inherited/evaluated /GL state and the
# explicit /GL- override. Raw textual presence of /GL is therefore diagnostic,
# not a sufficient proof that LTCG reached the emitted project compilands.
# Require explicit disable switches and use the linked PDB S_COMPILE3 flags as the
# substantive gate in qualify_msvc_pdb.ps1.
if ($buildText -notmatch '(?i)/GL-') { throw "Build log does not contain explicit /GL- override" }
if ($buildText -notmatch '(?i)/LTCG:OFF') { throw "Build log does not contain explicit /LTCG:OFF override" }
$optimizationSwitchAudit = Join-Path $EvidenceRoot "optimization-switch-audit.txt"
@(Get-Content $buildLog | Where-Object { $_ -match '(?i)/(?:GL-?|LTCG(?::OFF)?)\b' }) |
    Set-Content -Encoding utf8 $optimizationSwitchAudit

$dlls = @(Get-ChildItem -Path $buildDir -Recurse -File -Filter "DirectXTex.dll")
if ($dlls.Count -ne 1) { throw "Expected exactly one DirectXTex.dll, found $($dlls.Count)" }
$dll = $dlls[0].FullName
$pdb = Join-Path $dlls[0].DirectoryName "DirectXTex.pdb"
if (-not (Test-Path $pdb)) {
    $pdbs = @(Get-ChildItem -Path $buildDir -Recurse -File -Filter "DirectXTex.pdb" | Where-Object { $_.FullName -notmatch '\\.dir\\' })
    if ($pdbs.Count -ne 1) { throw "Could not identify exactly one linked DirectXTex.pdb; found $($pdbs.Count)" }
    $pdb = $pdbs[0].FullName
}

Copy-Item -Force $dll (Join-Path $binaryEvidence "DirectXTex.dll")
Copy-Item -Force $pdb (Join-Path $binaryEvidence "DirectXTex.pdb")

$qualifier = Join-Path $PSScriptRoot "qualify_msvc_pdb.ps1"
$qualifyArgs = @{
    TargetName = "Microsoft DirectXTex may2026"
    Mode = $Mode
    BinaryPath = $dll
    PdbPath = $pdb
    ProjectSourceRoots = @((Join-Path $SourceRoot "DirectXTex"))
    EvidenceRoot = $EvidenceRoot
}
& $qualifier @qualifyArgs
if ($LASTEXITCODE -ne 0) { throw "PDB qualification failed" }

Write-Host "PASS DirectXTex $Mode native MSVC build + PDB qualification"
