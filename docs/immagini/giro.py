# GIF del giro dell'app per il README: dissolvenze tra gli screenshot inglesi (en/*.png)
# e italiani, ridotti a 960 px. La lancia screenshot.ps1 dopo aver rifatto gli screenshot.
from pathlib import Path
from PIL import Image

QUI = Path(__file__).parent
PAGINE = ["oggi", "assistenti-codex", "assistenti-antigravity", "chat-pc", "appunti", "mappa-raggiera", "mappa-metro", "mappa-citta", "impostazioni", "oggi-chiaro"]
LARGO, FERMO, PASSI = 960, 1700, 4   # px, ms su ogni pagina, fotogrammi di dissolvenza


def giro(cartella: Path, uscita: Path):
    foto = [Image.open(cartella / f"{p}.png").convert("RGB") for p in PAGINE]
    foto = [f.resize((LARGO, round(f.height * LARGO / f.width)), Image.LANCZOS) for f in foto]
    fotogrammi, durate = [], []
    for i, f in enumerate(foto):
        fotogrammi.append(f); durate.append(FERMO)
        dopo = foto[(i + 1) % len(foto)]
        for k in range(1, PASSI + 1):
            fotogrammi.append(Image.blend(f, dopo, k / (PASSI + 1))); durate.append(60)
    # una tavolozza sola per tutta la GIF: niente sfarfallio dei colori tra i fotogrammi
    tav = Image.new("RGB", (LARGO, foto[0].height * len(foto)))
    for i, f in enumerate(foto):
        tav.paste(f, (0, i * f.height))
    tav = tav.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=tav, dither=Image.Dither.NONE) for f in fotogrammi]
    q[0].save(uscita, save_all=True, append_images=q[1:], duration=durate, loop=0, optimize=True)
    print(uscita.name, round(uscita.stat().st_size / 1e6, 1), "MB")


giro(QUI / "en", QUI / "en" / "tour.gif")
giro(QUI, QUI / "giro.gif")
