"""Le filigrane (0.1.2) : une capture d'écran d'une appli simulée doit se reconnaître."""
from __future__ import annotations

from urllib.parse import unquote

from app import filigrane


def test_filigrane_dit_bac_a_sable_et_l_appli():
    calque = filigrane.html("Douze points", "1.6.0")
    assert 'id="bac-a-sable-filigrane"' in calque
    assert "pointer-events:none" in calque and "position:fixed" in calque and "inset:0" in calque
    svg = unquote(calque.split("charset=utf-8,", 1)[1])
    assert "BAC À SABLE" in svg and "Douze points 1.6.0" in svg


def test_nom_echappe():
    svg = unquote(filigrane.motif("<script>"))
    assert "<script>" not in svg and "&lt;script&gt;" in svg
