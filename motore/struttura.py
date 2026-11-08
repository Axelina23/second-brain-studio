# Struttura delle cartelle di un second brain, in italiano o in inglese.
# Il primo avvio sceglie la lingua (quella dell'interfaccia) e da li' in poi non cambia:
# si riconosce dal file indice presente (INDICE.md o INDEX.md), cosi' un second brain
# esistente resta com'e' anche se l'interfaccia cambia lingua.
# I gruppi della pagina Appunti e della Mappa usano nomi fissi ("Io", "Progetti", "Sistema",
# "Generali") qualunque sia la struttura; l'interfaccia li traduce. Le altre aree (Lavoro,
# Work, Università...) sono le cartelle stesse.
from pathlib import Path

STRUTTURE = {
    "it": {"indice": "INDICE.md", "io": "Io", "regole": "Io/Regole.md", "profilo": "Io/Profilo.md",
           "progetti": "Progetti", "personali": "Personali.md", "archivio": "Archivio",
           "registro": "Archivio/Registro.md", "sistema": "Sistema", "strumenti": "Sistema/strumenti.md",
           "inbox": "Inbox", "output": "Output", "stato": "stato.md"},
    "en": {"indice": "INDEX.md", "io": "Me", "regole": "Me/Rules.md", "profilo": "Me/Profile.md",
           "progetti": "Projects", "personali": "Personal.md", "archivio": "Archive",
           "registro": "Archive/Log.md", "sistema": "System", "strumenti": "System/tools.md",
           "inbox": "Inbox", "output": "Output", "stato": "status.md"},
}


def rileva(radice) -> str:
    # "en" solo se c'e' INDEX.md e non INDICE.md; in tutti gli altri casi "it" (anche cartella vuota)
    r = Path(radice)
    if (r / STRUTTURE["en"]["indice"]).is_file() and not (r / STRUTTURE["it"]["indice"]).is_file():
        return "en"
    return "it"


def di(radice) -> dict:
    # i nomi della struttura usata da questo second brain
    return STRUTTURE[rileva(radice)]


def ha_indice(radice) -> bool:
    r = Path(radice)
    return any((r / s["indice"]).is_file() for s in STRUTTURE.values())


def gruppo(cartella: str, s: dict) -> str | None:
    # gruppo della pagina Appunti per una cartella di primo livello; None = non e' un'area
    if cartella == s["io"]:
        return "Io"
    if cartella == s["sistema"]:
        return "Sistema"
    if cartella in (s["progetti"], s["archivio"], s["inbox"], s["output"]) or cartella.startswith((".", "_")):
        return None
    return cartella
