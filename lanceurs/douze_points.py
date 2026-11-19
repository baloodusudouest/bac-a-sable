"""Lanceur de Douze points dans le Bac à sable (le dépôt n'a pas de serveur de démonstration).

Usage : python lanceurs/douze_points.py <dossier> <port>   (lancé dans le code source de Douze points)
- mot de passe : BAS_MOT_DE_PASSE (le relais s'en sert pour se connecter seul) ;
- adresse des invités : BAS_ADRESSE (le port du relais vu par le navigateur), pour le lien et le QR code ;
- aucune adresse de carnet ni d'Immich : les boucles d'envoi tournent à vide ;
- la soirée elle-même est montée ensuite par le Bac à sable, par l'API de l'appli (app/douze.py).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, os.getcwd())

from app import maison, main  # noqa: E402  (le code de Douze points, répertoire courant)
from app.config import Config  # noqa: E402


def lancer(dossier: Path, port: int) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    adresse = os.environ.get("BAS_ADRESSE", "").rstrip("/")
    main.ETAT["cfg"] = Config(password=os.environ["BAS_MOT_DE_PASSE"], data=dossier,
                              static=Path(main.__file__).parent / "static", attente_connexion=False,
                              limite_invite=100000, carnet_url="", carnet_jeton="", immich_url="", immich_cle="")
    # L'annuaire de l'Anneau est simulé : la tuile « Douze points » a pour adresse locale celle du relais.
    main.ANNUAIRE = maison.Annuaire(url="http://anneau.bac-a-sable", jeton="bac-a-sable",
                                    lire=lambda: [{"nom": "Douze points", "locale": adresse}] if adresse else [])
    main.LIRE_ANNEAU = lambda adresse_, jeton: {"dates": []}
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    lancer(Path(sys.argv[1]), int(sys.argv[2]))
