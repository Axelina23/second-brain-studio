# Produce il menu Windows 11. La firma usa una chiave gia' nel certificato utente;
# non importa certificati attendibili e non modifica le impostazioni di Windows.
param(
  [Parameter(Mandatory=$true)][string]$Zig,
  [Parameter(Mandatory=$true)][string]$SdkBin,
  [Parameter(Mandatory=$true)][string]$CertificateThumbprint,
  [string]$Versione = "1.0.0.0"
)
$ErrorActionPreference = "Stop"
$qui = $PSScriptRoot
$dest = Join-Path $qui "dist"
$stage = Join-Path $dest "package"
New-Item -ItemType Directory -Force -Path $stage | Out-Null
$cert = Get-Item -LiteralPath "Cert:\CurrentUser\My\$CertificateThumbprint"
if (-not $cert.HasPrivateKey) { throw "Il certificato non contiene la chiave di firma" }
& $Zig c++ (Join-Path $qui "SBSInbox.cpp") -target x86_64-windows-gnu -std=c++17 -O2 -shared -lole32 -lshlwapi -luuid -luser32 -o (Join-Path $dest "SBSInbox.dll")
if ($LASTEXITCODE -ne 0) { throw "Compilazione del menu non riuscita" }
[xml]$manifest = Get-Content -Raw -Encoding UTF8 (Join-Path $qui "AppxManifest.xml")
$manifest.Package.Identity.Publisher = $cert.Subject
$manifest.Package.Identity.Version = $Versione
$manifest.Save((Join-Path $stage "AppxManifest.xml"))
$makeappx = Join-Path $SdkBin "makeappx.exe"
$signtool = Join-Path $SdkBin "signtool.exe"
& $makeappx pack /o /nv /d $stage /p (Join-Path $dest "InboxMenu.msix")
if ($LASTEXITCODE -ne 0) { throw "Creazione pacchetto del menu non riuscita" }
& $signtool sign /fd SHA256 /sha1 $cert.Thumbprint (Join-Path $dest "InboxMenu.msix")
if ($LASTEXITCODE -ne 0) { throw "Firma pacchetto del menu non riuscita" }
Export-Certificate -Cert $cert -FilePath (Join-Path $dest "publisher.cer") -Force | Out-Null
# Solo certificato pubblico nel pacchetto; nessuna chiave privata esportata.
Write-Host "Menu compilato e firmato in $dest"
