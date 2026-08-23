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
    "O0"          = @("/Od", "/Ob0", "/Zi", "/GL-")
    "O2"          = @("/O2", "/Zi", "/GL-")
    "O2-noinline" = @("/O2", "/Ob0", "/Zi", "/GL-")
}
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
function Set-XmlChildText {
    param(
        [Parameter(Mandatory = $true)][System.Xml.XmlElement]$Parent,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$Value,
        [Parameter(Mandatory = $true)][System.Xml.XmlNamespaceManager]$Ns
    )
    $node = $Parent.SelectSingleNode("m:$Name", $Ns)
    if ($null -eq $node) {
        $node = $Parent.OwnerDocument.CreateElement($Name, $Parent.NamespaceURI)
        [void]$Parent.AppendChild($node)
    }
    $node.InnerText = $Value
}

$clExe = Get-NativeTool "cl.exe"
$linkExe = Get-NativeTool "link.exe"
$msbuildExe = Get-NativeTool "msbuild.exe"
$nugetExe = Get-NativeTool "nuget.exe"
$llvmPdbutilExe = Get-NativeTool "llvm-pdbutil.exe"
$llvmReadobjExe = Get-NativeTool "llvm-readobj.exe"
if ($clExe -notmatch "Microsoft Visual Studio") { throw "cl.exe did not resolve to Visual Studio: $clExe" }
if ($linkExe -notmatch "Microsoft Visual Studio") { throw "link.exe did not resolve to Visual Studio: $linkExe" }
if ($msbuildExe -notmatch "Microsoft Visual Studio") { throw "msbuild.exe did not resolve to Visual Studio: $msbuildExe" }

$buildLog = Join-Path $EvidenceRoot "build.log"
$commandLog = Join-Path $EvidenceRoot "commands.txt"
$projectPath = Join-Path $SourceRoot "WinSparkle.vcxproj"
$solutionPath = Join-Path $SourceRoot "WinSparkle.sln"
if (-not (Test-Path $projectPath)) { throw "WinSparkle.vcxproj not found" }
if (-not (Test-Path $solutionPath)) { throw "WinSparkle.sln not found" }

# Patch only the working checkout.  The pinned project has Release|x64 WPO/LTCG
# enabled upstream; target qualification must force controlled compiler modes and
# retain a full PDB without link-time code generation.
[xml]$xml = Get-Content -Raw $projectPath
$ns = [System.Xml.XmlNamespaceManager]::new($xml.NameTable)
$ns.AddNamespace("m", "http://schemas.microsoft.com/developer/msbuild/2003")

# Under StrictMode, PowerShell's XML property adapter throws when an optional XML
# attribute is absent. MSBuild files legitimately contain PropertyGroup elements
# without Condition/Label attributes, so use XmlElement.GetAttribute().
$propertyGroups = @($xml.SelectNodes("//m:PropertyGroup", $ns) | Where-Object {
    $condition = $_.GetAttribute("Condition")
    -not [string]::IsNullOrWhiteSpace($condition) -and $condition -match "Release\|x64"
})
if ($propertyGroups.Count -eq 0) { throw "Could not find Release|x64 property groups" }
foreach ($pg in $propertyGroups) {
    $label = $pg.GetAttribute("Label")
    if ($label -eq "Configuration" -or $null -ne $pg.SelectSingleNode("m:WholeProgramOptimization", $ns)) {
        Set-XmlChildText -Parent $pg -Name "WholeProgramOptimization" -Value "false" -Ns $ns
    }
    if ($null -ne $pg.SelectSingleNode("m:LinkIncremental", $ns)) {
        Set-XmlChildText -Parent $pg -Name "LinkIncremental" -Value "false" -Ns $ns
    }
}

$itemGroups = @($xml.SelectNodes("//m:ItemDefinitionGroup", $ns) | Where-Object {
    $condition = $_.GetAttribute("Condition")
    -not [string]::IsNullOrWhiteSpace($condition) -and $condition -match "Release\|x64"
})
if ($itemGroups.Count -ne 1) { throw "Expected one Release|x64 ItemDefinitionGroup, found $($itemGroups.Count)" }
$itemGroup = [System.Xml.XmlElement]$itemGroups[0]
$cl = [System.Xml.XmlElement]$itemGroup.SelectSingleNode("m:ClCompile", $ns)
$link = [System.Xml.XmlElement]$itemGroup.SelectSingleNode("m:Link", $ns)
if ($null -eq $cl -or $null -eq $link) { throw "Release|x64 compile/link definitions missing" }

