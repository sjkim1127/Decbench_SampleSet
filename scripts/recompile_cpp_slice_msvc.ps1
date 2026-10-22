param([Parameter(Mandatory=$true)][ValidateSet('O0','O2','O2-noinline')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$plan=Get-Content targets/qualification-controls/recovered-msvc.json -Raw | ConvertFrom-Json
$original=Join-Path $PWD "_qualification/frozen-original/$Mode"
$out=Join-Path $PWD "_qualification/recompiled-slice/$Mode"
New-Item -ItemType Directory -Force $out | Out-Null
$provenance=Get-Content "$original/provenance.json" -Raw | ConvertFrom-Json
$compiler=(Get-Command cl.exe -CommandType Application | Select-Object -First 1).Source
$linker=Join-Path (Split-Path -Parent $compiler) 'link.exe'
if ($compiler -ne $provenance.compiler -or $linker -ne $provenance.linker) {
  throw 'MSVC compiler/toolset path differs from frozen original'
}
$version=(Get-Item -LiteralPath $compiler).VersionInfo.FileVersion
$originalLog=Get-Content "$original/compile.log" -Raw
if (-not $originalLog.Contains("Version $version")) { throw 'MSVC version differs from frozen original' }
$flags=@('/nologo','/std:c++17','/c','/Z7','/GS-','/GR-','/EHsc','/GL-','/Gy','/Zo')
switch($Mode) {
  'O0' { $flags+=@('/Od','/Ob0') }
  'O2' { $flags+=@('/O2') }
  'O2-noinline' { $flags+=@('/O2','/Ob0') }
}
$rows=@()
foreach ($row in $plan.rows | Where-Object { $_.mode -eq $Mode }) {
  $dir=Join-Path $out $row.id
  New-Item -ItemType Directory -Force $dir | Out-Null
  $source=Join-Path $dir 'recovered.cpp'
  ($plan.common_prefix + "`nextern `"C`" {`n" + $row.code + "`n}`n") | Set-Content -Encoding utf8NoBOM $source
  $compile=@($flags)+@('/Bv',$source,"/Fo$dir/recovered.obj")
  & $compiler @compile 2>&1 | Tee-Object "$dir/compile.log"
  $compileExit=$LASTEXITCODE
  $linkExit=$null
  $link=@('/NOLOGO',"$dir/recovered.obj","/ENTRY:$($row.function)",'/SUBSYSTEM:CONSOLE','/NODEFAULTLIB','/DEBUG:FULL','/INCREMENTAL:NO','/OPT:NOREF','/OPT:NOICF',"/OUT:$dir/recovered.exe","/PDB:$dir/recovered.pdb")
  if ($compileExit -eq 0) {
    & $linker @link 2>&1 | Tee-Object "$dir/link.log"
    $linkExit=$LASTEXITCODE
  }
  $rows+=@{
    id=$row.id; mode=$Mode; tool=$row.tool; address=$row.address; function=$row.function
    code_sha256=$row.code_sha256; source_sha256=(Get-FileHash $source -Algorithm SHA256).Hash.ToLowerInvariant()
    compile_exit=$compileExit; link_exit=$linkExit
    compile_argv=@($compiler)+$compile; link_argv=@($linker)+$link
  }
}
@{
  schema=$plan.schema; original_run=$plan.original_run; workflow_commit=$env:GITHUB_SHA
  compiler=$compiler; compiler_version=$version
  compiler_sha256=(Get-FileHash $compiler -Algorithm SHA256).Hash.ToLowerInvariant()
  linker_sha256=(Get-FileHash $linker -Algorithm SHA256).Hash.ToLowerInvariant()
  original_binary_sha256=(Get-FileHash "$original/original.exe" -Algorithm SHA256).Hash.ToLowerInvariant()
  original_source_sha256=$provenance.source_sha256
  plan_sha256=(Get-FileHash targets/qualification-controls/recovered-msvc.json -Algorithm SHA256).Hash.ToLowerInvariant()
  common_prefix=$plan.common_prefix; linkage_wrapper='extern C: transport linkage only'
  original_compiler_version_verified=$true; official_score=$false; execution_parity=$false; rows=$rows
} | ConvertTo-Json -Depth 12 | Set-Content "$out/results.json"
