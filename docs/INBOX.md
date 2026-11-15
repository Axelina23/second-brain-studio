# Aggiungere file all'Inbox

- **Screenshot:** dopo la cattura apri Inbox e premi **Ctrl+V**, oppure **Incolla screenshot**. Viene salvata solo l'immagine corrente degli appunti, in PNG, con data e ora. Gli appunti vengono letti solo su richiesta. Le immagini mostrano una miniatura.
- **Qualunque file su Windows:** seleziona uno o più file in Esplora file, poi **tasto destro → Invia a → SBS Inbox**. Su Windows 11 può essere necessario scegliere prima **Mostra altre opzioni**. Il collegamento viene aggiunto dall'installer e rimosso con la disinstallazione.
- **Menu principale Windows 11:** nelle build con l'estensione moderna puoi scegliere direttamente **Invia a Inbox**. Occorrono la DLL nativa e un pacchetto identità firmato e attendibile. Non viene cambiato il menu globale di Windows. Il menu classico resta per Windows 10 e per le build senza estensione.
- Puoi continuare a trascinare i file nella pagina Inbox.

I file vengono copiati: gli originali restano al loro posto. I nomi duplicati ricevono un suffisso numerico, senza sovrascritture. Le cartelle vengono saltate. Non viene avviata un'analisi IA durante l'importazione.

Il comando Invia a apre Studio se è chiuso; se è già aperto, anche nascosto, consegna i file alla stessa istanza e mostra Inbox. Serve un second brain già configurato; altrimenti viene mostrato un avviso e occorre ripetere l'invio dopo la configurazione.

Da riga di comando: `"Second Brain Studio.exe" --inbox "C:\documenti\file uno.pdf" "C:\documenti\file due.png"`.

## Compilare il menu Windows 11

1. Compila `app/shell/build.ps1` passando `-Zig` (Zig 0.14.1), `-SdkBin` (Windows SDK, cartella x64 con MakeAppx e SignTool), `-CertificateThumbprint` (certificato di firma in CurrentUser/My) e una `-Versione` crescente, per esempio `1.0.0.1`.
2. Verifica la DLL con `python app/shell/verifica.py --zig <percorso-zig.exe>`. La prova non registra il menu e non modifica gli archivi certificati.
3. Esegui `app/build.ps1 -MenuWindows11`. L'installer include la DLL, il pacchetto e la registrazione per utente; la disinstallazione rimuove la registrazione prima dei file.

I binari prodotti in `app/shell/dist/` sono ignorati da Git. La chiave privata non viene esportata; `publisher.cer` contiene solo il certificato pubblico. Nessuno script importa automaticamente certificati attendibili. Per una prova locale, la fiducia al certificato di sviluppo va concessa separatamente; per distribuire serve una firma attendibile sui PC destinatari. La pubblicazione di build con una firma locale non attendibile viene bloccata.

Il comando non compare sulle cartelle. Se la selezione supera il limite della riga di comando di Windows, viene chiesto di inviarla in gruppi più piccoli. Dopo la prima registrazione può servire riaprire Esplora file o una nuova sessione Windows: l'installer non termina forzatamente Esplora file. Errori di registrazione in `~/.claude/second-brain/menu-inbox.log`.
