# Aggiungere file all'Inbox

- **Screenshot:** dopo la cattura apri Inbox e premi **Ctrl+V**, oppure **Incolla screenshot**. Viene salvata solo l'immagine corrente degli appunti, in PNG, con data e ora. Gli appunti vengono letti solo su richiesta. Le immagini mostrano una miniatura.
- **Qualunque file su Windows:** seleziona uno o più file in Esplora file, poi **tasto destro → Invia a → SBS Inbox**. Su Windows 11 può essere necessario scegliere prima **Mostra altre opzioni**. Il collegamento viene aggiunto dall'installer e rimosso con la disinstallazione.
- Puoi continuare a trascinare i file nella pagina Inbox.

I file vengono copiati: gli originali restano al loro posto. I nomi duplicati ricevono un suffisso numerico, senza sovrascritture. Le cartelle vengono saltate. Non viene avviata un'analisi IA durante l'importazione.

Il comando Invia a apre Studio se è chiuso; se è già aperto, anche nascosto, consegna i file alla stessa istanza e mostra Inbox. Serve un second brain già configurato; altrimenti viene mostrato un avviso e occorre ripetere l'invio dopo la configurazione.

Da riga di comando: `"Second Brain Studio.exe" --inbox "C:\documenti\file uno.pdf" "C:\documenti\file due.png"`.
