# Parti comuni degli hook di Second Brain Studio: legge la cartella del second brain e
# il percorso di claude da ~/.claude/second-brain/config.json (scritto dall'app).
# Nota: niente lettere accentate in questi file (PowerShell 5.1 legge male l'UTF-8).
$SB_CACHE = Join-Path $env:USERPROFILE ".claude\second-brain"
$SB_RADICE = $null
$SB_APPUNTI = $true; $SB_MODELLO = "sonnet"; $SB_SOGLIA = 30KB
$SB_CLAUDE = Join-Path $env:USERPROFILE ".local\bin\claude.exe"
try {
  $cfg = Get-Content -Raw -Encoding UTF8 (Join-Path $SB_CACHE "config.json") | ConvertFrom-Json
  if ($cfg.radice -and (Test-Path $cfg.radice)) { $SB_RADICE = $cfg.radice }
  if ($cfg.claude -and (Test-Path $cfg.claude)) { $SB_CLAUDE = $cfg.claude }
  # impostazioni dell'app (Impostazioni > Appunti automatici)
  $imp = $cfg.impostazioni
  if ($imp) {
    if ($imp.appunti_auto -eq $false) { $SB_APPUNTI = $false }
    if ($imp.modello_appunti -in @("sonnet", "haiku", "opus")) { $SB_MODELLO = $imp.modello_appunti }
    if ($imp.soglia_kb -gt 0) { $SB_SOGLIA = [int]$imp.soglia_kb * 1KB }
  }
} catch {}
if (-not (Test-Path $SB_CLAUDE)) {
  $c = Get-Command claude -ErrorAction SilentlyContinue
  if ($c) { $SB_CLAUDE = $c.Source }
}
