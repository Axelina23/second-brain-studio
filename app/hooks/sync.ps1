# Sincronizza il second brain con il suo repository (se ne ha uno).
#   -Modo pull : a inizio sessione, scarica le modifiche degli altri PC
#   -Modo push : a fine sessione, salva e carica tutto
# Non blocca mai Claude Code: in caso di errore scrive nel log ed esce.
# -Json: stampa un oggetto JSON vuoto (lo vogliono gli hook di Codex e Antigravity).
param([ValidateSet("pull", "push")][string]$Modo = "pull", [switch]$Json)
. (Join-Path $PSScriptRoot "comune.ps1")
if ($Json) { Write-Output "{}" }
if ($Modo -eq "pull" -and $env:CLAUDE_NOTES_PASS) { exit 0 }
if (-not $SB_RADICE -or -not (Test-Path (Join-Path $SB_RADICE ".git"))) { exit 0 }
Set-Location $SB_RADICE
$log = Join-Path $SB_CACHE "sync-ultimo.log"
$remoto = (& git.exe remote 2>$null | Out-String).Trim()

function Git { & git.exe @args 2>&1 | Out-String }

# Un rebase o un merge rimasto a meta' (conflitto) va annullato subito: se resta, i commit
# successivi si portano dietro i segni del conflitto e il push non parte piu'. Il conflitto
# lo ritrova la sincronizzazione dell'app, che lo mostra e lo fa sistemare all'assistente.
function Annulla-AMeta {
  $g = Join-Path $SB_RADICE ".git"
  $r = ""
  if ((Test-Path "$g\rebase-merge") -or (Test-Path "$g\rebase-apply")) { $r += "CONFLITTO: rebase annullato`n"; $r += Git rebase --abort }
  if (Test-Path "$g\MERGE_HEAD") { $r += "CONFLITTO: merge annullato`n"; $r += Git merge --abort }
  return $r
}

$out = "$(Get-Date -Format s) $Modo`n"
$out += Annulla-AMeta
if ($Modo -eq "pull") {
  if ($remoto) { $out += Git pull --rebase --autostash --quiet; $out += Annulla-AMeta }
} else {
  $out += Git add -A
  if ((Git status --porcelain).Trim()) {
    $out += Git commit --quiet -m "auto: $env:COMPUTERNAME $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
  }
  if ($remoto) {
    $out += Git pull --rebase --autostash --quiet
    $a = Annulla-AMeta
    $out += $a
    if (-not $a) { $out += Git push --quiet }
  }
}
$out | Out-File $log -Encoding utf8
exit 0
