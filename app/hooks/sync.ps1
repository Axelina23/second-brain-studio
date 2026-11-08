# Sincronizza il second brain con il suo repository (se ne ha uno).
#   -Modo pull : a inizio sessione, scarica le modifiche degli altri PC
#   -Modo push : a fine sessione, salva e carica tutto
# Non blocca mai Claude Code: in caso di errore scrive nel log ed esce.
param([ValidateSet("pull", "push")][string]$Modo = "pull")
. (Join-Path $PSScriptRoot "comune.ps1")
if (-not $SB_RADICE -or -not (Test-Path (Join-Path $SB_RADICE ".git"))) { exit 0 }
Set-Location $SB_RADICE
$log = Join-Path $SB_CACHE "sync-ultimo.log"
$remoto = (& git.exe remote 2>$null | Out-String).Trim()

function Git { & git.exe @args 2>&1 | Out-String }

$out = "$(Get-Date -Format s) $Modo`n"
if ($Modo -eq "pull") {
  if ($remoto) { $out += Git pull --rebase --autostash --quiet }
} else {
  $out += Git add -A
  if ((Git status --porcelain).Trim()) {
    $out += Git commit --quiet -m "auto: $env:COMPUTERNAME $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
  }
  if ($remoto) {
    $out += Git pull --rebase --autostash --quiet
    $out += Git push --quiet
  }
}
$out | Out-File $log -Encoding utf8
exit 0
