"""0.4.0 — « la maison branchée » : les liens entre applis simulées.

La table `liens:` d'applis.yaml recopie les flux du coffre entre applis maison (copie figée : docs/flux-maison.json).
Un lien est **branché** quand ses deux bouts sont des applis branchées (lanceur « bac » : elles prennent leurs données
dans le scénario et chez les autres applis simulées) et qu'il passe par une adresse http. Sinon il est **coupé**, avec
son motif : une appli « encore en démo » (pour ne pas mêler démo et scénario), un flux hors du Bac à sable (tuiles,
cookie commun, sauvegarde de nuit de l'Anneau), un fichier, un geste fait à la main.

Pour chaque lien branché, l'appli appelante reçoit sa variable d'adresse de la vraie stack, pointée vers le port local
de l'autre appli (`http://127.0.0.1:<port + 1000>`), et sa garde ne laisse passer que ces ports-là (plus le faux
annuaire de l'Anneau). Ouvrir une appli démarre d'abord celles qu'elle appelle (lecture ou écriture), sans boucle ;
toucher une appli touche aussi celles-là.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import yaml

PORTEES = ("simule", "annuaire", "hors", "main")
MOTIFS = {"hors": "hors du Bac à sable (tuiles, cookie commun ou sauvegarde de nuit de l'Anneau)",
          "main": "fait à la main dans la vraie maison",
          "annuaire": "simulé par le faux annuaire de l'Anneau (toutes les applis le reçoivent)"}


@dataclass(frozen=True)
class Lien:
    de: str
    vers: str
    nature: str
    appelant: str = ""
    variable: str = ""
    portee: str = "simule"
    moyen: str = ""

    @property
    def cible(self) -> str:
        """L'appli jointe par l'appelant (l'autre bout du flux)."""
        return self.vers if self.appelant == self.de else self.de


def charger(chemin: Path) -> list[Lien]:
    brut = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
    res = []
    for x in brut.get("liens") or []:
        lien = Lien(de=str(x["de"]), vers=str(x["vers"]), nature=str(x.get("nature", "donnees")),
                    appelant=str(x.get("appelant", "") or ""), variable=str(x.get("variable", "") or ""),
                    portee=str(x.get("portee", "simule") or "simule"), moyen=str(x.get("moyen", "") or ""))
        if lien.portee not in PORTEES:
            raise ValueError(f"portée inconnue pour {lien.de} → {lien.vers} : {lien.portee}")
        if lien.portee == "simule" and lien.appelant not in (lien.de, lien.vers):
            raise ValueError(f"{lien.de} → {lien.vers} : l'appelant doit être l'un des deux bouts")
        res.append(lien)
    return res


class Liens:
    """Les liens, vus depuis le catalogue des applis (`applis` : {id: Appli})."""

    def __init__(self, liens: list[Lien], applis: dict):
        self.tous = liens
        self.applis = applis

    def branchee(self, ident: str) -> bool:
        a = self.applis.get(ident)
        return bool(a and a.lanceur == "bac")

    def motif(self, lien: Lien) -> str:
        """Vide : branché. Sinon pourquoi le lien est coupé."""
        if lien.portee != "simule":
            return MOTIFS[lien.portee]
        for bout in (lien.de, lien.vers):
            if bout not in self.applis:
                return f"{bout} n'est pas embarquée"
        demo = [self.applis[b].nom for b in (lien.de, lien.vers) if not self.branchee(b)]
        if demo:
            return " et ".join(demo) + " encore en démo"
        if lien.moyen:
            return f"passe par un {lien.moyen}, pas simulé en 0.4.0"
        if not lien.variable:
            return "pas de variable d'adresse connue"
        return ""

    def branches(self) -> list[Lien]:
        return [x for x in self.tous if not self.motif(x)]

    def cibles(self, ident: str) -> list[str]:
        """Les applis qu'`ident` appelle directement (lit ou écrit) par un lien branché."""
        return list(dict.fromkeys(x.cible for x in self.branches() if x.appelant == ident))

    def cascade(self, ident: str) -> list[str]:
        """Toutes les applis à démarrer pour `ident` (elle exclue), les plus profondes d'abord. Les liens vont dans
        les deux sens (carnet ↔ Douze points) : on garde la liste des applis déjà vues, aucune boucle."""
        ordre: list[str] = []
        vues = {ident}

        def visiter(x: str) -> None:
            for c in self.cibles(x):
                if c in vues:
                    continue
                vues.add(c)
                visiter(c)
                ordre.append(c)
        visiter(ident)
        return ordre

    def variables(self, ident: str) -> dict[str, str]:
        """Les variables d'adresse d'`ident` : {VARIABLE: http://127.0.0.1:<port local de l'autre>}."""
        res: dict[str, str] = {}
        for x in self.branches():
            if x.appelant == ident:
                res[x.variable] = f"http://127.0.0.1:{self.applis[x.cible].port_local}"
        return res

    def ports(self, ident: str) -> list[int]:
        """Les ports locaux qu'`ident` a le droit de joindre (ceux des applis qu'elle appelle)."""
        return sorted({self.applis[c].port_local for c in self.cibles(ident)})

    def etat(self) -> list[dict]:
        res = []
        for x in self.tous:
            m = self.motif(x)
            res.append({"de": x.de, "vers": x.vers, "nature": x.nature, "appelant": x.appelant, "variable": x.variable,
                        "portee": x.portee, "branche": not m, "motif": m})
        return res


def flux_figes(chemin: Path) -> list[dict]:
    return list((json.loads(chemin.read_text(encoding="utf-8")) or {}).get("flux") or [])


def comparer(liens: list[Lien], flux: list[dict], applis: dict) -> dict:
    """La table `liens:` face à la copie figée des flux du coffre (identifiants du coffre = noms des dépôts).
    Rend les flux sans ligne dans la table, et les lignes sans flux."""
    vers_id = {a.depot: ident for ident, a in applis.items()}
    attendus = {(vers_id.get(f["de"], f["de"]), vers_id.get(f["vers"], f["vers"]), f["nature"]) for f in flux}
    presents = {(x.de, x.vers, x.nature) for x in liens}
    return {"manquants": sorted(attendus - presents), "en_trop": sorted(presents - attendus)}
