"""Bac à sable : les vraies applis maison, lancées à la demande sur une fausse maison, pour les essayer sans rien
écrire chez les vrais services.

Routes : /health (publique), /api/session, /api/connexion, /api/deconnexion,
/api/applis (état, démarrer, arrêter, vider), /api/personnes (inventer, pièges, copier depuis carnet, épingler,
effacer), /api/scenarios (créer, jouer, effacer), /api/douze (soirée simulée, téléphones), /api/journal,
/api/autotest, /api/reglages, /api/synthese, /externe/sauvegarde (jeton commun, pour l'Anneau), puis l'interface.
Les applis simulées sont servies par le relais, chacune sur son port (app/relais.py).
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import platform
import time
from contextlib import asynccontextmanager
from datetime import datetime
from importlib.metadata import version as version_paquet
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from . import __version__, autotest, base, douze, maison, personnes
from .auth import COMMUN, DUREE, Sessions, en_https
from .config import APPLI, Config, charger
from .processus import Gestionnaire, catalogue
from .relais import Relais, servir

ETAT: dict = {}
PUBLIQUES = ("/api/connexion", "/api/session")
journal = logging.getLogger("bac-a-sable")

REGLAGES_DEFAUTS = {
    "douze_tempo": 4.0,          # secondes entre deux notes d'un téléphone simulé
    "douze_telephones": 6,       # téléphones simulés par défaut (les autres prénoms restent aux vrais iPhone)
    "douze_chansons": 12,
}
REGLAGES_VARIABLES: dict[str, str] = {}
EXCLUS_SAUVEGARDE: tuple[str, ...] = ()


def cfg() -> Config:
    return ETAT["cfg"]


def g() -> Gestionnaire:
    return ETAT["gestionnaire"]


def _lire_generation(c: Config) -> int:
    try:
        return int((c.data / "session_generation").read_text().strip())
    except (OSError, ValueError):
        return 0


async def _purger_copies() -> None:
    """Chaque heure : les copies de vraies fiches de plus de 30 jours (ni épinglées, ni dans un scénario épinglé)
    sont effacées pour de bon."""
    while True:
        try:
            with base.base(cfg().data) as cx:
                vieilles = base.copies_perimees(cx, cfg().duree_copies_jours)
                if vieilles:
                    base.effacer_personnes(cx, vieilles)
            if vieilles:
                base.compacter(cfg().data)
                journal.warning("%d copie(s) de vraies fiches effacée(s) (plus de %d jours)", len(vieilles),
                                cfg().duree_copies_jours)
        except Exception:  # noqa: BLE001 — la purge ne doit jamais arrêter l'appli
            journal.exception("purge des copies")
        await asyncio.sleep(3600)


def _faire_autotest() -> dict:
    resultat = autotest.lancer(cfg()) if cfg().autotest else {
        "ok": True, "le": base.maintenant(), "message": "Autotest coupé (essais).", "essais": []}
    ETAT["autotest"] = resultat
    g().bloque = "" if resultat["ok"] else resultat["message"]
    return resultat


@asynccontextmanager
async def cycle(app: FastAPI):
    c = ETAT.get("cfg") or charger()
    c.data.mkdir(parents=True, exist_ok=True)
    base.preparer(c.data)
    reglages = maison.Reglages(c.data / "reglages.json", REGLAGES_DEFAUTS, REGLAGES_VARIABLES)
    gestion = Gestionnaire(c, catalogue(c.catalogue))
    sessions = Sessions(APPLI, c.password, _lire_generation(c))
    ETAT.update(cfg=c, reglages=reglages, sessions=sessions, gestionnaire=gestion, demarrage=time.monotonic())
    ETAT.setdefault("lire_anneau", None)
    relais = {a: Relais(gestion, a, lambda cookies: ETAT["sessions"].connecte(cookies)) for a in gestion.applis}
    ETAT["relais"] = relais
    ETAT["regie"] = douze.Regie(relais["douze-points"]) if "douze-points" in relais else None
    await asyncio.to_thread(_faire_autotest)
    taches = [asyncio.create_task(gestion.veiller()), asyncio.create_task(_purger_copies())]
    if c.relais:
        taches += await servir(list(relais.values()))
    # 0.1.1 : une ligne claire dans le journal du conteneur (Portainer)
    ports = sorted(a.port for a in gestion.applis.values())
    logging.getLogger("uvicorn.error").warning(
        "Bac à sable %s prêt : écran sur le port %s (http), applis simulées sur %s à %s ; autotest : %s",
        __version__, gestion.cfg_port_bac, ports[0], ports[-1], ETAT["autotest"]["message"])
    try:
        yield
    finally:
        if ETAT.get("regie"):
            await ETAT["regie"].arreter()
        await gestion.tout_arreter()
        for t in taches:
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await t


app = FastAPI(title=APPLI, version=__version__, lifespan=cycle, docs_url=None, redoc_url=None)


@app.middleware("http")
async def garde(request: Request, appel):
    chemin = request.url.path
    if chemin.startswith("/api/") and chemin not in PUBLIQUES and not ETAT["sessions"].connecte(request.cookies):
        return JSONResponse({"detail": "Connexion nécessaire."}, status_code=401)
    reponse = await appel(request)
    if chemin.startswith(("/api/", "/externe/")):
        reponse.headers["Cache-Control"] = "no-store"
    return reponse


def adresse_appli(request: Request, ident: str) -> str:
    """L'adresse de l'appli simulée vue par ce navigateur : même hôte que le Bac à sable, port de l'appli."""
    return f"{request.url.scheme}://{request.url.hostname}:{g().applis[ident].port}"


