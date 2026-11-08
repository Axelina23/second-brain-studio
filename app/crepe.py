# Genera web/crepe.png: craquelure dello smalto (rete di celle poligonali irregolari,
# bianco smalto su trasparente, 256 px, ripetibile senza giunture) per le piastrelle dei
# progetti fermi. Celle di Voronoi su toro con bordi spezzati; alcuni lati mancano, come
# nelle crepe vere. Procedurale e deterministico (seme fisso). Uso: python Sistema/app/crepe.py
import math
import random
from pathlib import Path

from PIL import Image, ImageFilter, PngImagePlugin

QUI = Path(__file__).resolve().parent
LATO = 256
SCALA = 2
CELLE = 16


def main() -> None:
    rnd = random.Random(1742)  # anno del chiostro maiolicato
    n = LATO * SCALA
    siti = [(rnd.uniform(0, n), rnd.uniform(0, n)) for _ in range(CELLE)]
    # deformazione leggera delle coordinate: lati non perfettamente dritti
    fasi = [rnd.uniform(0, 6.28) for _ in range(4)]

    def vicino(x, y):
        x += 4 * SCALA * math.sin(2 * math.pi * y / n * 3 + fasi[0])
        y += 4 * SCALA * math.sin(2 * math.pi * x / n * 2 + fasi[1])
        meglio, i_meglio = 1e18, 0
        for i, (sx, sy) in enumerate(siti):
            dx = min(abs(x - sx), n - abs(x - sx))
            dy = min(abs(y - sy), n - abs(y - sy))
            d = dx * dx + dy * dy
            if d < meglio:
                meglio, i_meglio = d, i
        return i_meglio

    etichette = [[vicino(x, y) for x in range(n)] for y in range(n)]
    # ogni coppia di celle confinanti: tenuta o no, e con quale intensita'
    tenuti = {}
    maschera = Image.new("L", (n, n), 0)
    px = maschera.load()
    for y in range(n):
        riga, sotto = etichette[y], etichette[(y + 1) % n]
        for x in range(n):
            a, b, c = riga[x], riga[(x + 1) % n], sotto[x]
            for altro in (b, c):
                if altro != a:
                    coppia = (min(a, altro), max(a, altro))
                    if coppia not in tenuti:
                        tenuti[coppia] = rnd.random() < 0.8 and rnd.uniform(150, 255)
                    if tenuti[coppia]:
                        px[x, y] = int(tenuti[coppia])
    maschera = maschera.filter(ImageFilter.GaussianBlur(0.6)).resize((LATO, LATO), Image.LANCZOS)
    img = Image.new("RGBA", (LATO, LATO), (241, 236, 224, 0))
    img.putalpha(maschera)
    info = PngImagePlugin.PngInfo()
    info.add_text("provenance", "Procedurale: Sistema/app/crepe.py (Pillow, Voronoi su toro, seme 1742), Second Brain 2026-11-07")
    img.save(QUI / "web" / "crepe.png", pnginfo=info)
    print("web/crepe.png scritta")


if __name__ == "__main__":
    main()
