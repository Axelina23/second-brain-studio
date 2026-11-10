# Parti comuni degli hook di Second Brain Studio: legge la cartella del second brain e
# il percorso di claude da ~/.claude/second-brain/config.json (scritto dall'app).
# Nota: niente lettere accentate in questi file (PowerShell 5.1 legge male l'UTF-8).
$SB_CACHE = Join-Path $env:USERPROFILE ".claude\second-brain"
$SB_RADICE = $null
$SB_APPUNTI = $true; $SB_ASSISTENTE_APPUNTI = "chat"
$SB_MODELLO = "sonnet"; $SB_MODELLO_CODEX = "gpt-5.6-luna"; $SB_MODELLO_AGY = "gemini-3.8-flash-high"
$SB_SOGLIA = 30KB
$SB_CLAUDE = Join-Path $env:USERPROFILE ".local\bin\claude.exe"
# Explorer e l'avvio automatico possono avere ancora il PATH precedente all'installazione.
$percorsiCli = @([Environment]::GetEnvironmentVariable('Path', 'Machine'), [Environment]::GetEnvironmentVariable('Path', 'User'), $env:Path)
$percorsiCli += @("$env:USERPROFILE\.local\bin", "$env:USERPROFILE\.cargo\bin", "$env:LOCALAPPDATA\Programs\OpenAI\Codex\bin", "$env:APPDATA\npm", "$env:LOCALAPPDATA\Microsoft\WinGet\Links", "$env:LOCALAPPDATA\Programs\nodejs", "$env:ProgramFiles\nodejs")
$env:Path = ($percorsiCli | Where-Object { $_ } | ForEach-Object { [Environment]::ExpandEnvironmentVariables($_) }) -join ';'
try {
  $cfg = Get-Content -Raw -Encoding UTF8 (Join-Path $SB_CACHE "config.json") | ConvertFrom-Json
  if ($cfg.radice -and (Test-Path $cfg.radice)) { $SB_RADICE = $cfg.radice }
  if ($cfg.claude -and (Test-Path $cfg.claude)) { $SB_CLAUDE = $cfg.claude }
  # impostazioni dell'app (Impostazioni > Appunti automatici)
  $imp = $cfg.impostazioni
  if ($imp) {
    if ($imp.appunti_auto -eq $false) { $SB_APPUNTI = $false }
    if ($imp.assistente_appunti -in @("chat", "claude", "codex", "agy")) { $SB_ASSISTENTE_APPUNTI = $imp.assistente_appunti }
    if ($imp.modello_appunti -in @("sonnet", "haiku", "opus")) { $SB_MODELLO = $imp.modello_appunti }
    if ($imp.modello_appunti_codex -in @("predefinito", "gpt-5.6-luna", "gpt-6-luna", "gpt-5.6-terra", "gpt-6.1-terra", "gpt-5.6-sol", "gpt-6-sol", "gpt-6.1-sol", "gpt-6-astra")) { $SB_MODELLO_CODEX = $imp.modello_appunti_codex }
    if ($imp.modello_appunti_agy -in @("gemini-3.8-flash-high", "gemini-3.8-flash-low", "gemini-4-argon-low", "gemini-4-argon-medium", "gemini-4-argon-high")) { $SB_MODELLO_AGY = $imp.modello_appunti_agy }
    if ($imp.soglia_kb -gt 0) { $SB_SOGLIA = [int]$imp.soglia_kb * 1KB }
  }
} catch {}
if (-not (Test-Path $SB_CLAUDE)) {
  $c = Get-Command claude -ErrorAction SilentlyContinue
  if ($c) { $SB_CLAUDE = $c.Source }
}
