# Second Brain: app desktop. Finestra pywebview (WebView2) con l'interfaccia in web/,
# terminali incorporati (terminale.py), icona nell'area di notifica con notifiche di
# Windows, istanza unica. Chiudere la finestra la nasconde; "Esci" dal menu chiude tutto.
# Avvio: python Sistema/app/main.py [--nascosta] [--debug]   (o Second Brain Studio.exe)
import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
from datetime import date
from pathlib import Path

QUI = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import canali  # noqa: E402

canali.sistema()  # prima di ogni subprocess: vedi canali.py

from github import GitHub  # noqa: E402
from ponte import CACHE, RADICE, Ponte  # noqa: E402
import aggiornamenti  # noqa: E402
from aggiornamenti import avvia_staccato, script_aggiornamento  # noqa: E402
import altri_pc  # noqa: E402
import avvisi  # noqa: E402
import configurazione  # noqa: E402
import struttura  # noqa: E402
import impostazioni as imp_mod  # noqa: E402
import notifiche_win  # noqa: E402
from percorsi import cartella_sessioni  # noqa: E402
from terminale import Terminali  # noqa: E402

PORTA_ISTANZA = 47823
TITOLO = "Second Brain Studio"
try:
    VERSIONE = (QUI / "versione.txt").read_text(encoding="ascii").strip()
except OSError:
    VERSIONE = "sviluppo"
PRIMA_NOTIFICA = 90
OGNI = 15 * 60


def gia_aperta(comando: bytes = b"mostra") -> bool:
    # se un'altra istanza ascolta, le passa il comando (mostra / nuova) e restituisce True
    try:
        with socket.create_connection(("127.0.0.1", PORTA_ISTANZA), timeout=1) as s:
            s.sendall(comando + b"\n")
        return True
    except OSError:
        return False


def svuota_cache_interfaccia(cartella: Path) -> None:
    # WebView2 tiene in cache i file dell'interfaccia: dopo un aggiornamento userebbe quelli
    # vecchi. Si cancella solo la cache dei file (non localStorage, cioe' le preferenze).
    import shutil
    for nome in ("Cache", "Code Cache"):
        shutil.rmtree(cartella / "EBWebView" / "Default" / nome, ignore_errors=True)


class _Salta(Exception):
    pass


