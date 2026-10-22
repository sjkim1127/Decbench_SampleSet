param(
  [Parameter(Mandatory=$true)][ValidateSet('detours','winsparkle')][string]$Project,
  [Parameter(Mandatory=$true)][ValidateSet('O0','O2','O2-noinline')][string]$Mode
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$plan=Get-Content -Raw targets/qualification-v2/pilot.json | ConvertFrom-Json
$cells=@($plan.cells | Where-Object { $_.platform -eq 'windows' -and $_.project -eq $Project })
if ($cells.Count -ne 1) { throw 'Missing or ambiguous pinned source cell' }
$cell=$cells[0]
$src=Join-Path $PWD "_qualification/recollection-src/$Project"
$out=Join-Path $PWD "_qualification/recollection/$Project/$Mode"
New-Item -ItemType Directory -Force $src,$out | Out-Null
& git init -q $src
& git -C $src remote add origin "https://github.com/$($cell.source_repository).git"
& git -C $src fetch -q --depth 1 origin $cell.source_revision
if ($LASTEXITCODE -ne 0) { throw 'Pinned source fetch failed' }
& git -C $src checkout -q FETCH_HEAD
if ($LASTEXITCODE -ne 0 -or (& git -C $src rev-parse HEAD).Trim() -ne $cell.source_revision) { throw 'Pinned source mismatch' }
& git -C $src submodule update --init --recursive --depth 1
if ($LASTEXITCODE -ne 0) { throw 'Pinned submodule fetch failed' }
& git -C $src archive --format=tar.gz --output "$out/original.tar.gz" HEAD
if ($LASTEXITCODE -ne 0) { throw 'Original source archive failed' }
& git -C $src submodule status --recursive | Set-Content "$out/submodule-revisions.txt"
@{
  source_revision=$cell.source_revision
  source_repository=$cell.source_repository
  project=$Project
  optimization=$Mode
  workflow_commit=$env:GITHUB_SHA
  runner=$env:ImageOS
  image_version=$env:ImageVersion
  artifact_role='new linked-image recollection candidate; never an old-binary oracle'
  qualified=$false
  scoring_ready=$false
} | ConvertTo-Json -Depth 8 | Set-Content "$out/build-provenance.json"
if ($Project -eq 'detours') {
  & ./scripts/validate_detours_msvc.ps1 -Mode $Mode -DetoursRoot $src -EvidenceRoot $out
} else {
  & ./scripts/validate_winsparkle_msvc.ps1 -Mode $Mode -SourceRoot $src -EvidenceRoot $out
}
if (-not (Test-Path "$out/qualification.json")) { throw 'Native PE/PDB build validation did not complete' }
$compiler=(Get-Command cl.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
& python scripts/collect_msvc_recollection.py --project $Project --source $src --evidence $out --compiler $compiler
if ($LASTEXITCODE -ne 0) { throw 'Native compiler/preprocessing evidence recollection failed' }
& tar -czf "$out/preprocessed.tar.gz" -C $out preprocessed
if ($LASTEXITCODE -ne 0) { throw 'Preprocessed source archive failed' }
Remove-Item -Recurse -Force "$out/preprocessed"
