# Pytest crea il collegamento "<nome>current" verso l'ultima cartella temporanea. Alcuni
# Windows 11 rifiutano di attraversare i collegamenti creati dai programmi (WinError 448,
# "punto di montaggio non attendibile") e i test falliscono in pulizia: il collegamento
# non serve, quindi non si crea.
import _pytest.pathlib
import _pytest.tmpdir


def _niente(*a, **k):
    return None


_pytest.pathlib._force_symlink = _niente
_pytest.tmpdir._force_symlink = _niente