switch ($Mode) {
    "O0" {
        Set-XmlChildText -Parent $cl -Name "Optimization" -Value "Disabled" -Ns $ns
        Set-XmlChildText -Parent $cl -Name "InlineFunctionExpansion" -Value "Disabled" -Ns $ns
    }
    "O2" {
        Set-XmlChildText -Parent $cl -Name "Optimization" -Value "MaxSpeed" -Ns $ns
        Set-XmlChildText -Parent $cl -Name "InlineFunctionExpansion" -Value "AnySuitable" -Ns $ns
    }
    "O2-noinline" {
        Set-XmlChildText -Parent $cl -Name "Optimization" -Value "MaxSpeed" -Ns $ns
        Set-XmlChildText -Parent $cl -Name "InlineFunctionExpansion" -Value "Disabled" -Ns $ns
    }
}
Set-XmlChildText -Parent $cl -Name "DebugInformationFormat" -Value "ProgramDatabase" -Ns $ns
Set-XmlChildText -Parent $cl -Name "WholeProgramOptimization" -Value "false" -Ns $ns
Set-XmlChildText -Parent $cl -Name "AdditionalOptions" -Value ("%(AdditionalOptions) " + ($modeFlags[$Mode] -join " ")) -Ns $ns
Set-XmlChildText -Parent $link -Name "GenerateDebugInformation" -Value "true" -Ns $ns
Set-XmlChildText -Parent $link -Name "LinkTimeCodeGeneration" -Value "Default" -Ns $ns
Set-XmlChildText -Parent $link -Name "EnableCOMDATFolding" -Value "false" -Ns $ns
Set-XmlChildText -Parent $link -Name "OptimizeReferences" -Value "false" -Ns $ns
Set-XmlChildText -Parent $link -Name "AdditionalOptions" -Value ("%(AdditionalOptions) " + ($linkFlags -join " ")) -Ns $ns
$xml.Save($projectPath)
Copy-Item -Force $projectPath (Join-Path $EvidenceRoot "WinSparkle.decbench.vcxproj")

@(
    "target=WinSparkle v0.9.4",
    "mode=$Mode",
    "source_revision=a8986caf620262f7d4581b241436ceaa0cc9370f",
    "cl=$clExe",
    "link=$linkExe",
    "msbuild=$msbuildExe",
    "nuget=$nugetExe",
    "llvm_pdbutil=$llvmPdbutilExe",
    "llvm_readobj=$llvmReadobjExe",
    "compile_override=$($modeFlags[$Mode] -join ' ')",
    "link_override=$($linkFlags -join ' ')"
) | Set-Content -Encoding utf8 $commandLog

Invoke-Logged -Exe $nugetExe -Arguments @("restore", $solutionPath, "-NonInteractive") -Label "Restore WinSparkle NuGet packages" -LogPath $buildLog
Invoke-Logged -Exe $msbuildExe -Arguments @(
    $projectPath,
    "/m",
    "/t:Rebuild",
    "/p:Configuration=Release",
    "/p:Platform=x64",
    "/p:WholeProgramOptimization=false",
    "/v:detailed",
    "/clp:ShowCommandLine;Summary"
) -Label "Build WinSparkle" -LogPath $buildLog

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

# MSBuild detailed output can contain both the upstream /GL setting and the later
# /GL- override (and can also print evaluated properties that are not effective
# compiler switches).  Therefore raw textual presence of /GL is not a sound gate.
# Require the explicit disable switches here, preserve all GL/LTCG lines for audit,
# and let qualify_msvc_pdb.ps1 enforce the substantive oracle: every selected
# project compiland must have an S_COMPILE3 record with no LTCG flag.
if ($buildText -notmatch '(?i)/GL-') { throw "Build log does not contain explicit /GL- override" }
if ($buildText -notmatch '(?i)/LTCG:OFF') { throw "Build log does not contain explicit /LTCG:OFF override" }
$optimizationSwitchAudit = Join-Path $EvidenceRoot "optimization-switch-audit.txt"
@(Get-Content $buildLog | Where-Object { $_ -match '(?i)/(?:GL-?|LTCG(?::OFF)?)\b' }) |
    Set-Content -Encoding utf8 $optimizationSwitchAudit

$dllPath = Join-Path $SourceRoot "x64\Release\WinSparkle.dll"
$pdbPath = Join-Path $SourceRoot "x64\Release\WinSparkle.pdb"
if (-not (Test-Path $dllPath)) {
    $dlls = @(Get-ChildItem -Path $SourceRoot -Recurse -File -Filter "WinSparkle.dll")
    if ($dlls.Count -ne 1) { throw "Expected one WinSparkle.dll, found $($dlls.Count)" }
    $dllPath = $dlls[0].FullName
}
if (-not (Test-Path $pdbPath)) {
    $pdbs = @(Get-ChildItem -Path $SourceRoot -Recurse -File -Filter "WinSparkle.pdb")
    if ($pdbs.Count -ne 1) { throw "Expected one WinSparkle.pdb, found $($pdbs.Count)" }
    $pdbPath = $pdbs[0].FullName
}

Copy-Item -Force $dllPath (Join-Path $binaryEvidence "WinSparkle.dll")
Copy-Item -Force $pdbPath (Join-Path $binaryEvidence "WinSparkle.pdb")

$qualifier = Join-Path $PSScriptRoot "qualify_msvc_pdb.ps1"
$qualifyArgs = @{
    TargetName = "WinSparkle v0.9.4"
    Mode = $Mode
    BinaryPath = $dllPath
    PdbPath = $pdbPath
    ProjectSourceRoots = @((Join-Path $SourceRoot "src"))
    EvidenceRoot = $EvidenceRoot
}
& $qualifier @qualifyArgs
if ($LASTEXITCODE -ne 0) { throw "PDB qualification failed" }

Write-Host "PASS WinSparkle $Mode native MSVC build + PDB qualification"
