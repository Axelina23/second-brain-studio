; Installer classico di Windows per Second Brain (Inno Setup 6).
; Installazione per utente (niente permessi di amministratore), cartella a scelta,
; collegamenti su Desktop e menu Start, avvio con Windows facoltativo, disinstallazione
; da Impostazioni > App. Lo compila build.ps1 passando /DVersione=... e /DSorgente=...
; Gli aggiornamenti usano lo stesso installer in modalita' /SILENT: si vede la barra di
; avanzamento e alla fine l'app si riapre da sola.

#ifndef Versione
  #define Versione "0.0.0"
#endif
#ifndef Sorgente
  #define Sorgente "dist\Second Brain Studio"
#endif

[Setup]
AppId={{6B7D1E2A-4C3F-4E8B-9A51-2F0C7D9E8B14}
AppName=Second Brain Studio
AppVersion={#Versione}
AppVerName=Second Brain Studio {#Versione}
AppPublisher=Francesco Cinquegrana
DefaultDirName={autopf}\Second Brain Studio
DefaultGroupName=Second Brain Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputBaseFilename=Second Brain Studio Setup {#Versione}
SetupIconFile=icona.ico
UninstallDisplayIcon={app}\Second Brain Studio.exe
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=force
UsePreviousAppDir=no
RestartApplications=no
; Non trasmettere all'app il blocco delle junction utente usate da Codex.
RedirectionGuard=no
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"

[Tasks]
Name: "desktop"; Description: "Crea un collegamento sul desktop"; GroupDescription: "Collegamenti:"
Name: "avvio"; Description: "Avvia Second Brain con Windows (nascosto vicino all'orologio)"; GroupDescription: "Avvio:"

[Files]
Source: "{#Sorgente}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; via i file di versioni vecchie che non esistono piu'
Type: filesandordirs; Name: "{app}\_internal"
; installazioni precedenti con il vecchio nome "Second Brain"
Type: filesandordirs; Name: "{localappdata}\Programs\Second Brain"
Type: files; Name: "{autodesktop}\Second Brain.lnk"
Type: files; Name: "{autoprograms}\Second Brain.lnk"
Type: files; Name: "{userstartup}\Second Brain.lnk"
#ifdef MenuWindows11
Type: files; Name: "{usersendto}\SBS Inbox.lnk"; Check: UsaMenuModerno
#endif

[Icons]
Name: "{autoprograms}\Second Brain Studio"; Filename: "{app}\Second Brain Studio.exe"; AppUserModelID: "SecondBrainStudio.App"
Name: "{autodesktop}\Second Brain Studio"; Filename: "{app}\Second Brain Studio.exe"; Tasks: desktop
Name: "{userstartup}\Second Brain Studio"; Filename: "{app}\Second Brain Studio.exe"; Parameters: "--nascosta"; Tasks: avvio

; Explorer aggiunge alla riga di comando tutti i file selezionati.
Name: "{usersendto}\SBS Inbox"; Filename: "{app}\Second Brain Studio.exe"; Parameters: "--inbox"; WorkingDir: "{app}"; Comment: "Copia i file nell'Inbox di Second Brain Studio"; Check: UsaInviaA

[Run]
; dopo un aggiornamento Windows tiene in cache le icone vecchie dei collegamenti: le rinfresca
Filename: "{sys}\ie4uinit.exe"; Parameters: "-show"; Flags: runhidden nowait
Filename: "{app}\Second Brain Studio.exe"; Description: "Apri Second Brain Studio"; Flags: nowait postinstall; Check: DaAprire

[Registry]
; collegamento secondbrainstudio:// (clic sulle notifiche): lo riscrive anche l'app a ogni avvio
Root: HKCU; Subkey: "Software\Classes\secondbrainstudio"; ValueType: string; ValueName: ""; ValueData: "URL:Second Brain Studio"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\secondbrainstudio"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""
Root: HKCU; Subkey: "Software\Classes\secondbrainstudio\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Second Brain Studio.exe"" --link ""%1"""

#ifdef MenuWindows11
[UninstallRun]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\_shell\gestisci-menu.ps1"" -Azione rimuovi"; Flags: runhidden waituntilterminated; RunOnceId: "SBSInboxMenu"; Check: UsaMenuModerno
#endif

[Code]
function UsaMenuModerno(): Boolean;
var
  VersioneWindows: TWindowsVersion;
begin
  GetWindowsVersionEx(VersioneWindows);
  Result := VersioneWindows.Build >= 22000;
end;

function UsaInviaA(): Boolean;
begin
#ifdef MenuWindows11
  Result := not UsaMenuModerno();
#else
  Result := True;
#endif
end;

#ifdef MenuWindows11
procedure CurStepChanged(CurStep: TSetupStep);
var
  Codice: Integer;
  Parametri: String;
begin
  if (CurStep = ssPostInstall) and UsaMenuModerno() then begin
    Parametri := '-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\_shell\gestisci-menu.ps1') + '" -Azione installa -CartellaApp "' + ExpandConstant('{app}') + '"';
    if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Parametri, '', SW_HIDE, ewWaitUntilTerminated, Codice) or (Codice <> 0) then begin
      Log('Menu Inbox non registrato: controllare menu-inbox.log e la firma del pacchetto');
      if not WizardSilent() then
        MsgBox('Il menu Inbox di Windows 11 non e'' stato attivato. Controlla che la firma del pacchetto sia attendibile. Dettagli: menu-inbox.log nella cartella dei registri di SBS.', mbInformation, MB_OK);
    end;
  end;
end;
#endif

// /NOAVVIO: aggiornamento lanciato da "Esci" nell'app, che non va riaperta
function DaAprire(): Boolean;
begin
  Result := Pos('/NOAVVIO', UpperCase(GetCmdTail)) = 0;
end;

