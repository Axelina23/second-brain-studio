# Aggiunge motore/ al path cosi' i test importano i moduli direttamente.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
