"""Lanceur de la Gazette dans le Bac à sable (0.4.0, « la maison branchée »).

Usage : python lanceurs/gazette.py <dossier> <port>   (lancé dans le code source de la Gazette)

Avant (0.3.x) : la démonstration du dépôt (tools/demo.py), dont le faux Douze points (`DS.exemple()`) donnait les
« Pays 6, Pays 12 » de la capture de Julien. Elle n'est plus lancée. Désormais :
- **fiches** : lues dans carnet simulé (GAZETTE_CARNET_URL, jeton commun simulé MAISON_JETON), et **seulement les
  personnes inventées du scénario** (arbitrage de Julien du 20/11/2026) : les copies de vraies fiches restent dans carnet
  et Douze points simulés, ce lanceur les écarte. Règle « liste blanche » : une fiche passe si son identifiant de carnet
  est celui d'une personne inventée (ou piège) du scénario (« BAS-<id> », écrit par lanceurs/carnet.py) ; tout le reste,
  dont une fiche inconnue, est écarté. La fiche complète, les parutions et les « journaux » ne sont demandés ou écrits
  que pour ces personnes-là ;
- **soirées** : lues dans Douze points simulé (GAZETTE_DOUZE_POINTS_URL, routes /externe/soirees… de Douze points ≥ 1.9),
  le journal de chaque soirée filtré de la même façon : un invité qui n'est pas une personne inventée du scénario
  disparaît du journal (invités, notes, commentaires, palmarès, duos, flair) avant que la Gazette ne le lise ;
- variable de lien absente : le lanceur s'arrête (jamais de repli sur l'adresse de la vraie stack, http://carnet:8096) ;
- Sillage est encore en démo : lien coupé (pas d'adresse de Sillage) ;
- les autres faux services restent sans réseau : Immich et Ollama minimaux écrits ici (aucune donnée de démo : ni
  personne, ni album), sources Wikipédia et Larousse gardées des fixtures du dépôt (sources_actives faux), l'Anneau
  sans sauvegarde, la porte Home Assistant fermée ;
- **Chromium** (rendu PDF) : la Gazette coupe déjà tout le réseau des pages qu'elle imprime (page.route, data: et about:
  seulement). Le Bac à sable ajoute deux réglages au lancement de Chromium : un proxy mort (127.0.0.1:9) et
  `--proxy-bypass-list=<-loopback>`, qui retire l'exception implicite de Chromium pour la machine elle-même. Chromium
  ne peut donc joindre aucun port local, même ceux des autres applis simulées, alors que la garde Python ne le voit pas
  (ce n'est pas du Python).
"""
from __future__ import annotations

import base64
import copy
import json
import os
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, os.getcwd())

ARGS_CHROMIUM = ["--proxy-server=http://127.0.0.1:9", "--proxy-bypass-list=<-loopback>"]
ORIGINES_PERMISES = ("inventee", "piege")


# ------------------------------------------------------------------ liste blanche (testée sans la Gazette)

def lien(variable: str) -> str:
    """Une variable de lien manquante fait échouer le lanceur, sans repli sur l'adresse de la vraie stack."""
    valeur = os.environ.get(variable, "").strip().rstrip("/")
    if not valeur.startswith("http://127.0.0.1:"):
        raise SystemExit(f"Bac à sable : {variable} manque ou ne vise pas 127.0.0.1 : la Gazette ne démarre pas.")
    return valeur


def permis_du_scenario(scenario: dict | None) -> set[str]:
    """Les identifiants de carnet simulé des personnes inventées (et pièges) du scénario. Copies de vraies fiches :
    jamais."""
    res = set()
    for p in (scenario or {}).get("personnes_detail") or []:
        if p.get("origine") in ORIGINES_PERMISES and p.get("id") is not None:
            res.add(f"BAS-{int(p['id']):05d}")
    return res


def filtrer_personnes(liste: list[dict], permis: set[str]) -> list[dict]:
    return [p for p in liste or [] if str(p.get("carnet_id") or "") in permis]


def filtrer_journal(journal: dict, permis: set[str]) -> dict:
    """Le journal d'une soirée de Douze points sans les invités hors liste blanche (ni leurs notes, commentaires,
    places au palmarès, duos ni flair). Les totaux calculés par Douze points ne nomment personne : ils restent."""
    if not isinstance(journal, dict):
        return journal
    j = copy.deepcopy(journal)
    invites = j.get("invites") or []
    gardes = {i.get("id") for i in invites if str(i.get("carnet_id") or "") in permis}
    j["invites"] = [i for i in invites if i.get("id") in gardes]
    for c in j.get("chansons") or []:
        c["notes"] = [n for n in c.get("notes") or [] if n.get("invite") in gardes]
    j["palmares"] = [x for x in j.get("palmares") or [] if x.get("invite") in gardes]
    if j.get("plus_proche") not in gardes:
        j["plus_proche"] = next((x["invite"] for x in j["palmares"] if x.get("complet")), None)
    j["commentaires"] = [x for x in j.get("commentaires") or [] if x.get("invite") in gardes]
    j["duos"] = [d for d in j.get("duos") or [] if all(i in gardes for i in d.get("invites") or [])]
    if isinstance(j.get("demi"), dict):
        j["demi"]["flair"] = [x for x in j["demi"].get("flair") or [] if x.get("invite") in gardes]
    j["bac_a_sable"] = {"invites_ecartes": len(invites) - len(gardes)}
    return j


# ------------------------------------------------------------------ faux services restants (sans réseau)

GRIS = base64.b64decode("/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAx"
                        "NDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAI"
                        "AQEAAD8AKp//2Q==")


