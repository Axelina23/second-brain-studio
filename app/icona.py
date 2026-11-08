# Icona dell'app "Sinapsi": il disegno sorgente e' web/icona.svg; icona-1024.png e' il suo
# rendering a 1024 px con sfondo trasparente (fatto dal browser). Da questo si ricavano
# web/icona.png (256 px, area di notifica e barra laterale) e icona.ico (16-256 px).
# Uso: python icona.py
from pathlib import Path

from PIL import Image, PngImagePlugin

QUI = Path(__file__).resolve().parent


def main() -> None:
    grande = Image.open(QUI / "icona-1024.png").convert("RGBA")
    info = PngImagePlugin.PngInfo()
    info.add_text("provenance", "Rendering di web/icona.svg (vettoriale disegnato a mano), Second Brain Studio")
    grande.resize((256, 256), Image.LANCZOS).save(QUI / "web" / "icona.png", pnginfo=info)
    taglie = [16, 24, 32, 48, 64, 128, 256]
    immagini = [grande.resize((s, s), Image.LANCZOS) for s in taglie]
    immagini[-1].save(QUI / "icona.ico", sizes=[(s, s) for s in taglie], append_images=immagini[:-1])
    print("icona.png e icona.ico scritte")


if __name__ == "__main__":
    main()
