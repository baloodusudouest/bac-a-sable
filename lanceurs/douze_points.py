"""Lanceur de Douze points dans le Bac à sable (le dépôt n'a pas de serveur de démonstration).

Usage : python lanceurs/douze_points.py <dossier> <port>   (lancé dans le code source de Douze points)
- mot de passe : BAS_MOT_DE_PASSE (le relais s'en sert pour se connecter seul) ;
- adresse des invités : BAS_ADRESSE (le port du relais vu par le navigateur), pour le lien et le QR code ;
- aucune adresse de carnet : l'envoi de la soirée vers carnet tourne à vide ;
- 0.1.3 : un faux Immich (celui des tests de Douze points), pour que l'icône 📷 et « Immortaliser » paraissent ;
  les photos y arrivent et le journal note « Douze points aurait écrit chez immich.bac-a-sable » ;
- la soirée elle-même est montée ensuite par le Bac à sable, par l'API de l'appli (app/douze.py).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import uvicorn

sys.path.insert(0, os.getcwd())

from app import immich, maison, main  # noqa: E402  (le code de Douze points, répertoire courant)
from app.config import Config  # noqa: E402


FAUX_IMMICH_URL = "http://immich.bac-a-sable"
FAUX_IMMICH_CLE = "cle-de-test"          # la clé qu'attend le faux Immich des tests de Douze points


def faux_immich():
    """Le faux Immich des tests de Douze points (1.6.0 et plus) ; s'il manque, un faux minimal qui accepte tout."""
    try:
        from tests.test_photos_16 import FauxImmich  # noqa: E402
        return FauxImmich()
    except ImportError:
        compte = {"n": 0}

        def repondre(req: httpx.Request) -> httpx.Response:
            compte["n"] += 1
            if req.url.path.endswith("/server/about") or req.url.path.endswith("/api-keys/me"):
                return httpx.Response(200, json={"version": "simulé", "permissions": ["all"]})
            return httpx.Response(200 if req.method != "POST" else 201,
                                  json={"id": f"faux-{compte['n']}", "status": "created"})
        return repondre


def lancer(dossier: Path, port: int) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    adresse = os.environ.get("BAS_ADRESSE", "").rstrip("/")
    main.ETAT["cfg"] = Config(password=os.environ["BAS_MOT_DE_PASSE"], data=dossier,
                              static=Path(main.__file__).parent / "static", attente_connexion=False,
                              limite_invite=100000, carnet_url="", carnet_jeton="",
                              immich_url=FAUX_IMMICH_URL, immich_cle=FAUX_IMMICH_CLE)
    # 0.1.3 : Immich est simulé (aucun appel ne quitte le processus : httpx.MockTransport, noté par la garde)
    immich.CLIENT = httpx.Client(transport=httpx.MockTransport(faux_immich()))
    # L'annuaire de l'Anneau est simulé : la tuile « Douze points » a pour adresse locale celle du relais.
    main.ANNUAIRE = maison.Annuaire(url="http://anneau.bac-a-sable", jeton="bac-a-sable",
                                    lire=lambda: [{"nom": "Douze points", "locale": adresse}] if adresse else [])
    main.LIRE_ANNEAU = lambda adresse_, jeton: {"dates": []}
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    lancer(Path(sys.argv[1]), int(sys.argv[2]))
