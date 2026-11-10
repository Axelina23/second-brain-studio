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
    Remove-Item (Join-Path $SB_CACHE "segni\$Id.in-corso") -ErrorAction SilentlyContinue
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
    "Follow the rules in Me/Rules.md. You may use local shell commands to read files and apply_patch to edit them. Do not use git, network access or other programs; only update the requested notes. Don't save temporary details. Never write passwords, API keys, tokens or access codes in the notes, not even partially. Don't make things up. If there is nothing relevant, don't touch anything. " +
    "At the end write in one line what you changed."
  } else {
  $prompt = "Sei il passaggio automatico che aggiorna gli appunti di questo second brain. " +
    "Leggi ${riassunto}: e' il riassunto (messaggi utente e risposte) di una sessione di $Strumento del $oggi nella cartella $Progetto. " +
    "Poi leggi INDICE.md e Io/Regole.md in questa cartella. " +
    "1) Se la sessione e' stata significativa, aggiungi in cima alla lista di Archivio/Registro.md una riga nel formato descritto nel file (strumento: $Strumento). " +
    "2) Se ci sono fatti durevoli (cambi di stato di un progetto, decisioni, scadenze, preferenze) che mancano o sono superati nei file indicati dall'indice, aggiornali con modifiche minime, sostituendo le informazioni superate. " +
    "Ogni file di stato deve restare sotto le ~80 righe: se lo superi, sposta la parte vecchia in un file storico.md nella stessa cartella. " +
    "3) Modifica INDICE.md solo se un progetto e' nuovo o concluso. " +
    "Rispetta le regole di Io/Regole.md. Puoi usare comandi locali per leggere i file e apply_patch per modificarli. Non usare git, rete o altri programmi; limita le modifiche agli appunti richiesti. Non salvare dettagli temporanei. Mai scrivere negli appunti password, chiavi API, token o codici di accesso, nemmeno in parte. Non inventare. Se non c'e' niente di rilevante, non toccare nulla. " +
    "Alla fine scrivi in una riga cosa hai modificato."
  }

  Set-Location $SB_RADICE
  $origine = if ($Assistente -in @("claude", "codex", "agy")) { $Assistente } elseif ($Strumento -eq "Codex") { "codex" } elseif ($Strumento -eq "Antigravity") { "agy" } else { "claude" }
  $chi = if ($SB_ASSISTENTE_APPUNTI -in @("claude", "codex", "agy")) { $SB_ASSISTENTE_APPUNTI } else { $origine }
  $modUsato = if ($chi -eq "agy") { $SB_MODELLO_AGY } elseif ($chi -eq "codex") { $SB_MODELLO_CODEX } else { $SB_MODELLO }
  $logTmp = Join-Path $env:TEMP "appunti-log-$PID.txt"
  $errTmp = Join-Path $env:TEMP "appunti-err-$PID.txt"
  "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Appunti: $chi ($modUsato) - chat $Id" | Out-File $logTmp -Encoding utf8
  if ($chi -eq "agy" -and (Get-Command agy -ErrorAction SilentlyContinue)) {
    & agy --model $SB_MODELLO_AGY --add-dir $env:TEMP -p $prompt 2> $errTmp | Out-File $logTmp -Append -Encoding utf8
  } elseif ($chi -eq "codex" -and (Get-Command codex -ErrorAction SilentlyContinue)) {
    $prompt += " Al termine, solo se hai letto i file e completato l'aggiornamento (o verificato che non serve), scrivi su una riga separata SB_NOTES_OK. Se non riesci, non scrivere questo segnale."
    $modArg = if ($SB_MODELLO_CODEX -and $SB_MODELLO_CODEX -ne "predefinito") { @("-m", $SB_MODELLO_CODEX) } else { @() }
    $prompt | & codex exec --ephemeral -s workspace-write --add-dir $env:TEMP @modArg - 2> $errTmp | Out-File $logTmp -Append -Encoding utf8
  } else {
    $prompt | & $SB_CLAUDE -p --model $SB_MODELLO --add-dir $env:TEMP --allowedTools "Read" "Edit" "Write" "Glob" "Grep" 2> $errTmp | Out-File $logTmp -Append -Encoding utf8
  }
  $codice = $LASTEXITCODE
  if ($codice -ne 0) { throw "Assistente terminato con codice $codice; dettagli in $errTmp" }
  if ($chi -eq "codex") {
    $risposta = [IO.File]::ReadAllText($logTmp)
    if ($risposta -notmatch '(?m)^SB_NOTES_OK\s*$') { throw "Codex non ha confermato il completamento; dettagli in $logTmp e $errTmp" }
  }
  Segna-Salvata
  $archivioLog = Join-Path $SB_CACHE "salvataggi"
  New-Item -ItemType Directory -Force -Path $archivioLog | Out-Null
  Copy-Item -LiteralPath $logTmp -Destination (Join-Path $archivioLog "$Id.log") -Force
  if (Test-Path $errTmp) { Copy-Item -LiteralPath $errTmp -Destination (Join-Path $archivioLog "$Id.errori.log") -Force }
  try { Move-Item -Force $logTmp $log -ErrorAction SilentlyContinue } catch {}
  try { Move-Item -Force $errTmp $err -ErrorAction SilentlyContinue } catch {}
  Remove-Item $riassunto, $logTmp, $errTmp -ErrorAction SilentlyContinue
} catch {
  try {
    New-Item -ItemType Directory -Force -Path (Join-Path $SB_CACHE "segni") | Out-Null
    Set-Content -Path (Join-Path $SB_CACHE "segni\$Id.errore") -Value (Get-Date -Format o)
  } catch {}
  try { $_ | Out-String | Out-File $err -Encoding utf8 } catch {}
}
Remove-Item (Join-Path $SB_CACHE "segni\$Id.in-corso") -ErrorAction SilentlyContinue
& (Join-Path $PSScriptRoot "sync.ps1") -Modo push
