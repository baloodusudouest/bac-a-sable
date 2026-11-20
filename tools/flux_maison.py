"""Copie figée des flux entre applis maison (0.4.0), pour le test qui la compare à la table `liens:` d'applis.yaml.

Usage : python tools/flux_maison.py <carte.json>
La carte est fabriquée hors d'ici, depuis le coffre privé (`.github/scripts/carte.py` du coffre). On n'en garde que
les flux dont les deux bouts sont des applis embarquées (identifiants du coffre = noms des dépôts), et pour chacun
seulement `de`, `vers` et `nature` : aucune adresse, aucun jeton, aucun texte libre (ce dépôt est public).
Le Bac à sable ne lit jamais le coffre quand il tourne.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent


def extraire(carte: dict, depots: set[str]) -> list[dict]:
    vus, res = set(), []
    for f in carte.get("flux") or []:
        de, vers, nature = str(f.get("de", "")), str(f.get("vers", "")), str(f.get("nature", ""))
        if de in depots and vers in depots and (de, vers, nature) not in vus:
            vus.add((de, vers, nature))
            res.append({"de": de, "vers": vers, "nature": nature})
    return sorted(res, key=lambda x: (x["de"], x["vers"], x["nature"]))


if __name__ == "__main__":
    carte = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    applis = yaml.safe_load((RACINE / "applis.yaml").read_text(encoding="utf-8"))["applis"]
    depots = {a["depot"] for a in applis.values()}
    flux = extraire(carte, depots)
    sortie = {"source": "carte de la maison (coffre), flux entre applis maison", "commit_coffre": str(carte.get("commit", ""))[:7],
              "tire_le": str(carte.get("genere_le", ""))[:10], "flux": flux}
    (RACINE / "docs" / "flux-maison.json").write_text(json.dumps(sortie, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(flux)} flux entre applis maison → docs/flux-maison.json")