def connu(ident: str) -> None:
    if ident not in g().applis:
        raise HTTPException(404, "Appli inconnue du Bac à sable.")


# ================================================================ public

@app.get("/health")
def sante(request: Request):
    """Des nombres seulement (tuile de l'Anneau) : applis lancées, scénarios, personnes ; aucun nom."""
    session_ok = "sessions" in ETAT and ETAT["sessions"].connecte(request.cookies)
    nombres = {}
    if "gestionnaire" in ETAT:
        with base.base(cfg().data) as cx:
            nombres = {"scenarios": cx.execute("SELECT COUNT(*) FROM scenario").fetchone()[0],
                       "personnes": cx.execute("SELECT COUNT(*) FROM personne").fetchone()[0]}
        nombres["applis_lancees"] = sum(1 for e in g().etats.values() if e.vivant())
        nombres["coupure"] = bool(ETAT.get("autotest", {}).get("ok"))
    return {"ok": True, "version": __version__, **nombres, **maison.sante(request, session_ok=session_ok)}


# ================================================================ connexion

@app.get("/api/session")
def session(request: Request):
    return {"connecte": ETAT["sessions"].connecte(request.cookies), "version": __version__}


@app.post("/api/connexion")
async def connexion(request: Request, corps: dict = Body(...)):
    s = ETAT["sessions"]
    if cfg().attente_connexion:
        await asyncio.sleep(s.attente())
    if not s.verifier_mot_de_passe(str(corps.get("mot_de_passe", ""))):
        raise HTTPException(401, "Mot de passe incorrect.")
    r = JSONResponse({"ok": True})
    r.set_cookie(s.cookie, s.creer(), max_age=DUREE, httponly=True, samesite="strict", secure=en_https(request))
    return r


@app.post("/api/deconnexion")
def deconnexion():
    s = ETAT["sessions"]
    s.generation += 1
    try:
        (cfg().data / "session_generation").write_text(str(s.generation))
    except OSError:
        pass
    r = JSONResponse({"ok": True})
    r.delete_cookie(s.cookie)
    r.delete_cookie(COMMUN)
    return r


# ================================================================ applis

@app.get("/api/applis")
def applis(request: Request):
    return {"applis": [{**g().etat(a), "adresse": adresse_appli(request, a)} for a in g().applis],
            "bloque": g().bloque, "max_simultanees": cfg().max_simultanees, "arret_minutes": cfg().arret_minutes}


@app.post("/api/applis/{ident}/demarrer")
async def demarrer(ident: str, request: Request):
    connu(ident)
    try:
        etat = await g().demarrer(ident, adresse_publique=adresse_appli(request, ident))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    ETAT["relais"][ident].session = {}
    return {**etat, "adresse": adresse_appli(request, ident)}


