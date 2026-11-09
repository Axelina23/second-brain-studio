# Worker di fine sessione: estrae dalla trascrizione solo i messaggi e il testo delle
# risposte (niente output dei tool), poi un Claude headless (Sonnet) aggiorna gli appunti.
# Log in ~/.claude/second-brain: appunti-ultimo.log e appunti-errori.log.
# Per le chat di Codex e Antigravity lo lancia l'app con -Testo (il riassunto gia' estratto,
# in un file della cartella temporanea), -Id, -Strumento e -Data al posto di -Transcript.
param([string]$Transcript, [string]$Progetto, [string]$Testo = "", [string]$Id = "",
      [string]$Strumento = "Claude Code", [string]$Data = "", [string]$Assistente = "")
. (Join-Path $PSScriptRoot "comune.ps1")
$env:CLAUDE_NOTES_PASS = "1"
$log = Join-Path $SB_CACHE "appunti-ultimo.log"
$err = Join-Path $SB_CACHE "appunti-errori.log"
if (-not $Id) { $Id = [IO.Path]::GetFileNameWithoutExtension($Transcript) }
$oggi = if ($Data) { $Data } elseif ($Transcript) { (Get-Item $Transcript).LastWriteTime.ToString("yyyy-MM-dd") } else { Get-Date -Format "yyyy-MM-dd" }

function Segna-Salvata {
  try {
    $segni = Join-Path $SB_CACHE "segni"
    New-Item -ItemType Directory -Force -Path $segni | Out-Null
    Set-Content -Path (Join-Path $segni "$Id.salvata") -Value (Get-Date -Format o)
  } catch {}
}

