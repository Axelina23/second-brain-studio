# Apre una nuova chat di Claude in una scheda di Second Brain Studio (l'app deve essere
# aperta). Pensato per Claude stesso: per passare un lavoro a una chat nuova.
#   powershell -File apri-chat.ps1 -Prompt "testo" [-Cartella C:\percorso] [-Titolo "nome"]
#   powershell -File apri-chat.ps1 -PromptFile C:\tmp\compito.md [-Cartella ...]
# Il testo lungo conviene passarlo con -PromptFile (niente problemi di virgolette).
param([string]$Prompt = "", [string]$PromptFile = "", [string]$Cartella = "", [string]$Titolo = "")
if ($PromptFile) { $Prompt = [IO.File]::ReadAllText($PromptFile, [Text.Encoding]::UTF8) }
if (-not $Prompt.Trim()) { Write-Output "Serve -Prompt o -PromptFile"; exit 1 }
$dati = [ordered]@{ prompt = $Prompt; cartella = $Cartella; titolo = $Titolo } | ConvertTo-Json -Compress
$byte = [Text.Encoding]::UTF8.GetBytes("chat " + $dati + "`n")
try {
  $c = New-Object Net.Sockets.TcpClient("127.0.0.1", 47823)
  $s = $c.GetStream(); $s.Write($byte, 0, $byte.Length); $s.Flush(); $c.Close()
  Write-Output "Chat aperta in Second Brain Studio"
} catch {
  Write-Output "Second Brain Studio non e' aperto"; exit 1
}
