param([Parameter(Mandatory=$true)][ValidateSet('O0','O2','O2-noinline')][string]$Mode)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$out=Join-Path $PWD "_qualification/cpp-slice/$Mode"
New-Item -ItemType Directory -Force $out | Out-Null
$source=(Resolve-Path targets/qualification-controls/reference_fields.cpp).Path
$compiler=(Get-Command cl.exe -CommandType Application).Source
$linker=(Get-Command link.exe -CommandType Application).Source
$flags=@('/nologo','/std:c++17','/c','/Z7','/GS-','/GR-','/EHsc','/GL-','/Gy','/Zo')
switch($Mode) {
  'O0' { $flags+=@('/Od','/Ob0') }
  'O2' { $flags+=@('/O2') }
  'O2-noinline' { $flags+=@('/O2','/Ob0') }
}
$compile=@($flags)+@('/Bv',$source,"/Fo$out/original.obj")
& $compiler @compile 2>&1 | Tee-Object "$out/compile.log"
if($LASTEXITCODE -ne 0) { throw 'Original bounded C++ compilation failed' }
$preprocess=@($flags)+@($source,'/P',"/Fi$out/original.ii")
& $compiler @preprocess 2>&1 | Tee-Object "$out/preprocess.log"
if($LASTEXITCODE -ne 0) { throw 'Original bounded C++ preprocessing failed' }
$link=@('/NOLOGO',"$out/original.obj",'/ENTRY:entry','/SUBSYSTEM:CONSOLE','/NODEFAULTLIB','/DEBUG:FULL','/INCREMENTAL:NO','/OPT:NOREF','/OPT:NOICF',"/OUT:$out/original.exe","/PDB:$out/original.pdb")
& $linker @link 2>&1 | Tee-Object "$out/link.log"
if($LASTEXITCODE -ne 0) { throw 'Original bounded C++ link failed' }
& $compiler @flags '/TP' "$out/original.ii" '/Zs' 2>&1 | Tee-Object "$out/preprocessed-syntax.log"
if($LASTEXITCODE -ne 0) { throw 'Original preprocessed TU fails native compiler syntax check' }
Copy-Item $source "$out/original.cpp"
@{
  schema='native-msvc-cpp-slice-v1'
  role='controlled compiler fixture; not the scored corpus'
  workflow_commit=$env:GITHUB_SHA
  optimization=$Mode
  compiler=$compiler
  linker=$linker
  compile_argv=@($compiler)+$compile
  preprocess_argv=@($compiler)+$preprocess
  link_argv=@($linker)+$link
  source_sha256=(Get-FileHash $source -Algorithm SHA256).Hash.ToLowerInvariant()
  qualified=$false
  scoring_ready=$false
  supported='free C++ functions with POD field reads, lvalue references and a branch; no implicit lifetime or exception claims'
} | ConvertTo-Json -Depth 12 | Set-Content "$out/provenance.json"
