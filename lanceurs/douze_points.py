"""Lanceur de Douze points dans le Bac à sable (le dépôt n'a pas de serveur de démonstration).

Usage : python lanceurs/douze_points.py <dossier> <port>   (lancé dans le code source de Douze points)
- mot de passe : BAS_MOT_DE_PASSE (le relais s'en sert pour se connecter seul) ;
- 0.4.0 : carnet simulé, à l'adresse DOUZE_POINTS_CARNET_URL (lien branché, http://127.0.0.1:<port local de carnet>)
  avec le jeton commun simulé MAISON_JETON : les invités sont choisis dans carnet simulé, et la clôture y envoie la
  soirée. Variable absente : le lanceur s'arrête (jamais de repli sur l'adresse de la vraie stack) ;
- 0.4.0 : adresse des invités (lien et QR code) prise dans le faux annuaire de l'Anneau (MAISON_ANNEAU_URL), comme
  dans la vraie maison ;
- 0.1.3 : un faux Immich (celui des tests de Douze points), pour que l'icône 📷 et « Immortaliser » paraissent ;
  les photos y arrivent et le journal note « Douze points aurait écrit chez immich.bac-a-sable » (le faux Immich
  commun aux applis simulées viendra en 0.4.1) ;
- la soirée elle-même est montée ensuite par le Bac à sable, par l'API de l'appli (app/douze.py).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import uvicorn

sys.path.insert(0, os.getcwd())

from app import immich, main  # noqa: E402  (le code de Douze points, répertoire courant)
from app.config import Config  # noqa: E402


FAUX_IMMICH_URL = "http://immich.bac-a-sable"
FAUX_IMMICH_CLE = "cle-de-test"          # la clé qu'attend le faux Immich des tests de Douze points


def lien(variable: str) -> str:
    """0.4.0 (conseil) : une variable de lien manquante fait échouer le lanceur, sans repli sur la vraie stack."""
    valeur = os.environ.get(variable, "").strip().rstrip("/")
    if not valeur.startswith("http://127.0.0.1:"):
        raise SystemExit(f"Bac à sable : {variable} manque ou ne vise pas 127.0.0.1 : Douze points ne démarre pas.")
    return valeur


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
    main.ETAT["cfg"] = Config(password=os.environ["BAS_MOT_DE_PASSE"], data=dossier,
                              static=Path(main.__file__).parent / "static", attente_connexion=False,
                              limite_invite=100000, carnet_url=lien("DOUZE_POINTS_CARNET_URL"),
                              carnet_jeton=os.environ["MAISON_JETON"],
                              immich_url=FAUX_IMMICH_URL, immich_cle=FAUX_IMMICH_CLE)
    # 0.1.3 : Immich est simulé (aucun appel ne quitte le processus : httpx.MockTransport, noté par la garde)
    immich.CLIENT = httpx.Client(transport=httpx.MockTransport(faux_immich()))
    main.LIRE_ANNEAU = lambda adresse_, jeton: {"dates": []}      # pas de sauvegarde simulée dans l'Anneau
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    lancer(Path(sys.argv[1]), int(sys.argv[2]))