def immich_simule(methode: str, chemin: str, corps: dict | None = None):
    """Immich minimal : aucune personne, aucun album, aucune photo trouvée ; une image grise pour un aperçu demandé
    (les photos des duos de Douze points arriveront par le faux Immich commun, en 0.4.1)."""
    if chemin == "/tags" or chemin.startswith("/albums"):
        return []
    if chemin == "/search/metadata":
        return {"assets": {"items": [], "nextPage": None}}
    if chemin.startswith("/assets/") and "/thumbnail" not in chemin and "/original" not in chemin:
        return {"people": []}
    if chemin.startswith("/people"):
        return {"people": []} if methode == "GET" else {}
    return GRIS


def ollama_simule(chemin: str, corps: dict | None):
    """L'IA du PC simulée : des titres neutres, sans personne de démonstration."""
    if corps is None:
        return {"models": [{"name": "simule:bac-a-sable"}]}
    return {"response": "1. Titre simulé un\n2. Titre simulé deux\n3. Titre simulé trois\n4. Titre simulé quatre\n"
                        "5. Titre simulé cinq"}


def anneau_simule(adresse: str, jeton: str) -> dict:
    return {"dates": []}


# ------------------------------------------------------------------ Chromium

def restreindre_chromium() -> bool:
    """Ajoute le proxy mort et la fin de l'exception « machine locale » à chaque lancement de Chromium par la Gazette."""
    try:
        from playwright.sync_api._generated import BrowserType
    except Exception:  # noqa: BLE001 — Playwright absent : pas de rendu PDF, rien à restreindre
        return False
    if getattr(BrowserType.launch, "_bac", False):
        return True
    origine = BrowserType.launch

    def launch(self, *args, **kw):
        kw["args"] = [*(kw.get("args") or []), *ARGS_CHROMIUM]
        return origine(self, *args, **kw)

    launch._bac = True
    BrowserType.launch = launch
    return True


# ------------------------------------------------------------------ lancement

def configurer(dossier: Path, scenario: dict | None) -> None:
    from app import carnet as carnet_mod  # noqa: E402  (le code de la Gazette, répertoire courant)
    from app import douze_points as DP  # noqa: E402
    from app import main  # noqa: E402
    from app.base import Base  # noqa: E402
    from app.config import Config  # noqa: E402

    permis = permis_du_scenario(scenario)
    personnes_permises: set[str] = set()          # personne_id (identifiant maison) des fiches gardées

    def lire_carnet(url: str, jeton: str) -> list[dict]:
        liste = filtrer_personnes(carnet_mod._lire_http(url, jeton), permis)
        personnes_permises.clear()
        personnes_permises.update(str(p.get("personne_id") or "") for p in liste if p.get("personne_id"))
        return liste

    def fiche(url: str, jeton: str, methode: str, chemin: str, corps: dict | None):
        morceaux = chemin.strip("/").split("/")
        if len(morceaux) < 3 or morceaux[2] not in personnes_permises:
            return 404, {"detail": "carnet ne trouve pas cette personne (Bac à sable : personne hors du scénario)"}
        return carnet_mod._fiche_http(url, jeton, methode, chemin, corps)

    def ecrire(url: str, jeton: str, personne_id: str, texte: str) -> None:
        if personne_id in personnes_permises:
            carnet_mod._ecrire_http(url, jeton, personne_id, texte)

    def paru(url: str, jeton: str, personne_id: str, cle: str, corps: dict) -> None:
        if personne_id in personnes_permises:
            carnet_mod._paru_http(url, jeton, personne_id, cle, corps)

    def lire_douze(url: str, jeton: str, chemin: str):
        d = DP._lire_http(url, jeton, chemin)
        if "/journal" in chemin and "/image/" not in chemin:
            return filtrer_journal(d, permis)
        return d

    try:   # sources gardées des fixtures du dépôt (Wikipédia, Larousse) : la Gazette ne va jamais les lire
        from tools import demo  # noqa: E402
        b = Base(dossier / "gazette.db")
        for cle, contenu in demo.SOURCES.items():
            b.garder_source(cle, contenu)
        for titre, n in demo.NOTORIETE:
            b.garder_source(f"wd:fr:{titre}", f'{{"n": {n}, "humain": true}}')
        b.fermer()
    except Exception:  # noqa: BLE001 — sans ces sources, les livrets sont seulement plus courts
        pass

    main.ETAT.clear()
    main.ETAT["carnet_lire"] = lire_carnet
    main.ETAT["carnet_fiche"] = fiche
    main.ETAT["carnet_ecrire"] = ecrire
    main.ETAT["carnet_paru"] = paru
    main.ETAT["douze_lire"] = lire_douze
    main.ETAT["immich_lire"] = immich_simule
    main.ETAT["ollama_lire"] = ollama_simule
    main.ETAT["anneau_lire"] = anneau_simule
    main.ETAT["cfg"] = Config(password=os.environ["BAS_MOT_DE_PASSE"], data=dossier,
                              static=Path(main.__file__).parent / "static", attente_connexion=False,
                              carnet_url=lien("GAZETTE_CARNET_URL"), carnet_jeton=os.environ["MAISON_JETON"],
                              douze_points_url=lien("GAZETTE_DOUZE_POINTS_URL"), sillage_url="",
                              immich_url="http://immich.bac-a-sable", immich_cle="cle-bac-a-sable",
                              ollama_url="http://ollama.bac-a-sable", sources_actives=False, jeton_ha="")


if __name__ == "__main__":
    dossier, port = Path(sys.argv[1]), int(sys.argv[2])
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = Path(os.environ.get("BAS_SCENARIO", ""))
    scenario = json.loads(chemin.read_text(encoding="utf-8")) if chemin.is_file() else None
    restreindre_chromium()
    configurer(dossier, scenario)
    from app import main  # noqa: E402
    uvicorn.run(main.app, host="127.0.0.1", port=port, log_level="warning")
