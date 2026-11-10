# Immagine di anteprima per i link condivisi (GitHub → Settings → Social preview, 1280x640):
# icona, nome, frase e uno screenshot inglese. Da rifare dopo screenshot.ps1 se cambia l'aspetto.
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

QUI = Path(__file__).parent
RADICE = QUI.parent.parent
W, H = 1280, 640
FONDO, CARTA, LIMONE, NEBBIA = "#0e1a22", "#f1ece0", "#f2c94c", "#9fb0b8"


def carattere(peso: int, dim: int):
    try:   # Figtree, il carattere dell'app (variabile)
        f = ImageFont.truetype(str(RADICE / "app/web/vendor/fonts/figtree-latin-wght-normal.woff2"), dim)
        f.set_variation_by_axes([peso])
        return f
    except Exception:
        return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if peso >= 600 else "C:/Windows/Fonts/segoeui.ttf", dim)


img = Image.new("RGB", (W, H), FONDO)
d = ImageDraw.Draw(img)

# screenshot a destra, con angoli arrotondati e ombra, che esce dal bordo
foto = Image.open(QUI / "en/oggi.png").convert("RGB").resize((900, 563), Image.LANCZOS)
maschera = Image.new("L", foto.size, 0)
ImageDraw.Draw(maschera).rounded_rectangle((0, 0, *foto.size), 18, fill=255)
x, y = 600, 70
ombra = Image.new("L", (W, H), 0)
ImageDraw.Draw(ombra).rounded_rectangle((x + 10, y + 20, x + foto.width + 10, y + foto.height + 20), 18, fill=150)
img.paste(Image.new("RGB", (W, H), "#04090c"), (0, 0), ombra.filter(ImageFilter.GaussianBlur(24)))
img.paste(foto, (x, y), maschera)
d.rounded_rectangle((x, y, x + foto.width, y + foto.height), 18, outline="#2a3a44", width=2)

# testo a sinistra
icona = Image.open(RADICE / "app/icona-1024.png").convert("RGBA").resize((104, 104), Image.LANCZOS)
img.paste(icona, (72, 112), icona)
titolo = carattere(750, 58)
d.text((72, 250), "Second Brain", font=titolo, fill=CARTA)
d.text((72, 316), "Studio", font=titolo, fill=LIMONE)
frase = carattere(450, 27)
for i, riga in enumerate(["Claude Code, Codex, Antigravity.", "Your second brain, in one window."]):
    d.text((72, 410 + i * 38), riga, font=frase, fill=NEBBIA)
d.text((72, 526), "Windows  ·  free  ·  source available", font=carattere(600, 20), fill="#86c5a1")

img.save(QUI / "anteprima-social.png", optimize=True)
print("anteprima-social.png")
