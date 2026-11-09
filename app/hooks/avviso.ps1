# Hook Stop e Notification di Claude Code: lascia un file evento che Second Brain Studio
# legge per la notifica "Claude ha finito" / "Claude aspetta un permesso".
# Deve essere velocissimo: copia il JSON ricevuto e aggiunge il tipo di evento.
# Lo usano anche Codex (Stop, PermissionRequest: stessi campi di Claude) e Antigravity
# (Stop: campi con altri nomi). A loro si risponde con un oggetto JSON vuoto, che vuol
# dire "nessuna decisione".
param([string]$Evento = "fine", [string]$Assistente = "claude")
$rispostaAgy = if ($Evento -eq "attesa") { '{"decision":"allow"}' } else { "{}" }
if ($env:CLAUDE_NOTES_PASS) {
  if ($Assistente -eq "agy") { Write-Output $rispostaAgy }
  elseif ($Assistente -ne "claude" -and $Evento -eq "fine") { Write-Output "{}" }
  exit 0
}
try {
  $dati = [Console]::In.ReadToEnd() | ConvertFrom-Json
  $cartella = Join-Path $env:USERPROFILE ".claude\second-brain\eventi"
  New-Item -ItemType Directory -Force -Path $cartella | Out-Null
  # attenzione: in PowerShell $evento e $Evento sono la stessa variabile, per questo si chiama $voce
  $voce = [ordered]@{
    evento = $Evento; sessione = $dati.session_id; cwd = $dati.cwd
    trascrizione = $dati.transcript_path; messaggio = $dati.message
    quando = [DateTimeOffset]::Now.ToUnixTimeSeconds(); assistente = $Assistente
  }
  if ($Assistente -eq "codex") {
    $voce.anteprima = $dati.last_assistant_message
    if ($Evento -eq "attesa" -and $dati.tool_name) { $voce.messaggio = "$($dati.tool_name)" }
  } elseif ($Assistente -eq "agy") {
    $voce.sessione = $dati.conversationId; $voce.cwd = @($dati.workspacePaths)[0]
    $voce.trascrizione = $dati.transcriptPath
    if ($Evento -eq "attesa") {
      # solo ask_question: "allow" la lascia partire (e' una domanda all'utente, non salta
      # nessun permesso). run_command non passa da qui: "allow" scavalcherebbe i permessi
      $nomeTool = $dati.toolCall.name; $argTool = $dati.toolCall.args
      if ($nomeTool -eq "ask_question") {
        $domanda = @($argTool.questions)[0].question
        $voce.messaggio = if ($domanda) { "$domanda" } else { "Domanda" }
      } else {
        Write-Output $rispostaAgy; exit 0
      }
    } else {
      # interrotto dall'utente: non e' una risposta finita, niente notifica
      if ($dati.terminationReason -eq "USER_CANCELED") { Write-Output "{}"; exit 0 }
    }
  }
  $nome = "{0}-{1}.json" -f [DateTime]::Now.Ticks, $PID
  $tmp = Join-Path $cartella "$nome.tmp"
  [IO.File]::WriteAllText($tmp, ($voce | ConvertTo-Json -Compress), (New-Object Text.UTF8Encoding($false)))
  Move-Item -Force $tmp (Join-Path $cartella $nome)
} catch {}
if ($Assistente -eq "agy") { Write-Output $rispostaAgy }
elseif ($Assistente -ne "claude" -and $Evento -eq "fine") { Write-Output "{}" }
exit 0
