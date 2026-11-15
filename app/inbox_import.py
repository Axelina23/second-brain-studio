"""Importazioni esplicite nell'Inbox, senza sovrascrivere file esistenti."""
import base64
import io
import re
import shutil
from pathlib import Path

from PIL import Image, ImageGrab


def scrivi_unico(cartella, nome, scrivi):
    cartella.mkdir(parents=True, exist_ok=True)
    n = 1
    while True:
        p = cartella / (nome if n == 1 else f"{Path(nome).stem}-{n}{Path(nome).suffix}")
        try:
            f = p.open("xb")
        except FileExistsError:
            n += 1
            continue
        try:
            with f:
                scrivi(f)
        except Exception:
            p.unlink(missing_ok=True)
            raise
        return p.name


def copia_file(cartella, percorsi, adesso):
    aggiunti, saltati = [], []
    for percorso in percorsi or []:
        p = Path(percorso)
        try:
            if not p.is_file():
                saltati.append(p.name or str(p))
                continue
            nome = p.name if re.match(r"^\d{4}-\d{2}-\d{2} ", p.name) else f"{adesso:%Y-%m-%d} {p.name}"
            with p.open("rb") as sorgente:
                aggiunti.append(scrivi_unico(cartella, nome, lambda f: shutil.copyfileobj(sorgente, f)))
        except OSError:
            saltati.append(p.name)
    return {"aggiunti": aggiunti, "saltati": saltati}


def incolla_immagine(cartella, adesso, dati=None):
    try:
        if dati is None:
            immagine = ImageGrab.grabclipboard()
            if not isinstance(immagine, Image.Image):
                return {"errore": "Nessuna immagine negli appunti. Fai uno screenshot e riprova."}
        else:
            if not isinstance(dati, str) or len(dati) > 40 * 1024 * 1024:
                return {"errore": "Immagine troppo grande (massimo 30 MB)."}
            immagine = Image.open(io.BytesIO(base64.b64decode(dati, validate=True)))
        with immagine:
            immagine.load()
            nome = f"{adesso:%Y-%m-%d} screenshot {adesso:%H%M%S}.png"
            aggiunto = scrivi_unico(cartella, nome, lambda f: immagine.save(f, format="PNG"))
        return {"aggiunti": [aggiunto], "saltati": []}
    except (OSError, ValueError, Image.DecompressionBombError):
        return {"errore": "Non riesco a incollare l'immagine. Copiala di nuovo e riprova."}


def miniatura(percorso):
    if percorso.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
        return ""
    try:
        with Image.open(percorso) as im:
            im.thumbnail((480, 280))
            out = io.BytesIO()
            im.convert("RGB").save(out, format="JPEG", quality=75)
            return "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode("ascii")
    except (OSError, ValueError, Image.DecompressionBombError):
        return ""