@app.post("/api/applis/{ident}/arreter")
async def arreter(ident: str):
    connu(ident)
    if ident == "douze-points" and ETAT.get("regie"):
        await ETAT["regie"].arreter()
    await g().arreter(ident)
    return g().etat(ident)


@app.post("/api/applis/{ident}/vider")
async def vider(ident: str):
    """Arrête l'appli et jette ses données simulées : au prochain lancement, elle repart de zéro."""
    connu(ident)
    if ident == "douze-points" and ETAT.get("regie"):
        await ETAT["regie"].arreter()
        ETAT["regie"].soiree = douze.Soiree()
    await g().vider(ident)
    ETAT["relais"][ident].session = {}
    return g().etat(ident)


@app.post("/api/applis/tout-arreter")
async def tout_arreter():
    if ETAT.get("regie"):
        await ETAT["regie"].arreter()
    await g().tout_arreter()
    return {"ok": True}


# ================================================================ personnes

def _traduire_liens(cx, ids: list[int], gens: list[dict]) -> None:
    """Les liens d'une fournée inventée pointent vers des indices : on les change en identifiants."""
    for pid, p in zip(ids, gens):
        if p.get("liens"):
            p = {**p, "liens": [{"vers": ids[x["vers"]], "relation": x["relation"]} for x in p["liens"]]}
            base.changer_donnees(cx, pid, p)


@app.get("/api/personnes")
def lister_personnes():
    with base.base(cfg().data) as cx:
        gens = base.personnes(cx)
    return {"personnes": gens, "copie_carnet": bool(cfg().carnet_url and cfg().carnet_jeton),
            "duree_copies_jours": cfg().duree_copies_jours}


@app.post("/api/personnes/inventer")
def inventer(corps: dict = Body(...)):
    n = int(corps.get("nombre", 8))
    if not 1 <= n <= 200:
        raise HTTPException(422, "De 1 à 200 personnes à la fois.")
    gens = personnes.inventer(n, graine=corps.get("graine"), variete=int(corps.get("variete", 50)))
    with base.base(cfg().data) as cx:
        ids = [base.ajouter_personne(cx, "inventee", p) for p in gens]
        _traduire_liens(cx, ids, gens)
    return {"ajoutees": ids}


@app.post("/api/personnes/pieges")
def ajouter_pieges():
    with base.base(cfg().data) as cx:
        ids = [base.ajouter_personne(cx, "piege", p) for p in personnes.pieges()]
    return {"ajoutees": ids}


@app.get("/api/carnet/personnes")
async def carnet_personnes(q: str = ""):
    """Recherche dans les vraies fiches de carnet (lecture seule). Rien n'est gardé tant qu'on ne copie pas."""
    try:
        fiches = await asyncio.to_thread(personnes.lire_carnet, cfg().carnet_url, cfg().carnet_jeton,
                                         ETAT.get("transport_carnet"))
    except personnes.CarnetInjoignable as exc:
        raise HTTPException(503, str(exc)) from exc
    mots = [m for m in q.casefold().split() if m]
    trouves = [f for f in fiches if all(m in f"{f['prenom']} {f['nom']}".casefold() for m in mots)]
    with base.base(cfg().data) as cx:
        deja = {r["carnet_id"] for r in cx.execute("SELECT carnet_id FROM personne WHERE carnet_id IS NOT NULL")}
    return {"fiches": [{**f, "copiee": f["carnet_id"] in deja} for f in trouves[:50]], "total": len(trouves)}


@app.post("/api/personnes/copier")
async def copier(corps: dict = Body(...)):
    voulus = {str(x) for x in corps.get("carnet_ids") or []}
    if not voulus:
        raise HTTPException(422, "Choisis au moins une fiche.")
    try:
        fiches = await asyncio.to_thread(personnes.lire_carnet, cfg().carnet_url, cfg().carnet_jeton,
                                         ETAT.get("transport_carnet"))
    except personnes.CarnetInjoignable as exc:
        raise HTTPException(503, str(exc)) from exc
    ajoutees = []
    with base.base(cfg().data) as cx:
        deja = {r["carnet_id"] for r in cx.execute("SELECT carnet_id FROM personne WHERE carnet_id IS NOT NULL")}
        for f in fiches:
            if f["carnet_id"] in voulus and f["carnet_id"] not in deja:
                ajoutees.append(base.ajouter_personne(cx, "reelle", personnes.depuis_carnet(f), f["carnet_id"]))
    return {"ajoutees": ajoutees}


