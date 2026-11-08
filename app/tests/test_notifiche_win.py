import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import notifiche_win as nw  # noqa: E402


def test_link_andata_e_ritorno():
    assert nw.leggi_link(nw.link_chat("a1b2-c3")) == ("chat", "a1b2-c3")
    assert nw.leggi_link('"secondbrainstudio://chat/abc/"') == ("chat", "abc")
    assert nw.leggi_link(nw.link_chat(None)) == ("mostra", None)


def test_link_sospetti_non_passano():
    for cattivo in ("secondbrainstudio://chat/../../x", "secondbrainstudio://chat/a b", "http://chat/abc",
                    "secondbrainstudio://chat/" + "a" * 100, "secondbrainstudio://chat/a;calc"):
        assert nw.leggi_link(cattivo) == ("mostra", None)


def test_xml_scappa_i_caratteri():
    x = nw.xml_toast("Tesi & <prova>", "risposta \"ok\" 'si'", nw.link_chat("s1"))
    assert "&amp;" in x and "&lt;prova&gt;" in x and 'launch="secondbrainstudio://chat/s1"' in x
