# Notifiche native di Windows (toast) che si possono cliccare: il clic apre un collegamento
# secondbrainstudio://chat/<sessione>, che Windows passa a "Second Brain Studio.exe --link ...";
# l'istanza gia' aperta riceve il comando e mostra quella chat (main.py).
# Senza librerie: il toast lo mostra PowerShell con le classi WinRT di Windows. Serve
# l'AppUserModelID dell'app sul collegamento del menu Start (installer.iss): dall'app avviata
# da sorgente il toast non compare e si torna alle notifiche semplici dell'area di notifica.
import base64
import os
import subprocess
import sys
from xml.sax.saxutils import escape, quoteattr

AUMID = "SecondBrainStudio.App"
PROTOCOLLO = "secondbrainstudio"
_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def imposta_aumid() -> None:
    # finestra, barra delle applicazioni e notifiche raggruppate sotto l'app installata
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(AUMID)
    except Exception:
        pass


def registra_protocollo(exe: str) -> bool:
    # HKCU\Software\Classes\secondbrainstudio -> "exe" --link "%1" (solo per l'utente, niente permessi)
    try:
        import winreg
        base = rf"Software\Classes\{PROTOCOLLO}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base) as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, "URL:Second Brain Studio")
            winreg.SetValueEx(k, "URL Protocol", 0, winreg.REG_SZ, "")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\DefaultIcon") as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, f'"{exe}",0')
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, base + r"\shell\open\command") as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, f'"{exe}" --link "%1"')
        return True
    except OSError:
        return False


def link_chat(sessione: str | None) -> str:
    return f"{PROTOCOLLO}://chat/{sessione}" if sessione else f"{PROTOCOLLO}://mostra"


def leggi_link(link: str) -> tuple[str, str | None]:
    # "secondbrainstudio://chat/<id>" -> ("chat", "<id>"); qualunque altra cosa -> ("mostra", None)
    testa = f"{PROTOCOLLO}://"
    resto = str(link or "").strip().strip('"')
    if not resto.lower().startswith(testa):
        return "mostra", None
    parti = resto[len(testa):].strip("/").split("/")
    if parti[0] == "chat" and len(parti) > 1 and all(c.isalnum() or c in "-_" for c in parti[1]) and len(parti[1]) <= 80:
        return "chat", parti[1]
    return "mostra", None


def xml_toast(titolo: str, testo: str, link: str) -> str:
    return (f'<toast activationType="protocol" launch={quoteattr(link)}>'
            f'<visual><binding template="ToastGeneric"><text>{escape(titolo[:60])}</text>'
            f'<text>{escape(testo[:250])}</text></binding></visual><audio src="ms-winsoundevent:Notification.Default"/></toast>')


def mostra(titolo: str, testo: str, link: str) -> bool:
    if sys.platform != "win32":
        return False
    # il testo (che arriva dalle risposte di Claude) non entra mai nel codice dello script:
    # passa da una variabile d'ambiente, in base64, e lo script la legge come dato
    xml = base64.b64encode(xml_toast(titolo, testo, link).encode("utf-8")).decode()
    script = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null\n"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null\n"
        "$x = New-Object Windows.Data.Xml.Dom.XmlDocument\n"
        "$x.LoadXml([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($env:SBS_TOAST)))\n"
        "$t = New-Object Windows.UI.Notifications.ToastNotification $x\n"
        f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{AUMID}').Show($t)\n")
    codificato = base64.b64encode(script.encode("utf-16-le")).decode()
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", codificato],
                           capture_output=True, timeout=15, creationflags=_FLAGS, env={**os.environ, "SBS_TOAST": xml})
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