@app.put("/api/personnes/{pid}")
def changer_personne(pid: int, corps: dict = Body(...)):
    with base.base(cfg().data) as cx:
        r = cx.execute("SELECT * FROM personne WHERE id=?", (pid,)).fetchone()
        if not r:
            raise HTTPException(404, "Personne inconnue.")
        if "epinglee" in corps:
            cx.execute("UPDATE personne SET epinglee=? WHERE id=?", (int(bool(corps["epinglee"])), pid))
        champs = {k: corps[k] for k in ("prenom", "nom", "genre", "naissance", "ville", "telephone", "courriel")
                  if k in corps}
        if champs:
            if r["origine"] == "reelle":
                raise HTTPException(409, "Une copie de vraie fiche ne se modifie pas ici : change la fiche dans carnet.")
            base.changer_donnees(cx, pid, {**json.loads(r["donnees"]), **{k: str(v)[:120] for k, v in champs.items()}})
        return base.personne(cx.execute("SELECT * FROM personne WHERE id=?", (pid,)).fetchone())


@app.post("/api/personnes/effacer")
def effacer(corps: dict = Body(...)):
    """`ids` : ces personnes ; `origine` : toutes celles de cette origine ; `tout` : toutes. Effacées pour de bon."""
    with base.base(cfg().data) as cx:
        if corps.get("tout"):
            n = base.effacer_personnes(cx, None)
        elif corps.get("origine"):
            ids = [r["id"] for r in cx.execute("SELECT id FROM personne WHERE origine=?", (str(corps["origine"]),))]
            n = base.effacer_personnes(cx, ids)
        else:
            n = base.effacer_personnes(cx, [int(x) for x in corps.get("ids") or []])
    base.compacter(cfg().data)
    return {"effacees": n}


# ================================================================ scénarios

def _scenario_valide(corps: dict) -> dict:
    nom = " ".join(str(corps.get("nom", "")).split())[:80]
    if not nom:
        raise HTTPException(422, "Il faut un nom de scénario.")
    applis_voulues = [a for a in corps.get("applis") or [] if a in g().applis]
    if not applis_voulues:
        raise HTTPException(422, "Choisis au moins une appli.")
    return {"nom": nom, "applis": applis_voulues, "personnes": [int(x) for x in corps.get("personnes") or []],
            "reglages": corps.get("reglages") or {}, "epingle": bool(corps.get("epingle"))}


@app.get("/api/scenarios")
def lister_scenarios():
    with base.base(cfg().data) as cx:
        return {"scenarios": base.scenarios(cx)}


@app.post("/api/scenarios")
def creer_scenario(corps: dict = Body(...)):
    s = _scenario_valide(corps)
    with base.base(cfg().data) as cx:
        return {"id": base.ecrire_scenario(cx, s)}


@app.put("/api/scenarios/{sid}")
def changer_scenario(sid: int, corps: dict = Body(...)):
    with base.base(cfg().data) as cx:
        ancien = base.lire_scenario(cx, sid)
        if not ancien:
            raise HTTPException(404, "Scénario inconnu.")
        s = _scenario_valide({**ancien, **corps})
        base.ecrire_scenario(cx, s, sid)
        return base.lire_scenario(cx, sid)


@app.post("/api/scenarios/{sid}/dupliquer")
def dupliquer_scenario(sid: int):
    with base.base(cfg().data) as cx:
        s = base.lire_scenario(cx, sid)
        if not s:
            raise HTTPException(404, "Scénario inconnu.")
        return {"id": base.ecrire_scenario(cx, {**s, "nom": f"{s['nom']} (copie)"[:80], "epingle": False})}


@app.delete("/api/scenarios/{sid}")
def effacer_scenario(sid: int):
    with base.base(cfg().data) as cx:
        cx.execute("DELETE FROM scenario WHERE id=?", (sid,))
    return {"ok": True}


