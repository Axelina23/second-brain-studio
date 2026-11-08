# Hook SessionEnd: lancia in background il worker che riassume la chat e aggiorna gli
# appunti. Deve uscire subito: il lavoro pesante sta nel worker.
if ($env:CLAUDE_NOTES_PASS) { exit 0 }  # la sessione headless del worker non riparte
. (Join-Path $PSScriptRoot "comune.ps1")
if (-not $SB_RADICE) { exit 0 }

$data = [Console]::In.ReadToEnd() | ConvertFrom-Json
$transcript = $data.transcript_path
if (-not $transcript -or -not (Test-Path $transcript)) { exit 0 }

# appunti automatici spenti o chat troppo corta: niente appunti, ma le modifiche ai file vanno comunque salvate
if (-not $SB_APPUNTI -or (Get-Item $transcript).Length -lt $SB_SOGLIA) {
  Start-Process -FilePath "powershell" -WindowStyle Hidden -ArgumentList @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$(Join-Path $PSScriptRoot 'sync.ps1')`"", "-Modo", "push")
  exit 0
}

# segno "in corso" per l'app: il worker e' partito
try {
  $segni = Join-Path $SB_CACHE "segni"
  New-Item -ItemType Directory -Force -Path $segni | Out-Null
  $id = if ($data.session_id) { $data.session_id } else { [IO.Path]::GetFileNameWithoutExtension($transcript) }
  Set-Content -Path (Join-Path $segni "$id.in-corso") -Value (Get-Date -Format o)
} catch {}

Start-Process -FilePath "powershell" -WindowStyle Hidden -ArgumentList @(
  "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$(Join-Path $PSScriptRoot 'fine-sessione-worker.ps1')`"",
  "-Transcript", "`"$transcript`"", "-Progetto", "`"$($data.cwd)`"")
exit 0
