"""Lanceur de carnet dans le Bac à sable.

Usage : python lanceurs/carnet.py <dossier> <port>   (lancé dans le code source de carnet)

Avec un scénario (BAS_SCENARIO) : les personnes du scénario deviennent les fiches du faux iCloud (nom, téléphone,
courriel, naissance, liens de famille en « personnes liées » comme sur l'iPhone) ; la moitié environ a son double
dans le faux Immich, écrit un peu autrement (majuscules, accents), pour que carnet propose des liens à vérifier.
Sans scénario (0.4.0, « plus de données de démo ») : carnet simulé démarre sans aucune fiche.

0.4.0 : le jeton commun simulé (MAISON_JETON, tiré par le Bac à sable) ouvre les portes des autres applis simulées
branchées : Douze points lit /douze-points/personnes et envoie ses soirées sur /evenements/…, la Gazette lit
/gazette/personnes et écrit ses parutions. Les fiches portent l'identifiant « BAS-<id de la personne du Bac à sable> »
(le carnet_id que voient les autres applis). Sillage, Millésime et le kit sont encore en démo : leurs liens avec
carnet restent coupés (Sillage n'est pas lu, Millésime et Immich restent les faux des tests).

Tout passe par les faux services des tests de carnet (MockTransport) : rien ne sort.
"""
from __future__ import annotations

import json
import os
import random
import sys
import threading
from pathlib import Path

import uvicorn

sys.path.insert(0, os.getcwd())

from app import coffre, icloud, liaisons, main  # noqa: E402  (le code de carnet, répertoire courant)
from app.carnet import Carnet  # noqa: E402
from tests.faux_icloud import FauxICloud  # noqa: E402
from tests.faux_services import FauxImmich, FauxTreemich  # noqa: E402
from tests.interface import serveur as demo  # noqa: E402
from tests.test_carnet import _config, carte_simple  # noqa: E402

ETIQUETTES = {"frere": "_$!<Brother>!$_", "soeur": "_$!<Sister>!$_", "conjoint": "_$!<Spouse>!$_",
              "parent": "_$!<Parent>!$_", "enfant": "_$!<Child>!$_", "ami": "_$!<Friend>!$_"}


def _nom(p: dict) -> str:
    return " ".join(x for x in (p.get("prenom", ""), p.get("nom", "")) if x).strip() or "Sans nom"


def _bday(naissance: str) -> str:
    if not naissance:
        return ""
    if naissance.startswith("--"):
        return f"BDAY;X-APPLE-OMIT-YEAR=1604:1604-{naissance[2:]}\r\n"
    if len(naissance) == 4:
        return ""            # année seule : l'iPhone ne sait pas l'écrire, elle n'entre pas dans la fiche
    return f"BDAY:{naissance}\r\n"


def fiches(personnes: list[dict]) -> str:
    par_id = {p["id"]: p for p in personnes}
    vcf = ""
    for p in personnes:
        extra = ""
        if p.get("telephone"):
            extra += f"TEL;type=CELL:{p['telephone']}\r\n"
        if p.get("courriel"):
            extra += f"EMAIL;type=HOME:{p['courriel']}\r\n"
        extra += _bday(p.get("naissance", ""))
        if p.get("ville"):
            extra += f"ADR;type=HOME:;;;{p['ville']};;;France\r\n"
        for i, lien in enumerate(p.get("liens") or [], start=1):
            autre = par_id.get(lien.get("vers"))
            if autre and lien.get("relation") in ETIQUETTES:
                extra += (f"item{i}.X-ABRELATEDNAMES:{_nom(autre)}\r\n"
                          f"item{i}.X-ABLabel:{ETIQUETTES[lien['relation']]}\r\n")
        if p.get("note"):
            extra += f"NOTE:Bac à sable — {p['note']}\r\n"
        vcf += carte_simple(f"BAS-{p['id']:05d}", _nom(p), extra)
    return vcf


def doubles_immich(personnes: list[dict], graine: int = 7) -> list[dict]:
    """Un double dans Immich pour une personne sur deux, écrit comme Immich l'aurait appris (« Prénom NOM »)."""
    rng = random.Random(graine)
    res = []
    for p in personnes:
        if rng.random() < 0.5 or not p.get("prenom"):
            continue
        nom = f"{p['prenom']} {p.get('nom', '').upper()}".strip() if rng.random() < 0.5 else _nom(p)
        naissance = p.get("naissance", "")
        res.append({"id": f"im-bas-{p['id']}", "name": nom, "isHidden": False,
                    "birthDate": naissance if len(naissance) == 10 else None})
    return res


def preparer(dossier: Path, scenario: dict) -> Carnet:
    personnes = scenario.get("personnes_detail") or []
    ic = FauxICloud(fiches(personnes))
    immich = FauxImmich()
    immich.personnes = doubles_immich(personnes)
    immich.photos = {x["id"]: [f"{x['id']}-a", f"{x['id']}-b"] for x in immich.personnes}
    services = {"icloud": ic, "immich": immich, "treemich": FauxTreemich(),
                "synology": FauxICloud("", utilisateur="carnet", mot_de_passe="syno")}
    cfg = _config(dossier, password=os.environ["BAS_MOT_DE_PASSE"], static=Path(main.__file__).parent / "static",
                  millesime_jeton="demo")
    c = Carnet(cfg, {k: v.transport() for k, v in services.items()} | {"millesime": demo.faux_millesime()})
    c.treemich().facteur_attente = 0
    with c.ecriture():
        icloud.relire(c, "Bac à sable")
    liaisons.donnees(c)
    c.transports["logos"] = demo.faux_logos()
    main.LIRE_ANNEAU = demo.faux_anneau()
    return c


if __name__ == "__main__":
    dossier, port = Path(sys.argv[1]), int(sys.argv[2])
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = Path(os.environ.get("BAS_SCENARIO", ""))
    scenario = json.loads(chemin.read_text(encoding="utf-8")) if chemin.is_file() else None
    carnet = preparer(dossier, scenario or {"personnes_detail": []})
    # 0.4.0 : Sillage est encore en démo (lien coupé) : carnet ne le lit pas
    coffre.LIRE_SILLAGE = lambda c, immich_id: None
    main.ETAT["carnet"] = carnet
    threading.excepthook = lambda a: None
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning")