@app.post("/api/scenarios/{sid}/jouer")
async def jouer_scenario(sid: int, request: Request, corps: dict = Body(default={})):
    """Remet l'appli à zéro, y verse le scénario et la démarre. Pour Douze points, monte aussi la soirée."""
    ident = str(corps.get("appli", ""))
    with base.base(cfg().data) as cx:
        s = base.lire_scenario(cx, sid)
        if not s:
            raise HTTPException(404, "Scénario inconnu.")
        if ident not in s["applis"]:
            raise HTTPException(422, "Cette appli ne fait pas partie du scénario.")
        detail = base.personnes(cx, s["personnes"])
        cx.execute("UPDATE scenario SET joue_le=? WHERE id=?", (base.maintenant(), sid))
    contenu = {**s, "personnes_detail": detail, "appli": ident}
    try:
        await g().demarrer(ident, scenario=contenu, remettre_a_zero=True,
                           adresse_publique=adresse_appli(request, ident))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    ETAT["relais"][ident].session = {}
    res = {"appli": ident, "adresse": adresse_appli(request, ident), "personnes": len(detail),
           "versees": g().applis[ident].personnes}
    if ident == "douze-points":
        r = ETAT["reglages"].tout()
        reglages = {"telephones": r["douze_telephones"], "chansons": r["douze_chansons"],
                    **(s["reglages"].get("douze-points") or {})}
        try:
            res["soiree"] = await ETAT["regie"].preparer(detail, reglages)
        except Exception as exc:  # noqa: BLE001 — le message va à l'écran
            raise HTTPException(409, f"Soirée impossible à monter : {exc}") from exc
    return res


# ================================================================ Douze points : soirée simulée

@app.get("/api/douze")
def douze_etat(request: Request):
    regie = ETAT.get("regie")
    if not regie:
        raise HTTPException(404, "Douze points n'est pas embarqué.")
    adresse = adresse_appli(request, "douze-points")
    res = regie.resume()
    res["lien_invites"] = f"{adresse}/invite/{res['jeton_invite']}" if res["jeton_invite"] else ""
    res["adresse"] = adresse
    res["lancee"] = g().etats["douze-points"].vivant()
    return res


@app.post("/api/douze/jouer")
async def douze_jouer(corps: dict = Body(default={})):
    regie = ETAT.get("regie")
    if not regie or not g().etats["douze-points"].vivant():
        raise HTTPException(409, "Lance d'abord un scénario sur Douze points.")
    tempo = 0.0 if corps.get("avance_rapide") else float(corps.get("tempo", ETAT["reglages"].tout()["douze_tempo"]))
    try:
        return await regie.jouer(tempo=max(0.0, min(tempo, 120.0)), envoyer=bool(corps.get("envoyer", True)))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/douze/arreter")
async def douze_arreter():
    regie = ETAT.get("regie")
    if regie:
        await regie.arreter()
    return regie.resume() if regie else {}


@app.get("/api/douze/qr.svg")
def douze_qr(request: Request):
    """Le QR code de la porte invité (vrai iPhone), vers le port de Douze points de ce Bac à sable."""
    import io

    import segno
    regie = ETAT.get("regie")
    if not regie or not regie.soiree.jeton_invite:
        raise HTTPException(404, "Pas de soirée simulée.")
    lien = f"{adresse_appli(request, 'douze-points')}/invite/{regie.soiree.jeton_invite}"
    tampon = io.BytesIO()
    segno.make(lien, error="m").save(tampon, kind="svg", scale=8, border=2, dark="#151311", light="#f2ece2",
                                     xmldecl=False)
    from fastapi.responses import Response
    return Response(tampon.getvalue(), media_type="image/svg+xml")


# ================================================================ journal

