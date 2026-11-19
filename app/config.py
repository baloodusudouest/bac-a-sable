"""Réglages lus dans l'environnement du conteneur. Aucune valeur personnelle dans le code.

Le Bac à sable ne reçoit aucune adresse ni clé de service de la maison, sauf deux choses, toutes deux facultatives :
l'adresse de carnet et le jeton commun, pour copier de vraies fiches (lecture seule, depuis ce processus seulement,
jamais transmises aux applis simulées).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from . import maison

APPLI = "bac-a-sable"
NOM = "Bac à sable"


@dataclass(frozen=True)
class Config:
    password: str
    data: Path
    static: Path
    applis: Path = Path("/applis")              # code, site-packages et interfaces des applis embarquées
    catalogue: Path = Path("/app/applis.yaml")  # la liste des applis embarquées
    garde: Path = Path("/app/garde")            # sitecustomize chargé dans chaque appli simulée
    lanceurs: Path = Path("/app/lanceurs")      # lanceurs écrits ici (carnet, Douze points)
    python: str = "/usr/local/bin/python"
    carnet_url: str = ""                        # vide : pas de copie de vraies fiches
    carnet_jeton: str = ""
    attente_connexion: bool = True              # délai anti-essais ; coupé dans les tests
    arret_minutes: int = 30                     # une appli sans requête depuis ce délai est arrêtée
    max_simultanees: int = 4                    # applis lancées en même temps, au plus
    duree_copies_jours: int = 30                # copies de vraies fiches effacées après ce délai, sauf épinglées
    autotest: bool = True                       # coupé dans les tests (pas de réseau)
    relais: bool = True                         # écouter sur les ports des applis ; coupé dans les tests d'API
    hotes_autotest: tuple = field(default=())   # adresses à essayer en plus (le NAS, Immich, HA…)


def charger() -> Config:
    mot_de_passe = maison.mot_de_passe()
    if len(mot_de_passe) < 12:
        raise SystemExit("MAISON_PASSWORD est absent ou trop court (12 caractères au moins) : "
                         "le Bac à sable ne démarre pas.")
    racine = Path(__file__).resolve().parent.parent
    hotes = tuple(h.strip() for h in os.environ.get("BAC_AUTOTEST", "").split(",") if h.strip())
    return Config(
        password=mot_de_passe,
        data=Path(os.environ.get("BAC_DATA", "/data")),
        static=Path(__file__).parent / "static",
        applis=Path(os.environ.get("BAC_APPLIS", "/applis")),
        catalogue=racine / "applis.yaml",
        garde=racine / "garde",
        lanceurs=racine / "lanceurs",
        carnet_url=os.environ.get("BAC_CARNET_URL", "").strip().rstrip("/"),
        carnet_jeton=maison.jeton_a_envoyer(),
        arret_minutes=int(os.environ.get("BAC_ARRET_MINUTES", "30") or 30),
        max_simultanees=int(os.environ.get("BAC_MAX_SIMULTANEES", "4") or 4),
        hotes_autotest=hotes,
    )
