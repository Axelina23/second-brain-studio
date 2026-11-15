"""Prova COM della DLL compilata, senza registrazione o modifiche a Esplora file."""
import argparse
import ctypes as c
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
from pathlib import Path


def guid(s):
    return (c.c_ubyte * 16).from_buffer_copy(uuid.UUID(s).bytes_le)


def metodo(p, slot, ritorno, *tipi):
    vtable = c.cast(p, c.POINTER(c.POINTER(c.c_void_p))).contents
    return c.WINFUNCTYPE(ritorno, c.c_void_p, *tipi)(vtable[slot])


def verifica(zig):
    dll_originale = Path(__file__).parent / "dist" / "SBSInbox.dll"
    with tempfile.TemporaryDirectory(prefix="sbs-menu-test-", ignore_cleanup_errors=True) as td:
        root = Path(td)
        (root / "_shell").mkdir()
        shutil.copy2(dll_originale, root / "_shell" / dll_originale.name)
        probe = root / "probe.c"
        probe.write_text(r'''
#include <windows.h>
#include <wchar.h>
int main(void) {
 wchar_t path[32768]; GetModuleFileNameW(NULL,path,32768);
 wchar_t* last=wcsrchr(path,L'\\'); wcscpy(last+1,L"args.bin");
 HANDLE f=CreateFileW(path,GENERIC_WRITE,0,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
 DWORD n; const wchar_t* line=GetCommandLineW();
 WriteFile(f,line,(DWORD)(wcslen(line)*sizeof(wchar_t)),&n,NULL); CloseHandle(f); return 0;
}''', encoding="utf-8")
        subprocess.run([zig, "cc", str(probe), "-O2", "-o", str(root / "Second Brain Studio.exe")],
                       check=True, stdin=subprocess.DEVNULL, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        ole = c.OleDLL("ole32")
        ole.CoInitializeEx(None, 2)
        dll = c.WinDLL(str(root / "_shell" / dll_originale.name))
        factory = c.c_void_p()
        clsid = guid("82d0325c-7cb8-4ac5-a366-4096b7f5a231")
        iid_factory = guid("00000001-0000-0000-c000-000000000046")
        assert dll.DllGetClassObject(c.byref(clsid), c.byref(iid_factory), c.byref(factory)) == 0
        comando = c.c_void_p()
        iid_cmd = guid("a08ce4d0-fa25-44ab-b57c-c7b1c323e0b9")
        assert metodo(factory, 3, c.c_long, c.c_void_p, c.c_void_p, c.c_void_p)(factory, None, c.byref(iid_cmd), c.byref(comando)) == 0
        metodo(factory, 2, c.c_ulong)(factory)
        titolo = c.c_void_p()
        assert metodo(comando, 3, c.c_long, c.c_void_p, c.c_void_p)(comando, None, c.byref(titolo)) == 0
        assert c.wstring_at(titolo) in ("Invia a Inbox", "Send to Inbox")
        ole.CoTaskMemFree.argtypes = [c.c_void_p]
        ole.CoTaskMemFree(titolo)
        shell = c.WinDLL("shell32")
        shell.SHParseDisplayName.argtypes = [c.c_wchar_p, c.c_void_p, c.c_void_p, c.c_ulong, c.c_void_p]
        shell.SHCreateShellItemArrayFromIDLists.argtypes = [c.c_uint, c.c_void_p, c.c_void_p]

        def selezione(percorsi):
            pidls = (c.c_void_p * len(percorsi))()
            for i, p in enumerate(percorsi):
                ptr = c.c_void_p()
                shell.SHParseDisplayName(str(p), None, c.byref(ptr), 0, None)
                pidls[i] = ptr
            array = c.c_void_p()
            shell.SHCreateShellItemArrayFromIDLists(len(percorsi), pidls, c.byref(array))
            for ptr in pidls:
                ole.CoTaskMemFree(ptr)
            return array

        files = [root / "documento uno.pdf", root / "secondo è.txt"]
        for p in files:
            p.write_text("Dati inventati", encoding="utf-8")
        archivio = root / "archivio.zip"
        with zipfile.ZipFile(archivio, "w") as z:
            z.writestr("prova.txt", "Dati inventati")
        files.append(archivio)
        selezionati = selezione(files)
        stato = c.c_int()
        assert metodo(comando, 7, c.c_long, c.c_void_p, c.c_int, c.c_void_p)(comando, selezionati, 0, c.byref(stato)) == 0
        assert stato.value == 0  # ECS_ENABLED
        assert metodo(comando, 8, c.c_long, c.c_void_p, c.c_void_p)(comando, selezionati, None) == 0
        for _ in range(100):
            if (root / "args.bin").exists():
                break
            time.sleep(.03)
        linea = (root / "args.bin").read_bytes().decode("utf-16-le")
        shell.CommandLineToArgvW.argtypes = [c.c_wchar_p, c.c_void_p]
        shell.CommandLineToArgvW.restype = c.POINTER(c.c_wchar_p)
        n = c.c_int()
        argv = shell.CommandLineToArgvW(linea, c.byref(n))
        assert [argv[i] for i in range(1, n.value)] == ["--inbox", *map(str, files)]
        c.windll.kernel32.LocalFree.argtypes = [c.c_void_p]
        c.windll.kernel32.LocalFree(argv)
        metodo(selezionati, 2, c.c_ulong)(selezionati)
        cartella = selezione([root])
        assert metodo(comando, 7, c.c_long, c.c_void_p, c.c_int, c.c_void_p)(comando, cartella, 0, c.byref(stato)) == 0
        assert stato.value == 2  # ECS_HIDDEN
        metodo(cartella, 2, c.c_ulong)(cartella)
        metodo(comando, 2, c.c_ulong)(comando)
        assert dll.DllCanUnloadNow() == 0
        # Scarica la DLL prima della pulizia della cartella temporanea su Windows.
        c.windll.kernel32.FreeLibrary.argtypes = [c.c_void_p]
        c.windll.kernel32.FreeLibrary(dll._handle)
        ole.CoUninitialize()
        print("OK: COM, titolo, selezione multipla, Unicode/spazi, avvio con argomenti esatti, cartelle nascoste, scaricamento DLL")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--zig", required=True)
    verifica(parser.parse_args().zig)
