// Estensione COM del menu moderno di Esplora file: nessuna lettura dei file durante
// la costruzione del menu. Invoke consegna soltanto i percorsi selezionati a SBS.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shobjidl.h>
#include <shlwapi.h>
#include <string>
#include <new>

static const CLSID CLSID_Inbox = {0x82d0325c,0x7cb8,0x4ac5,{0xa3,0x66,0x40,0x96,0xb7,0xf5,0xa2,0x31}};
static HMODULE modulo;
static LONG oggetti = 0;
static bool italiano() { return PRIMARYLANGID(GetUserDefaultUILanguage()) == LANG_ITALIAN; }

static std::wstring eseguibile() {
    wchar_t percorso[32768];
    DWORD n = GetModuleFileNameW(modulo, percorso, ARRAYSIZE(percorso));
    if (!n || n == ARRAYSIZE(percorso)) return L"";
    PathRemoveFileSpecW(percorso); // _shell
    PathRemoveFileSpecW(percorso); // cartella dell'app
    return std::wstring(percorso) + L"\\Second Brain Studio.exe";
}

// Quoting degli argomenti secondo CommandLineToArgvW, compresi backslash finali.
static std::wstring quota(const std::wstring& valore) {
    std::wstring r = L"\"";
    size_t slash = 0;
    for (wchar_t c : valore) {
        if (c == L'\\') { ++slash; continue; }
        r.append(c == L'"' ? slash * 2 + 1 : slash, L'\\');
        slash = 0;
        r += c;
    }
    r.append(slash * 2, L'\\');
    return r + L"\"";
}

class Comando final : public IExplorerCommand {
    LONG riferimenti = 1;
public:
    Comando() { InterlockedIncrement(&oggetti); }
    ~Comando() { InterlockedDecrement(&oggetti); }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** pp) override {
        if (!pp) return E_POINTER;
        *pp = nullptr;
        if (iid == IID_IUnknown || iid == IID_IExplorerCommand) {
            *pp = static_cast<IExplorerCommand*>(this); AddRef(); return S_OK;
        }
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&riferimenti); }
    ULONG STDMETHODCALLTYPE Release() override {
        LONG r = InterlockedDecrement(&riferimenti); if (!r) delete this; return r;
    }
    HRESULT STDMETHODCALLTYPE GetTitle(IShellItemArray*, LPWSTR* titolo) override {
        return SHStrDupW(italiano() ? L"Invia a Inbox" : L"Send to Inbox", titolo);
    }
    HRESULT STDMETHODCALLTYPE GetIcon(IShellItemArray*, LPWSTR* icona) override {
        auto percorso = eseguibile();
        if (percorso.empty()) return E_FAIL;
        return SHStrDupW((percorso + L",0").c_str(), icona);
    }
    HRESULT STDMETHODCALLTYPE GetToolTip(IShellItemArray*, LPWSTR* testo) override {
        return SHStrDupW(italiano() ? L"Copia i file nell'Inbox di Second Brain Studio" : L"Copy files to Second Brain Studio Inbox", testo);
    }
    HRESULT STDMETHODCALLTYPE GetCanonicalName(GUID* guid) override {
        if (!guid) return E_POINTER; *guid = CLSID_Inbox; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE GetState(IShellItemArray* elementi, BOOL, EXPCMDSTATE* stato) override {
        if (!stato) return E_POINTER;
        *stato = ECS_HIDDEN;
        if (!elementi) return S_OK;
        SFGAOF attributi = 0;
        DWORD n = 0;
        if (FAILED(elementi->GetCount(&n)) || !n ||
            FAILED(elementi->GetAttributes(SIATTRIBFLAGS_OR, SFGAO_FOLDER, &attributi))) return S_OK;
        if (attributi & SFGAO_FOLDER) {
            // Gli ZIP hanno anche SFGAO_FOLDER: SFGAO_STREAM li distingue dalle directory.
            for (DWORD i = 0; i < n; ++i) {
                IShellItem* elemento = nullptr;
                if (FAILED(elementi->GetItemAt(i, &elemento))) return S_OK;
                SFGAOF a = 0;
                HRESULT hr = elemento->GetAttributes(SFGAO_FOLDER | SFGAO_STREAM, &a);
                elemento->Release();
                if (FAILED(hr) || ((a & SFGAO_FOLDER) && !(a & SFGAO_STREAM))) return S_OK;
            }
        }
        *stato = ECS_ENABLED;
        return S_OK;
    }
    HRESULT STDMETHODCALLTYPE Invoke(IShellItemArray* elementi, IBindCtx*) override {
        if (!elementi) return E_INVALIDARG;
        try {
            auto exe = eseguibile();
            if (exe.empty()) return E_FAIL;
            std::wstring comando = quota(exe) + L" --inbox";
            DWORD n = 0;
            HRESULT hr = elementi->GetCount(&n);
            if (FAILED(hr) || !n) return E_INVALIDARG;
            for (DWORD i = 0; i < n; ++i) {
                IShellItem* elemento = nullptr;
                hr = elementi->GetItemAt(i, &elemento);
                if (FAILED(hr)) return hr;
                PWSTR percorso = nullptr;
                hr = elemento->GetDisplayName(SIGDN_FILESYSPATH, &percorso);
                elemento->Release();
                if (FAILED(hr)) return hr;
                comando += L" " + quota(percorso);
                CoTaskMemFree(percorso);
            }
            if (comando.size() >= 32767) {
                MessageBoxW(nullptr, italiano() ? L"Troppi file selezionati. Inviali in gruppi piu' piccoli." : L"Too many files selected. Send them in smaller groups.", L"Second Brain Studio", MB_OK | MB_ICONINFORMATION);
                return HRESULT_FROM_WIN32(ERROR_BUFFER_OVERFLOW);
            }
            STARTUPINFOW avvio = {sizeof(avvio)};
            PROCESS_INFORMATION processo = {};
            if (!CreateProcessW(exe.c_str(), comando.data(), nullptr, nullptr, FALSE, CREATE_NO_WINDOW, nullptr, nullptr, &avvio, &processo)) {
                DWORD errore = GetLastError();
                MessageBoxW(nullptr, italiano() ? L"Non riesco ad aprire Second Brain Studio. Prova a reinstallare l'app." : L"Cannot open Second Brain Studio. Try reinstalling the app.", L"Second Brain Studio", MB_OK | MB_ICONERROR);
                return HRESULT_FROM_WIN32(errore);
            }
            CloseHandle(processo.hThread); CloseHandle(processo.hProcess);
            return S_OK;
        } catch (...) { return E_OUTOFMEMORY; }
    }
    HRESULT STDMETHODCALLTYPE GetFlags(EXPCMDFLAGS* flags) override {
        if (!flags) return E_POINTER; *flags = ECF_DEFAULT; return S_OK;
    }
    HRESULT STDMETHODCALLTYPE EnumSubCommands(IEnumExplorerCommand** comandi) override {
        if (!comandi) return E_POINTER; *comandi = nullptr; return E_NOTIMPL;
    }
};

