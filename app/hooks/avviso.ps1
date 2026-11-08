# Hook Stop e Notification di Claude Code: lascia un file evento che Second Brain Studio
# legge per la notifica "Claude ha finito" / "Claude aspetta un permesso".
# Deve essere velocissimo: copia il JSON ricevuto e aggiunge il tipo di evento.
param([string]$Evento = "fine")
if ($env:CLAUDE_NOTES_PASS) { exit 0 }  # le sessioni automatiche degli appunti non avvisano
try {
  $dati = [Console]::In.ReadToEnd() | ConvertFrom-Json
  $cartella = Join-Path $env:USERPROFILE ".claude\second-brain\eventi"
  New-Item -ItemType Directory -Force -Path $cartella | Out-Null
  $evento = [ordered]@{
    evento = $Evento; sessione = $dati.session_id; cwd = $dati.cwd
    trascrizione = $dati.transcript_path; messaggio = $dati.message
    quando = [DateTimeOffset]::Now.ToUnixTimeSeconds()
  }
  $nome = "{0}-{1}.json" -f [DateTime]::Now.Ticks, $PID
  $tmp = Join-Path $cartella "$nome.tmp"
  [IO.File]::WriteAllText($tmp, ($evento | ConvertTo-Json -Compress), (New-Object Text.UTF8Encoding($false)))
  Move-Item -Force $tmp (Join-Path $cartella $nome)
} catch {}
exit 0