class Api:
    # solo metodi: pywebview li espone a JS come window.pywebview.api.<nome>
    def __init__(self, app: "App"):
        self._app = app

    @property
    def _p(self):
        # dinamico: dopo il primo avvio il ponte viene ricreato sulla cartella scelta
        return self._app.ponte

    def home(self): return self._p.home()
    def chat(self): return self._p.chat()
    def appunti(self): return self._p.appunti()
    def leggi(self, rel): return self._p.leggi(rel)
    def scrivi(self, rel, testo, mtime): return self._p.scrivi(rel, testo, mtime)
    def cerca(self, q): return self._p.cerca(q)
    def inbox(self): return self._p.inbox()
    def conta_inbox(self): return self._p.conta_inbox()
    def nota(self, testo): return self._p.nota(testo)
    def apri_chat(self, tipo="nuova", sessione=None, prompt=None, cartella=None, titolo=None):
        imp = imp_mod.leggi()
        return self._p.apri_chat(tipo, sessione, prompt, cartella, titolo, imp["modello_chat"], imp["assistente_chat"])
    def assistenti(self): return self._p.assistenti()
    def salva_chat(self, sessione): return self._p.salva_chat(sessione)
    def elimina_chat(self, sessione): return self._p.elimina_chat(sessione)
    def ripristina_chat(self, sessione): return self._p.ripristina_chat(sessione)
    def cestino_chat(self): return self._p.cestino_chat()
    def elimina_per_sempre(self, sessione): return self._p.elimina_per_sempre(sessione)
    def svuota_cestino_chat(self): return self._p.svuota_cestino_chat()
    def rinomina_chat(self, sessione, titolo): return self._p.rinomina_chat(sessione, titolo)
    def rinomina_scheda(self, sid, titolo): return self._p.rinomina_scheda(sid, titolo)
    def fissa_chat(self, sessione, fissa=True): return self._p.fissa_chat(sessione, fissa)
    def apri_in_cartella(self, sessione, cartella): return self._p.apri_in_cartella(sessione, cartella)
    def esporta_chat(self, sessione): return self._p.esporta_chat(sessione)
    def riga_registro(self, sessione): return self._p.riga_registro(sessione)
    def cerca_chat(self, query): return self._p.cerca_chat(query)
    def duplica_chat(self, sessione):
        return self._p.apri_chat("duplica", sessione, modello=imp_mod.leggi()["modello_chat"])
    def elimina_inbox(self, rel): return self._p.elimina_inbox(rel)
    def ripristina_inbox(self, chiave): return self._p.ripristina_inbox(chiave)
    def rinomina_inbox(self, rel, nome): return self._p.rinomina_inbox(rel, nome)
    def sposta_inbox(self, rel, progetto): return self._p.sposta_inbox(rel, progetto)
    def schede(self): return self._p.schede()
    def chiudi_scheda(self, sid): return self._p.chiudi_scheda(sid)
    def apri_esterno(self, rel): return self._p.apri_esterno(rel)
    def apri_cartella(self): return self._p.apri_cartella()
    def stato_git(self): return self._p.stato_git()
    def mappa(self): return self._p.mappa()
    def uso(self): return self._p.uso()
    def attivita(self): return self._p.attivita()
    def esci(self, forza=False): return self._app.esci(forza)
    def aggiornamento(self):
        agg = self._app._aggiornamento()
        return {"pronto": agg is not None, "versione": VERSIONE, "nuova": agg.get("versione") if agg else None}
    def cerca_aggiornamenti(self): return self._app.cerca_aggiornamenti()
    def pc_remoti(self): return self._app.pc_remoti()
    def aggiorna(self): return self._app.aggiorna()
    def da_riaprire(self): return self._app.da_riaprire()
    def crea_progetto(self, nome, descrizione="", fondo=None, emblema=None, motivo=None): return self._p.crea_progetto(nome, descrizione, fondo, emblema, motivo)
    def cambia_aspetto(self, percorso, fondo=None, emblema=None, motivo=None): return self._p.cambia_aspetto(percorso, fondo, emblema, motivo)
    def pagina(self, nome): self._app.pagina = nome; return {"ok": True}
    def github_stato(self): return self._app.github.stato()
    def github_accedi(self): return self._app.github.avvia_accesso()
    def github_annulla(self): return self._app.github.annulla_accesso()
    def github_scollega(self): return self._app.github.scollega()
    def github_crea_repo(self, nome="second-brain"): return self._app.github.crea_repo(nome)
    def github_sincronizza(self):
        threading.Thread(target=self._app.sincronizza, name="sincronizza", daemon=True).start()
        return {"avviata": True}
    def apri_github(self, url):
        if isinstance(url, str) and url.startswith("https://github.com/"):
            os.startfile(url)  # type: ignore[attr-defined]
        return {"ok": True}
    def nascondi(self): return self._app.nascondi()
    def apri_link(self, url):
        if isinstance(url, str) and url.startswith("https://"):
            os.startfile(url)  # type: ignore[attr-defined]
        return {"ok": True}
    # primo avvio
    def configurazione(self): return configurazione.stato()
    def valuta_cartella(self, percorso): return configurazione.valuta_cartella(percorso)
    def scegli_cartella(self, iniziale=None): return self._app.scegli_cartella(iniziale)
    def accedi_claude(self): return configurazione.apri_accesso_claude()
    def github_repo_lista(self): return self._app.github.repo_lista()
    def completa_configurazione(self, scelte): return self._app.completa_configurazione(scelte)
    def annulla_primo_avvio(self):
        r = configurazione.annulla()
        if r.get("ok"):
            self._app.ricarica_radice(Path(r["radice"]))
        return r
    # impostazioni
    def impostazioni(self):
        return {"impostazioni": imp_mod.leggi(), "avvio": imp_mod.avvio_attivo(), "account": imp_mod.account_claude(),
                "avvisi": self._app.avvisi_collegati(), "radice": str(self._p.radice), "versione": VERSIONE,
                "cache": str(CACHE), "installata": getattr(sys, "frozen", False)}
    def salva_impostazioni(self, nuove):
        r = imp_mod.salva(nuove)
        if r.get("ok") and isinstance(nuove, dict) and "scorciatoia_globale" in nuove:
            self._app.aggiorna_scorciatoia()
        return r
    def imposta_avvio(self, attivo): return imp_mod.imposta_avvio(bool(attivo))
    def collega_avvisi(self): return self._app.collega_avvisi()
    def esporta(self):
        r = imp_mod.esporta(self._p.radice)
        if r.get("ok"):
            subprocess.Popen(["explorer", "/select,", r["file"]])
        return r
    def svuota_cache(self): return imp_mod.svuota_cache()
    def apri_registri(self): os.startfile(str(CACHE)); return {"ok": True}  # type: ignore[attr-defined]
    def rifai_primo_avvio(self): return self._app.rifai_primo_avvio()
    def accedi_claude_terminale(self): return self._p.apri_chat("nuova", None, "/login", None, "Accesso a Claude")
    def visibile(self, in_primo_piano, sessione=None):
        # l'interfaccia dice se la finestra e' in primo piano e quale chat si sta guardando
        self._app.in_primo_piano, self._app.sessione_vista = bool(in_primo_piano), sessione
        return {"ok": True}


