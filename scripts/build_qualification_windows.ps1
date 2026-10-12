param(
  [Parameter(Mandatory=$true)][ValidateSet('ninja','snappy','OpenCC','tracy')][string]$Project,
  [Parameter(Mandatory=$true)][ValidateSet('O0','O2','O2-noinline')][string]$Mode
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$plan=Get-Content -Raw targets/qualification-v2/pilot.json | ConvertFrom-Json
$cell=$plan.cells | Where-Object { $_.platform -eq 'windows' -and $_.project -eq $Project }
if (-not $cell -or -not $cell.source_revision) { throw 'Missing pinned source cell' }
$src=Join-Path $PWD "_qualification/src/$Project"
$build=Join-Path $PWD "_qualification/build/$Project/$Mode"
$out=Join-Path $PWD "_qualification/evidence/$Project/$Mode"
New-Item -ItemType Directory -Force $src,$build,$out | Out-Null
& git init -q $src
& git -C $src remote add origin "https://github.com/$($cell.source_repository).git"
& git -C $src fetch -q --depth 1 origin $cell.source_revision
if ($LASTEXITCODE -ne 0) { throw 'Pinned source fetch failed' }
& git -C $src checkout -q FETCH_HEAD
if ((& git -C $src rev-parse HEAD).Trim() -ne $cell.source_revision) { throw 'Source revision mismatch' }
& git -C $src submodule update --init --recursive --depth 1
if ($LASTEXITCODE -ne 0) { throw 'Pinned submodule checkout failed' }
& git -C $src archive --format=tar.gz --output "$out/original.tar.gz" HEAD
$opt=@{'O0'='/Od /Ob0';'O2'='/O2';'O2-noinline'='/O2 /Ob0'}[$Mode]
$flags="/nologo /EHsc /Zi $opt"
$source=$src
$target=$Project
if ($Project -eq 'tracy') { $source=Join-Path $src 'profiler';$target='tracy-profiler' }
$configure=@('-S',$source,'-B',$build,'-G','Ninja','-DCMAKE_BUILD_TYPE=Qualification',"-DCMAKE_C_FLAGS=$flags","-DCMAKE_CXX_FLAGS=$flags",'-DCMAKE_C_FLAGS_QUALIFICATION=/DNDEBUG','-DCMAKE_CXX_FLAGS_QUALIFICATION=/DNDEBUG','-DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF','-DCMAKE_EXPORT_COMPILE_COMMANDS=ON','-DCMAKE_EXE_LINKER_FLAGS=/DEBUG:FULL /INCREMENTAL:NO /OPT:REF /OPT:NOICF','-DCMAKE_SHARED_LINKER_FLAGS=/DEBUG:FULL /INCREMENTAL:NO /OPT:REF /OPT:NOICF','-DBUILD_TESTING=OFF')
if ($Project -eq 'snappy') { $configure+=@('-DBUILD_SHARED_LIBS=ON','-DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON','-DSNAPPY_BUILD_TESTS=OFF','-DSNAPPY_BUILD_BENCHMARKS=OFF') }
if ($Project -eq 'OpenCC') { $configure+=@('-DBUILD_SHARED_LIBS=OFF','-DENABLE_GTEST=OFF','-DENABLE_BENCHMARK=OFF','-DBUILD_PYTHON=OFF','-DBUILD_OPENCC_JIEBA_PLUGIN=OFF');$target='opencc' }
@{ source_revision=$cell.source_revision;source_repository=$cell.source_repository;cmake_argv=$configure;optimization=$Mode;environment=@{runner=$env:ImageOS;image_version=$env:ImageVersion} } | ConvertTo-Json -Depth 8 | Set-Content "$out/build-provenance.json"
& cmake @configure 2>&1 | Tee-Object "$out/build.log"
if ($LASTEXITCODE -ne 0) { throw 'CMake configure failed' }
& cmake --build $build --target $target --parallel 2 2>&1 | Tee-Object -Append "$out/build.log"
if ($LASTEXITCODE -ne 0) { throw 'CMake build failed' }
$extension=if ($Project -eq 'snappy') {'.dll'} else {'.exe'}
$binary=Get-ChildItem $build -Recurse -File | Where-Object { $_.Name -eq ($target+$extension) }
if (@($binary).Count -ne 1) { throw 'Selected linked target missing or ambiguous' }
$pdb=Get-ChildItem $build -Recurse -File | Where-Object { $_.Name -eq ($target+'.pdb') }
if (@($pdb).Count -ne 1) { throw 'Matching PDB missing or ambiguous' }
New-Item -ItemType Directory -Force "$out/binary" | Out-Null
Copy-Item $binary.FullName,$pdb.FullName "$out/binary"
Copy-Item "$build/compile_commands.json" "$out/compile_commands.json"
& python scripts/preprocess_qualification_msvc.py "$build/compile_commands.json" "$out/preprocessed"
if ($LASTEXITCODE -ne 0) { throw 'Source preprocessing failed' }
$ownedRoot=if ($Project -in @('ninja','OpenCC')) { Join-Path $src 'src' } else { $src }
& ./scripts/qualify_msvc_pdb.ps1 -TargetName $Project -Mode $Mode -BinaryPath $binary.FullName -PdbPath $pdb.FullName -ProjectSourceRoots @($ownedRoot) -EvidenceRoot $out
if (-not (Test-Path "$out/qualification.json")) { throw 'Qualification evidence missing' }