@app.get("/api/journal")
def lire_journal(appli: str = "", sorte: str = "", limite: int = 300):
    """Ce que les applis simulées ont tenté : écritures reçues par les faux services, sorties refusées."""
    lignes: list[dict] = []
    for ident in g().applis:
        if appli and ident != appli:
            continue
        try:
            texte = g().journal_appli(ident).read_text(encoding="utf-8", errors="replace").splitlines()[-2000:]
        except OSError:
            continue
        for t in texte:
            try:
                ligne = json.loads(t)
            except ValueError:
                continue
            if ligne.get("sorte") == "demarrage" or (sorte and ligne.get("sorte") != sorte):
                continue
            lignes.append(ligne)
    lignes.sort(key=lambda x: x.get("quand", ""), reverse=True)
    compte = {"ecriture": 0, "sortie_refusee": 0, "nom_refuse": 0}
    for x in lignes:
        if x.get("sorte") in compte:
            compte[x["sorte"]] += 1
    return {"lignes": lignes[:max(1, min(limite, 2000))], "compte": compte}


@app.get("/api/applis/{ident}/sortie")
def sortie_appli(ident: str, lignes: int = 300):
    """0.1.4 : la fin du journal du processus de l'appli simulée (erreurs Python, « Internal Server Error »…),
    pour comprendre une erreur 500 sans aller chercher le fichier sur le NAS."""
    connu(ident)
    chemin = g().dossier(ident) / "sortie.log"
    try:
        texte = chemin.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        texte = []
    fin = texte[-max(20, min(lignes, 3000)):]
    erreurs = sum(1 for t in texte if t.startswith("Traceback") or "Exception in ASGI application" in t)
    return {"appli": ident, "lignes": fin, "total": len(texte), "erreurs": erreurs}


# ================================================================ autotest, réglages, synthèse

@app.get("/api/autotest")
def lire_autotest():
    return ETAT.get("autotest") or {}


@app.post("/api/autotest")
async def relancer_autotest():
    return await asyncio.to_thread(_faire_autotest)


@app.get("/api/reglages")
def lire_reglages():
    return {"reglages": ETAT["reglages"].tout()}


@app.put("/api/reglages")
def changer_reglages(corps=Body(...)):
    if not isinstance(corps, dict):
        raise HTTPException(400, "Réglages attendus sous la forme {clé: valeur}.")
    try:
        return {"reglages": ETAT["reglages"].changer(corps)}
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, f"Valeur refusée : {exc}.") from exc


@app.get("/api/synthese")
def synthese():
    from .processus import memoire_mo
    import os
    vivantes = [g().etat(a) for a in g().applis if g().etats[a].vivant()]
    return {"version": __version__, "en_service_secondes": int(time.monotonic() - ETAT["demarrage"]),
            "memoire_bac_mo": round(memoire_mo(os.getpid())),
            "memoire_applis_mo": sum(x["memoire_mo"] for x in vivantes),
            "embarquees": [{"id": a.id, "nom": a.nom, "version": a.version, "depot": a.depot, "sha": a.sha[:7],
                            "port": a.port, "installee": g().source(a.id).is_dir()} for a in g().applis.values()],
            "versions": [{"nom": APPLI, "version": __version__},
                         {"nom": "Python", "version": platform.python_version()},
                         {"nom": "FastAPI", "version": version_paquet("fastapi")},
                         {"nom": "Uvicorn", "version": version_paquet("uvicorn")}],
            "carnet_relie": bool(cfg().carnet_url and cfg().carnet_jeton),
            "le": datetime.now().astimezone().isoformat(timespec="seconds")}


# ================================================================ sauvegarde (contrat 1)

@app.get("/externe/sauvegarde")
def externe_sauvegarde(request: Request):
    acceptes = maison.jetons()
    if not acceptes:
        raise HTTPException(404, "Not Found")
    if not maison.jeton_valide(maison.jeton_propose(request.headers), acceptes):
        raise HTTPException(401, "Jeton commun manquant ou invalide.")
    return maison.sauvegarde(APPLI, __version__, ETAT["reglages"].tout(), exclus=EXCLUS_SAUVEGARDE)


# ================================================================ interface

@app.get("/{chemin:path}")
def interface(chemin: str):
    statique: Path = cfg().static
    fichier = (statique / chemin).resolve() if chemin else None
    if fichier and fichier.is_file() and statique.resolve() in fichier.parents:
        return FileResponse(fichier)
    index = statique / "index.html"
    if index.is_file():
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
    return JSONResponse({"detail": "Interface non compilée."}, status_code=404)
