# Canali standard validi per i comandi lanciati dall'app.
# Se l'app la apre un altro programma (l'installer dopo un aggiornamento, l'avvio con
# Windows), il processo puo' ereditare canali standard non validi: ogni subprocess che
# non li imposta tutti e tre fallisce con "[WinError 6] Handle non valido". Ne seguivano
# aggiornamento che non parte, "Nessun repository" e semaforo grigio.
# Nell'app impacchettata (finestra, nessuna console) i canali non servono: si mettono
# sempre su NUL. Da sorgente si sostituiscono solo quelli che subprocess non riuscirebbe a
# duplicare (stesso controllo che fa subprocess). Va chiamato una volta, all'avvio.
import os
import sys

_CANALI = ((-10, os.O_RDONLY), (-11, os.O_WRONLY), (-12, os.O_WRONLY))  # ingresso, uscita, errori


def _duplicabile(h) -> bool:
    import _winapi
    try:
        d = _winapi.DuplicateHandle(_winapi.GetCurrentProcess(), h, _winapi.GetCurrentProcess(),
                                    0, 1, _winapi.DUPLICATE_SAME_ACCESS)
        _winapi.CloseHandle(d)
        return True
    except OSError:
        return False


def sistema(sempre: bool | None = None) -> list[int]:
    # restituisce i codici dei canali sostituiti (per il registro e per i test)
    if os.name != "nt":
        return []
    import ctypes
    import msvcrt
    import _winapi
    if sempre is None:
        sempre = bool(getattr(sys, "frozen", False))
    k = ctypes.WinDLL("kernel32")
    k.SetStdHandle.argtypes = [ctypes.c_ulong, ctypes.c_void_p]
    sostituiti = []
    for codice, modo in _CANALI:
        cod = codice & 0xFFFFFFFF
        if not sempre:
            h = _winapi.GetStdHandle(cod)
            if not h or _duplicabile(h):
                continue  # nessun canale (subprocess se la cava) o canale buono
        fd = os.open(os.devnull, modo)
        os.set_inheritable(fd, True)
        k.SetStdHandle(cod, msvcrt.get_osfhandle(fd))
        sostituiti.append(codice)
    return sostituiti