class Fabbrica final : public IClassFactory {
    LONG riferimenti = 1;
public:
    Fabbrica() { InterlockedIncrement(&oggetti); }
    ~Fabbrica() { InterlockedDecrement(&oggetti); }
    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID iid, void** pp) override {
        if (!pp) return E_POINTER; *pp = nullptr;
        if (iid == IID_IUnknown || iid == IID_IClassFactory) { *pp = static_cast<IClassFactory*>(this); AddRef(); return S_OK; }
        return E_NOINTERFACE;
    }
    ULONG STDMETHODCALLTYPE AddRef() override { return InterlockedIncrement(&riferimenti); }
    ULONG STDMETHODCALLTYPE Release() override { LONG r = InterlockedDecrement(&riferimenti); if (!r) delete this; return r; }
    HRESULT STDMETHODCALLTYPE CreateInstance(IUnknown* esterno, REFIID iid, void** pp) override {
        if (!pp) return E_POINTER; *pp = nullptr;
        if (esterno) return CLASS_E_NOAGGREGATION;
        auto c = new(std::nothrow) Comando();
        if (!c) return E_OUTOFMEMORY;
        HRESULT hr = c->QueryInterface(iid, pp); c->Release(); return hr;
    }
    HRESULT STDMETHODCALLTYPE LockServer(BOOL blocca) override { if (blocca) InterlockedIncrement(&oggetti); else InterlockedDecrement(&oggetti); return S_OK; }
};

extern "C" __declspec(dllexport) HRESULT __stdcall DllGetClassObject(REFCLSID clsid, REFIID iid, void** pp) {
    if (!pp) return E_POINTER; *pp = nullptr;
    if (clsid != CLSID_Inbox) return CLASS_E_CLASSNOTAVAILABLE;
    auto f = new(std::nothrow) Fabbrica();
    if (!f) return E_OUTOFMEMORY;
    HRESULT hr = f->QueryInterface(iid, pp); f->Release(); return hr;
}
extern "C" __declspec(dllexport) HRESULT __stdcall DllCanUnloadNow() { return InterlockedCompareExchange(&oggetti, 0, 0) ? S_FALSE : S_OK; }
BOOL WINAPI DllMain(HINSTANCE istanza, DWORD motivo, LPVOID) {
    if (motivo == DLL_PROCESS_ATTACH) { modulo = istanza; DisableThreadLibraryCalls(istanza); }
    return TRUE;
}
