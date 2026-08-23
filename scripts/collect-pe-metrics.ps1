param(
    [Parameter(Mandatory = $true)] [string] $Root,
    [Parameter(Mandatory = $true)] [string] $ExecutablePattern,
    [Parameter(Mandatory = $true)] [string] $OutDir,
    [string] $TargetName = "unknown"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$rootItem = Get-Item $Root
$llvmPdbUtil = Get-Command llvm-pdbutil -ErrorAction SilentlyContinue
$dumpbin = Get-Command dumpbin -ErrorAction SilentlyContinue

$executables = Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like $ExecutablePattern } |
    Sort-Object Length -Descending

$rows = @()
foreach ($exe in $executables) {
    $hash = (Get-FileHash -Algorithm SHA256 -Path $exe.FullName).Hash
    $pdbCandidates = @(
        Join-Path $exe.DirectoryName ($exe.BaseName + ".pdb")
    )

    $pdb = $null
    foreach ($candidate in $pdbCandidates) {
        if (Test-Path $candidate) {
            $pdb = Get-Item $candidate
            break
        }
    }

    if (-not $pdb) {
        $pdb = Get-ChildItem -Path $exe.DirectoryName -Recurse -File -Filter ($exe.BaseName + ".pdb") -ErrorAction SilentlyContinue |
            Select-Object -First 1
    }

    $procCount = $null
    $pdbError = $null
    if ($pdb -and $llvmPdbUtil) {
        try {
            $symbolDump = & $llvmPdbUtil.Source dump -symbols $pdb.FullName 2>&1
            $procCount = @($symbolDump | Select-String -Pattern 'S_(G|L)PROC32').Count
        }
        catch {
            $pdbError = $_.Exception.Message
        }
    }

    $machine = $null
    if ($dumpbin) {
        try {
            $headers = & $dumpbin.Source /headers $exe.FullName 2>&1
            $machineLine = $headers | Select-String -Pattern 'machine \(' | Select-Object -First 1
            if ($machineLine) { $machine = $machineLine.Line.Trim() }
        }
        catch {}
    }

    $rows += [PSCustomObject]@{
        target = $TargetName
        executable = $exe.FullName.Substring($rootItem.FullName.Length).TrimStart('\','/')
        bytes = $exe.Length
        sha256 = $hash
        machine = $machine
        pdb = if ($pdb) { $pdb.FullName.Substring($rootItem.FullName.Length).TrimStart('\','/') } else { $null }
        pdb_bytes = if ($pdb) { $pdb.Length } else { $null }
        pdb_proc_symbol_count = $procCount
        pdb_error = $pdbError
        llvm_pdbutil_available = [bool]$llvmPdbUtil
    }
}

$rows | Export-Csv -NoTypeInformation -Path (Join-Path $OutDir "pe-metrics.csv")
$rows | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $OutDir "pe-metrics.json")

$summary = @()
$summary += "target=$TargetName"
$summary += "root=$($rootItem.FullName)"
$summary += "pattern=$ExecutablePattern"
$summary += "matched_executables=$($executables.Count)"
$summary += "llvm_pdbutil_available=$([bool]$llvmPdbUtil)"
$summary += "dumpbin_available=$([bool]$dumpbin)"
$summary | Set-Content -Encoding UTF8 (Join-Path $OutDir "summary.txt")

$rows | Format-Table -AutoSize