try {
  $righe = New-Object System.Collections.Generic.List[string]
  if ($Testo) {
    $righe.Add([System.IO.File]::ReadAllText($Testo, [System.Text.Encoding]::UTF8))
    Remove-Item $Testo -ErrorAction SilentlyContinue
  } else {
  $reader = New-Object System.IO.StreamReader($Transcript, [System.Text.Encoding]::UTF8)
  while ($null -ne ($line = $reader.ReadLine())) {
    if ($line -notmatch '"type":"(user|assistant)"') { continue }
    try { $o = $line | ConvertFrom-Json } catch { continue }
    $c = $o.message.content
    if ($o.type -eq "user" -and $c -is [string]) {
      if ($c -match '^<(local-command|command-name|system-reminder)') { continue }
      $righe.Add("UTENTE: " + $c.Substring(0, [Math]::Min($c.Length, 2000)))
    } elseif ($o.type -eq "assistant") {
      foreach ($p in @($c)) {
        if ($p.type -eq "text" -and $p.text) {
          $righe.Add("CLAUDE: " + $p.text.Substring(0, [Math]::Min($p.text.Length, 1500)))
        }
      }
    }
  }
  $reader.Close()
  }

  $testo = $righe -join "`n`n"
  if ($testo.Length -gt 150000) { $testo = "[...inizio tagliato...]`n" + $testo.Substring($testo.Length - 150000) }
  if ($testo.Length -lt 500) {
    "Sessione senza contenuto utile, saltata." | Out-File $log -Encoding utf8
    Segna-Salvata
    & (Join-Path $PSScriptRoot "sync.ps1") -Modo push
    exit 0
  }

  $riassunto = Join-Path $env:TEMP "appunti-sessione-$PID.txt"
  [System.IO.File]::WriteAllText($riassunto, $testo, (New-Object System.Text.UTF8Encoding($false)))

  # struttura inglese (INDEX.md, Me/Rules.md, Archive/Log.md): istruzioni e file in inglese
  $inglese = (Test-Path (Join-Path $SB_RADICE "INDEX.md")) -and -not (Test-Path (Join-Path $SB_RADICE "INDICE.md"))
  if ($inglese) {
    $prompt = "You are the automatic step that updates the notes of this second brain. " +
    "Read ${riassunto}: it is the summary (user messages and replies) of a $Strumento session on $oggi in the folder $Progetto. " +
    "Then read INDEX.md and Me/Rules.md in this folder. " +
    "1) If the session was meaningful, add a line at the top of the list in Archive/Log.md, in the format described in that file (tool: $Strumento). " +
    "2) If there are lasting facts (a project changing status, decisions, deadlines, preferences) that are missing or outdated in the files listed in the index, update them with minimal edits, replacing outdated information. " +
    "Every status file must stay under ~80 lines: if it goes over, move the old part to a history.md file in the same folder. " +
    "3) Change INDEX.md only if a project is new or finished. " +
    "Follow the rules in Me/Rules.md. Don't save temporary details. Never write passwords, API keys, tokens or access codes in the notes, not even partially. Don't make things up. If there is nothing relevant, don't touch anything. " +
    "At the end write in one line what you changed."
  } else {
  $prompt = "Sei il passaggio automatico che aggiorna gli appunti di questo second brain. " +
    "Leggi ${riassunto}: e' il riassunto (messaggi utente e risposte) di una sessione di $Strumento del $oggi nella cartella $Progetto. " +
    "Poi leggi INDICE.md e Io/Regole.md in questa cartella. " +
    "1) Se la sessione e' stata significativa, aggiungi in cima alla lista di Archivio/Registro.md una riga nel formato descritto nel file (strumento: $Strumento). " +
    "2) Se ci sono fatti durevoli (cambi di stato di un progetto, decisioni, scadenze, preferenze) che mancano o sono superati nei file indicati dall'indice, aggiornali con modifiche minime, sostituendo le informazioni superate. " +
    "Ogni file di stato deve restare sotto le ~80 righe: se lo superi, sposta la parte vecchia in un file storico.md nella stessa cartella. " +
    "3) Modifica INDICE.md solo se un progetto e' nuovo o concluso. " +
    "Rispetta le regole di Io/Regole.md. Non salvare dettagli temporanei. Mai scrivere negli appunti password, chiavi API, token o codici di accesso, nemmeno in parte. Non inventare. Se non c'e' niente di rilevante, non toccare nulla. " +
    "Alla fine scrivi in una riga cosa hai modificato."
  }

  Set-Location $SB_RADICE
  $origine = if ($Assistente -in @("claude", "codex", "agy")) { $Assistente } elseif ($Strumento -eq "Codex") { "codex" } elseif ($Strumento -eq "Antigravity") { "agy" } else { "claude" }
  $chi = if ($SB_ASSISTENTE_APPUNTI -in @("claude", "codex", "agy")) { $SB_ASSISTENTE_APPUNTI } else { $origine }
  if ($chi -eq "agy" -and (Get-Command agy -ErrorAction SilentlyContinue)) {
    $prompt | & agy -p --model $SB_MODELLO_AGY --mode auto --add-dir $env:TEMP 2> $err | Out-File $log -Encoding utf8
  } elseif ($chi -eq "codex" -and (Get-Command codex -ErrorAction SilentlyContinue)) {
    $modArg = if ($SB_MODELLO_CODEX -and $SB_MODELLO_CODEX -ne "predefinito") { @("-m", $SB_MODELLO_CODEX) } else { @() }
    $prompt | & codex exec --ephemeral -s workspace-write --add-dir $env:TEMP @modArg - 2> $err | Out-File $log -Encoding utf8
  } else {
    $prompt | & $SB_CLAUDE -p --model $SB_MODELLO --add-dir $env:TEMP --allowedTools "Read" "Edit" "Write" "Glob" "Grep" 2> $err | Out-File $log -Encoding utf8
  }
  if ($LASTEXITCODE -eq 0) { Segna-Salvata }
  Remove-Item $riassunto -ErrorAction SilentlyContinue
} catch {
  $_ | Out-String | Out-File $err -Encoding utf8
}
& (Join-Path $PSScriptRoot "sync.ps1") -Modo push