class App:
    def __init__(self, nascosta: bool, debug: bool, nuova_chat: bool = False):
        self.nuova_chat = nuova_chat
        self.nascosta = nascosta
        self.debug = debug
        self.finestra = None
        self.icona = None
        self.uscendo = False
        self.terminali = Terminali(alla_chiusura=lambda s: self.ponte.scheda_chiusa(s))
        self.ponte = Ponte(radice=RADICE or CACHE / "nessun-second-brain", terminali=self.terminali)
        self.ponte.emetti = self.emetti
        self.github = GitHub(RADICE or CACHE, emetti=self.emetti, log=self.ponte._log, nota=self.ponte._nota)
        self.ponte.token_git = self.github._token
        self._blocco_aggiorna = threading.Lock()
        self.pagina = "oggi"
        self.in_primo_piano = True
        self.sessione_vista = None
        self.scorciatoia = imp_mod.Scorciatoia(self.mostra)
        self._ultima_sync = time.time()
        self.altri = altri_pc.AltriPC(self.github._token, self.github.repo, log=self.ponte._log)
        self._copia_strumenti()

    def _copia_strumenti(self) -> None:
        # apri-chat.ps1 e avviso.ps1 sempre aggiornati in ~/.claude/second-brain/hooks
        import shutil
        try:
            dest = CACHE / "hooks"
            dest.mkdir(parents=True, exist_ok=True)
            for f in (QUI / "hooks").glob("*.ps1"):
                shutil.copy2(f, dest / f.name)
        except OSError:
            self.ponte._log()

    # --- impostazioni ---
    def avvisi_collegati(self) -> bool:
        try:
            d = json.loads((Path.home() / ".claude" / "settings.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        return "avviso.ps1" in json.dumps((d.get("hooks") or {}).get("Stop") or [])

    def collega_avvisi(self) -> dict:
        import modello
        try:
            return modello.collega_hook(QUI / "hooks", CACHE / "hooks", solo_avvisi=True)
        except OSError as e:
            return {"errore": str(e)}

    def aggiorna_scorciatoia(self) -> None:
        if imp_mod.leggi()["scorciatoia_globale"]:
            self.scorciatoia.avvia()
        else:
            self.scorciatoia.ferma()

    def rifai_primo_avvio(self) -> dict:
        # il second brain attuale resta dov'e': si sceglie (o crea) un'altra cartella
        import percorsi
        cfg = percorsi.leggi_config()
        cfg["configurato"] = False
        cfg.pop("radice", None)
        cfg["radice_precedente"] = str(self.ponte.radice)
        percorsi.scrivi_config(cfg)
        return {"ok": True}

    # --- avvisi di Claude (hook Stop / Notification) ---
    def _avvisi(self) -> None:
        cartella = CACHE / "eventi"
        avvisi.leggi_eventi(cartella)  # via quelli rimasti da prima dell'avvio
        while not self.uscendo:
            try:
                for e in avvisi.leggi_eventi(cartella):
                    self._avviso(e)
            except Exception:
                self.ponte._log()
            time.sleep(1.5)

    def _avviso(self, e: dict) -> None:
        imp = imp_mod.leggi()
        sessione = e.get("sessione")
        scheda = next((s for s in self.terminali.schede.values() if s.sessione and s.sessione == sessione), None)
        attesa = e.get("evento") == "attesa"
        progetto = avvisi.nome_progetto(e.get("cwd"), self.ponte.radice)
        titolo = scheda.titolo if scheda else ""
        anteprima = (e.get("messaggio") or "") if attesa else avvisi.ultima_risposta(e.get("trascrizione"))
        dati = {"sessione": sessione, "scheda": scheda.id if scheda else None, "tipo": "attesa" if attesa else "fine",
                "progetto": progetto, "titolo": titolo, "anteprima": anteprima}
        self.emetti("claude-avviso", dati)
        if not imp["notifica_permesso" if attesa else "notifica_risposta"]:
            return
        if not scheda and not imp["notifica_fuori_app"]:
            return
        if self.in_primo_piano and scheda and self.sessione_vista == sessione:
            return  # la stai gia' guardando
        if imp_mod.in_silenzio(imp) or not self.icona:
            return
        testa = f"{progetto}" + (f" · {titolo}" if titolo and titolo.lower() != progetto.lower() else "")
        corpo = ("Claude aspetta un tuo permesso" if attesa else "Claude ha finito")
        if imp["anteprima"] and anteprima:
            corpo += f": {anteprima}"
        self._notifica(corpo[:250], testa[:60], sessione)

    def _notifica(self, testo: str, titolo: str, sessione: str | None = None) -> None:
        # app installata: notifica di Windows che si clicca (apre la chat); altrimenti quella semplice
        if getattr(sys, "frozen", False) and notifiche_win.mostra(titolo, testo, notifiche_win.link_chat(sessione)):
            return
        try:
            if self.icona:
                self.icona.notify(testo, titolo)
        except Exception:
            self.ponte._log()

    # --- chat degli altri PC (altri_pc.py) ---
    def pc_remoti(self) -> dict:
        attivo = imp_mod.leggi()["chat_altri_pc"]
        return {"pc": self.altri.elenco() if attivo else [], "attivo": attivo, "questo": self.altri.pc,
                "errore": self.altri.errore}

    def _ciclo_altri_pc(self) -> None:
        time.sleep(5)
        ultimo_errore = None
        while not self.uscendo:
            errore = None
            try:
                if imp_mod.leggi()["chat_altri_pc"] and self.github.repo():
                    self.altri.pubblica(altri_pc.riepilogo(self.ponte.voci_per_altri_pc(), VERSIONE))
                    if self.altri.leggi():
                        self.emetti("pc-remoti", self.pc_remoti())
            except PermissionError:
                errore = "Collega GitHub per vedere le chat degli altri PC"
            except urllib.error.HTTPError as e:
                if e.code == 401 and self.github.rifiutato("chat degli altri PC", e):
                    errore = "Accesso a GitHub scaduto: ricollega GitHub per vedere le chat degli altri PC"
                elif e.code == 401:
                    errore = "GitHub ha rifiutato l'accesso per un momento: riprovo tra poco"
                else:
                    errore = f"GitHub non raggiungibile (errore {e.code})"
                    if errore != ultimo_errore:
                        self.ponte._log()
            except Exception as e:
                errore = f"GitHub non raggiungibile ({type(e).__name__})"
                if errore != ultimo_errore:
                    self.ponte._log()
            if errore != self.altri.errore:
                self.altri.errore = errore
                self.emetti("pc-remoti", self.pc_remoti())
            ultimo_errore = errore
            for _ in range(10):
                if self.uscendo:
                    return
                time.sleep(1)

    def _ultimo_stato_altri_pc(self) -> None:
        # all'uscita: le chat di questo PC non risultano piu' aperte agli altri
        def lavoro():
            try:
                if imp_mod.leggi()["chat_altri_pc"] and self.github.repo():
                    self.altri.pubblica(altri_pc.riepilogo(self.ponte.voci_per_altri_pc(), VERSIONE, uscita=True), forza=True)
            except Exception:
                pass
        t = threading.Thread(target=lavoro, name="altri-pc-uscita", daemon=True)
        t.start()
        t.join(8)

    def _sync_automatica(self) -> None:
        while not self.uscendo:
            time.sleep(30)
            try:
                minuti = imp_mod.leggi()["sync_minuti"]
                if minuti and time.time() - self._ultima_sync >= minuti * 60:
                    self._ultima_sync = time.time()
                    st = self.github.stato()
                    if st.get("collegato") and st.get("repo") and not st.get("in_corso"):
                        self.sincronizza()
            except Exception:
                self.ponte._log()

    # --- eventi verso l'interfaccia ---
    def emetti(self, nome: str, dati) -> None:
        if self.finestra is None:
            return
        try:
            self.finestra.evaluate_js(f"window.sb && window.sb.evento({json.dumps(nome)}, {json.dumps(dati)})")
        except Exception:
            pass

    # --- finestra ---
    def mostra(self) -> None:
        if self.finestra:
            self.finestra.show()
            self.finestra.restore()
            self.emetti("mostrata", {})

    def nascondi(self) -> dict:
        if self.finestra:
            self.finestra.hide()
        return {"ok": True}

    def _in_chiusura(self) -> bool:
        if self.uscendo:
            return True
        self.nascondi()
        return False  # annulla la chiusura: resta nell'area di notifica

    def esci(self, forza: bool = False) -> dict:
        if not forza and self.terminali.attive():
            self.mostra()
            self.emetti("conferma-uscita", {"aperte": len(self.terminali.attive())})
            return {"conferma": True}
        self.uscendo = True
        self.terminali.chiudi_tutte()
        self._ultimo_stato_altri_pc()
        self._aggiorna_dopo_uscita()
        if self.icona:
            self.icona.stop()
        if self.finestra:
            self.finestra.destroy()
        return {"ok": True}

    # --- primo avvio ---
    def scegli_cartella(self, iniziale=None) -> dict:
        import webview
        try:
            scelta = self.finestra.create_file_dialog(webview.FileDialog.FOLDER, directory=iniziale or str(Path.home()))
        except Exception:
            self.ponte._log()
            return {"errore": "Non riesco ad aprire la scelta della cartella"}
        return {"percorso": scelta[0] if scelta else None}

    def completa_configurazione(self, scelte) -> dict:
        try:
            esito = configurazione.completa(scelte, self.github, QUI / "hooks")
        except Exception as e:
            self.ponte._log()
            return {"errore": f"Configurazione non riuscita: {e}"}
        if esito.get("ok"):
            self.ricarica_radice(Path(esito["radice"]))
        return esito

    def ricarica_radice(self, radice: Path) -> None:
        # il ponte riparte sulla cartella nuova; GitHub tiene l'accesso gia' fatto
        self.ponte = Ponte(radice=radice, cartella_sessioni=cartella_sessioni(radice), terminali=self.terminali)
        self.ponte.emetti = self.emetti
        self.github.radice = radice
        self.github._log = self.ponte._log
        self.ponte.token_git = self.github._token
        self.altri._log = self.ponte._log

    # --- file trascinati nell'Inbox ---
    def _al_caricamento(self) -> None:
        try:
            from webview.dom import DOMEventHandler
            doc = self.finestra.dom.document
            doc.events.dragover += DOMEventHandler(lambda e: None, True, True)
            doc.events.drop += DOMEventHandler(self._rilascio, True, True)
        except Exception:
            self.ponte._log()

    def _rilascio(self, evento) -> None:
        file = ((evento or {}).get("dataTransfer") or {}).get("files") or []
        percorsi = [f.get("pywebviewFullPath") for f in file if isinstance(f, dict) and f.get("pywebviewFullPath")]
        if not percorsi:
            return
        if self.pagina != "inbox":
            self.emetti("inbox-altrove", {})
            return
        self.emetti("inbox-aggiunti", self.ponte.aggiungi_inbox(percorsi))

    # --- sincronizzazione con GitHub ---
    def sincronizza(self) -> dict:
        esito = self.github.sincronizza()
        try:
            self.ponte._lavoro_sync()
        except Exception:
            self.ponte._log()
        return esito

    # --- aggiornamento in app ---
    # build.ps1 compila l'installer; se l'app e' aperta scrive cache/aggiornamento.json
    # ({versione, setup}). Il pulsante "Aggiornamento pronto" lancia l'installer in modalita'
    # rapida: barra di avanzamento visibile e app riaperta alla fine (con le chat di prima).
    def _aggiornamento(self) -> dict | None:
        try:
            d = json.loads((CACHE / "aggiornamento.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(d, dict) or not Path(str(d.get("setup", ""))).is_file():
            return None
        nuova, attuale = aggiornamenti.numeri(d.get("versione")), aggiornamenti.numeri(VERSIONE)
        if d.get("versione") == VERSIONE or (nuova and attuale and nuova <= attuale):
            return None  # gia' installata (o piu' vecchia di quella in uso)
        return d

    def _errore_aggiornamento(self) -> None:
        # l'ultimo aggiornamento non e' andato: lo si dice (il pulsante resta, si puo' riprovare)
        file = CACHE / "aggiornamento-errore.json"
        try:
            e = json.loads(file.read_text(encoding="utf-8-sig"))
            file.unlink()
        except (OSError, ValueError):
            return
        self._notifica(f"L'installazione della versione {e.get('versione', '')} non è riuscita (codice {e.get('codice')}). "
                       "Riprova con \"Aggiornamento pronto\"; i dettagli sono in setup-ultimo.log (Impostazioni → Dati → Registri).",
                       "Aggiornamento non riuscito")

    def cerca_aggiornamenti(self) -> dict:
        # release di GitHub: se ce n'e' una piu' nuova scarica l'installer e prepara il pulsante
        imp = imp_mod.leggi()
        try:
            return {"ok": True, **aggiornamenti.controlla(VERSIONE, imp["aggiornamenti_prova"], self.github._token(), CACHE)}
        except urllib.error.HTTPError as e:
            if e.code == 401:
                if self.github.rifiutato("aggiornamenti", e):
                    return {"errore": "Accesso a GitHub scaduto: ricollega GitHub per ricevere gli aggiornamenti"}
                return {"errore": "GitHub ha rifiutato l'accesso per un momento: riprova tra poco"}
            self.ponte._log()
            return {"errore": f"Controllo non riuscito: {e}"}
        except Exception as e:
            self.ponte._log()
            return {"errore": f"Controllo non riuscito: {e}"}

    def _aggiornamenti_periodici(self) -> None:
        time.sleep(60)
        while not self.uscendo:
            if imp_mod.leggi()["aggiornamenti_auto"] and not self.aggiornamento_pronto():
                self.cerca_aggiornamenti()
            for _ in range(6 * 3600):
                if self.uscendo:
                    return
                time.sleep(1)

    def aggiornamento_pronto(self) -> bool:
        return self._aggiornamento() is not None

    def aggiorna(self) -> dict:
        # le chiamate dall'interfaccia arrivano in thread separati: un doppio clic ne fa due.
        # Solo la prima procede (prima lanciava piu' installer insieme, falliti con codice 1)
        if not self._blocco_aggiorna.acquire(blocking=False):
            return {"in_corso": True}
        if getattr(self, "_aggiornamento_avviato_ora", False):
            self._blocco_aggiorna.release()
            return {"in_corso": True}
        try:
            esito = self._aggiorna()
            self._aggiornamento_avviato_ora = "errore" not in esito
            return esito
        finally:
            self._blocco_aggiorna.release()

    def _aggiorna(self) -> dict:
        if not self.aggiornamento_pronto():
            return {"errore": "Nessun aggiornamento pronto"}
        try:
            self.ponte._risolvi_schede()  # le chat nuove ricevono il loro id prima di chiudere
        except Exception:
            self.ponte._log()
        sessioni = [t.sessione for t in self.terminali.attive() if t.sessione]
        try:
            CACHE.mkdir(parents=True, exist_ok=True)
            (CACHE / "riapri.json").write_text(json.dumps(sessioni), encoding="utf-8")
        except OSError:
            self.ponte._log()
        self._riapri_dopo = True
        # lo script che installa parte prima di chiudere: se non parte l'app resta aperta e lo dice
        if not self._aggiorna_dopo_uscita():
            self._riapri_dopo = False
            return {"errore": "Non riesco ad avviare l'aggiornamento. Chiudi l'app con Esci e apri a mano "
                              f"l'installer: {self._aggiornamento().get('setup', '') if self._aggiornamento() else ''}"}
        return self.esci(forza=True)

    def da_riaprire(self) -> dict:
        file = CACHE / "riapri.json"
        try:
            sessioni = json.loads(file.read_text(encoding="utf-8"))
            file.unlink()
        except (OSError, ValueError):
            sessioni = []
        return {"sessioni": [s for s in sessioni if isinstance(s, str)]}

    def _aggiorna_dopo_uscita(self) -> bool:
        # se c'e' un aggiornamento pronto, un processo nascosto aspetta che questo processo
        # finisca e lancia l'installer: dal pulsante con la barra di avanzamento e la
        # riapertura dell'app; da "Esci" in silenzio e senza riaprire.
        # True se il processo che aspetta e' partito (o non serviva). Regole: docs/AGGIORNAMENTI.md
        if getattr(self, "_aggiornatore_avviato", False):
            return True
        agg = self._aggiornamento()
        if not agg:
            return True
        riapri = getattr(self, "_riapri_dopo", False)
        script = script_aggiornamento(os.getpid(), str(agg["setup"]), str(agg.get("versione", "")), riapri,
                                      Path(sys.executable).parent if getattr(sys, "frozen", False) else None, CACHE)
        try:
            file = CACHE / "applica-aggiornamento.ps1"
            file.write_text(script, encoding="utf-8")
        except OSError:
            self.ponte._log()
            return False
        self._aggiornatore_avviato = avvia_staccato(file)
        if not self._aggiornatore_avviato:
            self.ponte._log()
        return self._aggiornatore_avviato

    # --- istanza unica ---
    def _ascolta_istanze(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.bind(("127.0.0.1", PORTA_ISTANZA))
        except OSError:
            return
        server.listen()
        while not self.uscendo:
            try:
                conn, _ = server.accept()
                with conn:
                    conn.settimeout(3)
                    comando = b""
                    while not comando.endswith(b"\n") and len(comando) < 256 * 1024:
                        pezzo = conn.recv(65536)
                        if not pezzo:
                            break
                        comando += pezzo
                    if comando.startswith(b"vai "):
                        self.mostra()
                        self.emetti("vai-chat", {"sessione": comando[4:].decode("utf-8", "ignore").strip()})
                    elif comando.startswith(b"chat "):
                        self._chat_da_fuori(comando[5:])
                    elif comando.startswith(b"nuova"):
                        self._nuova_chat()
                    elif comando.startswith(b"mostra"):
                        self.mostra()
            except OSError:
                break

    def _chat_da_fuori(self, dati: bytes) -> None:
        try:
            d = json.loads(dati.decode("utf-8-sig"))
        except ValueError:
            return
        if isinstance(d, dict) and isinstance(d.get("prompt"), str) and d["prompt"].strip():
            self.mostra()
            self.emetti("apri-chat", {"prompt": d["prompt"], "cartella": d.get("cartella") or None,
                                     "titolo": d.get("titolo") or None})

    # --- area di notifica ---
    def _avvia_icona(self) -> None:
        import pystray
        from PIL import Image
        immagine = Image.open(QUI / "web" / "icona.png")
        menu = pystray.Menu(
            pystray.MenuItem("Apri Second Brain", lambda: self.mostra(), default=True),
            pystray.MenuItem("Nuova chat", lambda: self._nuova_chat()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Esci", lambda: self.esci()))
        self.icona = pystray.Icon("second-brain", immagine, TITOLO, menu)
        self.icona.run_detached()

    def _nuova_chat(self) -> None:
        self.mostra()
        self.emetti("nuova-chat", {})

    # --- notifiche di Windows ---
    def _notifiche(self) -> None:
        file = CACHE / "notifiche.json"
        time.sleep(PRIMA_NOTIFICA)
        while not self.uscendo:
            try:
                oggi = date.today().isoformat()
                try:
                    fatte = json.loads(file.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    fatte = {}
                if fatte.get("data") != oggi:
                    fatte = {"data": oggi, "chiavi": []}
                if not struttura.ha_indice(self.ponte.radice):
                    raise _Salta
                imp = imp_mod.leggi()
                if imp_mod.in_silenzio(imp):
                    raise _Salta
                stato = self.ponte.stato_notifiche()
                if not imp["notifica_non_salvate"]:
                    stato["non_salvate"] = []
                if not imp["notifica_sync"]:
                    stato["sync"] = ""
                if not imp["notifica_inbox"]:
                    stato["inbox"] = 0
                if not imp["notifica_scadenze"]:
                    stato["scadenze"] = None
                messaggi = []
                for c in stato["non_salvate"]:
                    chiave = f"chat:{c['id']}"
                    if chiave not in fatte["chiavi"]:
                        messaggi.append((chiave, f"Chat non salvata: {c['etichetta']}"))
                if stato["sync"] == "rosso" and "sync" not in fatte["chiavi"]:
                    messaggi.append(("sync", "Il PC non ha gli ultimi appunti: apri una chat per scaricarli"))
                if stato["inbox"] and f"inbox:{stato['inbox']}" not in fatte["chiavi"]:
                    messaggi.append((f"inbox:{stato['inbox']}", f"{stato['inbox']} note da smistare in Inbox"))
                if stato.get("scadenze") and "scadenze" not in fatte["chiavi"]:
                    messaggi.append(("scadenze", stato["scadenze"]))
                if messaggi and self.icona:
                    # Windows accetta al massimo 256 caratteri per notifica
                    testo = "\n".join(m if len(m) <= 110 else m[:109] + "…" for _, m in messaggi[:3])[:250]
                    self._notifica(testo, TITOLO)
                    fatte["chiavi"] += [k for k, _ in messaggi]
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_text(json.dumps(fatte), encoding="utf-8")
            except _Salta:
                pass  # primo avvio non ancora fatto, o silenzio
            except Exception:
                self.ponte._log()
            for _ in range(OGNI):
                if self.uscendo:
                    return
                time.sleep(1)

    def avvia(self) -> None:
        import webview
        if getattr(sys, "frozen", False):
            notifiche_win.imposta_aumid()
            notifiche_win.registra_protocollo(sys.executable)
        self.terminali.avvia()
        threading.Thread(target=self._ascolta_istanze, name="istanza", daemon=True).start()
        self.finestra = webview.create_window(
            TITOLO, url=str(QUI / "web" / "index.html"), js_api=Api(self),
            width=1360, height=860, min_size=(980, 640), hidden=self.nascosta,
            background_color="#0e1a22", text_select=True)
        self.finestra.events.closing += self._in_chiusura
        self.finestra.events.loaded += self._al_caricamento

        def dopo_avvio():
            try:
                self._avvia_icona()
            except Exception:
                self.ponte._log()
            threading.Thread(target=self._notifiche, name="notifiche", daemon=True).start()
            threading.Thread(target=self._avvisi, name="avvisi", daemon=True).start()
            threading.Thread(target=self._sync_automatica, name="sync-auto", daemon=True).start()
            threading.Thread(target=self._aggiornamenti_periodici, name="aggiornamenti", daemon=True).start()
            self._errore_aggiornamento()
            threading.Thread(target=self._ciclo_altri_pc, name="altri-pc", daemon=True).start()
            self.aggiorna_scorciatoia()
            if self.nuova_chat:
                time.sleep(2)
                self._nuova_chat()
        CACHE.mkdir(parents=True, exist_ok=True)
        svuota_cache_interfaccia(CACHE / "webview")
        webview.start(dopo_avvio, debug=self.debug, private_mode=False,
                      storage_path=str(CACHE / "webview"))
        self.uscendo = True
        self.terminali.chiudi_tutte()
        if self.icona:
            try:
                self.icona.stop()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nascosta", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--nuova-chat", action="store_true")
    parser.add_argument("--chat", help="apre una chat con questo compito (app gia' aperta)")
    parser.add_argument("--cartella", help="cartella di lavoro della chat di --chat")
    parser.add_argument("--titolo", help="nome della scheda di --chat")
    parser.add_argument("--link", help="collegamento secondbrainstudio:// (clic su una notifica)")
    args = parser.parse_args()
    if args.link:
        tipo, sessione = notifiche_win.leggi_link(args.link)
        comando = f"vai {sessione}".encode() if tipo == "chat" else b"mostra"
        if gia_aperta(comando):
            return
    elif args.chat:
        comando = b"chat " + json.dumps({"prompt": args.chat, "cartella": args.cartella, "titolo": args.titolo}).encode()
    else:
        comando = b"nuova" if args.nuova_chat else b"mostra"
    if gia_aperta(comando):
        return
    App(args.nascosta, args.debug, args.nuova_chat).avvia()


if __name__ == "__main__":
    main()
