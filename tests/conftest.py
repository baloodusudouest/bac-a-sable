"""Réglages communs des tests : aucun réseau, dossiers temporaires, applis embarquées prises dans BAC_ESSAI_APPLIS
(code source + site-packages de chaque appli, comme dans l'image) quand on lance les essais de bout en bout."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from app import main  # noqa: E402
from app.config import Config  # noqa: E402

MOT_DE_PASSE = "mot-de-passe-du-bac"


def port_libre() -> int:
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def config(tmp_path: Path, **kw) -> Config:
    base = dict(password=MOT_DE_PASSE, data=tmp_path / "data", static=tmp_path / "static",
                applis=Path(os.environ.get("BAC_ESSAI_APPLIS", tmp_path / "applis")),
                catalogue=RACINE / "applis.yaml", garde=RACINE / "garde", lanceurs=RACINE / "lanceurs",
                python=os.environ.get("BAC_ESSAI_PYTHON", sys.executable), attente_connexion=False,
                relais=False, annuaire=False, port_annuaire=port_libre(),
                navigateurs=os.environ.get("BAC_ESSAI_NAVIGATEURS", "/ms-playwright"))
    base.update(kw)
    return Config(**base)


@pytest.fixture()
def client(tmp_path, request):
    main.ETAT.clear()
    # les essais de bout en bout ont le faux annuaire de l'Anneau (port libre) ; ceux de l'API non
    main.ETAT["cfg"] = config(tmp_path, annuaire=bool(getattr(request.module, "ANNUAIRE", False)))
    with TestClient(main.app) as c:
        r = c.post("/api/connexion", json={"mot_de_passe": MOT_DE_PASSE})
        assert r.status_code == 200
        yield c
    main.ETAT.clear()
