"""Bac à sable : les vraies applis maison, lancées à la demande sur une fausse maison, pour les essayer sans rien
écrire chez les vrais services.

Routes : /health (publique), /api/session, /api/connexion, /api/deconnexion,
/api/applis (état, démarrer, arrêter, vider), /api/personnes (inventer, pièges, copier depuis carnet, épingler,
effacer), /api/scenarios (créer, jouer, effacer), /api/douze (soirée simulée, téléphones), /api/journal,
/api/autotest, /api/reglages, /api/synthese, /api/maison/services (fiches « Connexion », contrat 3),
0.4.0 : /api/liens (liens entre applis simulées), /api/maison/remise-a-zero (aperçu et remise à zéro de toute la
maison simulée), /api/douze/cloturer ; /externe/sauvegarde (jeton commun, pour l'Anneau), puis l'interface.
Les applis simulées sont servies par le relais, chacune sur son port (app/relais.py) ; le faux annuaire de l'Anneau
écoute en 127.0.0.1 seulement (app/annuaire.py).
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

from . import __version__, annuaire, autotest, base, douze, liens, maison, personnes
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
    # 0.4.0 (conseil) : adresses des liens toutes en 127.0.0.1, jeton simulé différent du vrai, toujours vérifiés
    liens_ok, liens_message = autotest.verifier_liens(g())
    resultat = {**resultat, "liens": {"ok": liens_ok, "message": liens_message}}
    if not liens_ok:
        resultat.update(ok=False, message=f"{liens_message} Applis bloquées.")
    ETAT["autotest"] = resultat
    g().bloque = "" if resultat["ok"] else resultat["message"]
    return resultat


@asynccontextmanager
async def cycle(app: FastAPI):
    c = ETAT.get("cfg") or charger()
    c.data.mkdir(parents=True, exist_ok=True)
    base.preparer(c.data)
    reglages = maison.Reglages(c.data / "reglages.json", REGLAGES_DEFAUTS, REGLAGES_VARIABLES)
    gestion = Gestionnaire(c, catalogue(c.catalogue), liens.charger(c.catalogue))
    sessions = Sessions(APPLI, c.password, _lire_generation(c))
    ETAT.update(cfg=c, reglages=reglages, sessions=sessions, gestionnaire=gestion, demarrage=time.monotonic())
    ETAT.setdefault("lire_anneau", None)
    relais = {a: Relais(gestion, a, lambda cookies: ETAT["sessions"].connecte(cookies)) for a in gestion.applis}
    ETAT["relais"] = relais
    ETAT["regie"] = douze.Regie(relais["douze-points"]) if "douze-points" in relais else None
    await asyncio.to_thread(_faire_autotest)
    taches = [asyncio.create_task(gestion.veiller()), asyncio.create_task(_purger_copies())]
    if c.annuaire:
        taches.append(await annuaire.servir(annuaire.FauxAnnuaire(gestion), gestion.port_annuaire))
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


# ================================================================ fiches « Connexion » (0.2.0, contrat 3, socle 0.11.0)
# GET /api/maison/services et POST /api/maison/services/{id}/verifier (session ou ANNEAU_CLE) : écran commun
# $lib/services/Services.svelte, et fiche « État » de l'Anneau (bandeau « Simulé » : simule=True).
# Une fiche par VRAI lien du Bac à sable : carnet seulement (copie de vraies fiches). Les applis embarquées
# (Douze points, carnet simulé…) ne joignent que des faux services, elles n'ont pas de fiche ici.
# Essai léger : relire la liste des fiches de carnet (lecture, rien n'est gardé ni écrit).

def _essai_carnet():
    fiches = personnes.lire_carnet(cfg().carnet_url, cfg().carnet_jeton, ETAT.get("transport_carnet"))
    return True, f"{len(fiches)} fiches lisibles."


SERVICES = maison.Services(APPLI, simule=True)
SERVICES.ajouter(
    "carnet", "carnet", genre="maison", cible="carnet",
    lit="Les vraies fiches de carnet (nom, prénom, naissance, genre), en lecture seule, pour en copier quelques-unes "
        "dans les personnes du Bac à sable. Le Bac à sable lui-même peut joindre carnet, sans jamais transmettre cet "
        "accès aux applis simulées.",
    ecrit="Rien.", regle=lambda: bool(cfg().carnet_url and cfg().carnet_jeton),
    reglage="BAC_CARNET_URL et MAISON_JETON", essai=_essai_carnet)
# Monté APRÈS la garde : le dernier middleware ajouté passe en premier.
maison.monter_services(app, SERVICES, lambda r: "sessions" in ETAT and ETAT["sessions"].connecte(r.cookies))


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
            "bloque": g().bloque, "arret_minutes": cfg().arret_minutes, "remise": g().remise,
            "memoire_mo": round(g().memoire_totale()), "memoire_limite_mo": cfg().memoire_limite_mo}


@app.post("/api/applis/{ident}/demarrer")
async def demarrer(ident: str, request: Request):
    """0.4.0 : démarre d'abord les applis qu'elle appelle (cascade), puis elle."""
    connu(ident)
    vivantes_avant = {a for a, e in g().etats.items() if e.vivant()}
    try:
        etat = await g().ouvrir(ident, adresse_publique=adresse_appli(request, ident))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc
    for a, e in g().etats.items():
        if e.vivant() and a not in vivantes_avant:
            ETAT["relais"][a].session = {}
    return {**etat, "adresse": adresse_appli(request, ident),
            "cascade": [g().applis[a].nom for a in g().liens.cascade(ident)]}


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


def _lire_scenario_complet(sid: int) -> tuple[dict, list[dict]]:
    with base.base(cfg().data) as cx:
        s = base.lire_scenario(cx, sid)
        if not s:
            raise HTTPException(404, "Scénario inconnu.")
        detail = base.personnes(cx, s["personnes"])
    return s, detail


async def _reverser(s: dict, detail: list[dict], request: Request, ouvrir: str = "") -> dict:
    """0.4.0 : verse le scénario dans toute la maison simulée (déjà vidée, sous le verrou de la remise à zéro) :
    chaque appli branchée reçoit les personnes du scénario ; les applis du scénario démarrent (avec celles qu'elles
    appellent) ; pour Douze points, la soirée est montée, et jouée jusqu'à la clôture si le scénario le dit."""
    contenu = {**s, "personnes_detail": detail}
    for ident, a in g().applis.items():
        if a.branchee:
            g().preparer_dossier(ident, {**contenu, "appli": ident}, remettre_a_zero=False)
    a_ouvrir = list(dict.fromkeys(([ouvrir] if ouvrir else []) + list(s["applis"])))
    for ident in a_ouvrir:
        await g().ouvrir(ident, adresse_publique=adresse_appli(request, ident), interne=True)
    for r in ETAT["relais"].values():
        r.session = {}
    with base.base(cfg().data) as cx:
        cx.execute("UPDATE scenario SET joue_le=? WHERE id=?", (base.maintenant(), s["id"]))
    ETAT["scenario_maison"] = s["id"]
    res = {"scenario": s["id"], "ouvertes": [g().applis[a].nom for a, e in g().etats.items() if e.vivant()],
           "personnes": len(detail)}
    if "douze-points" in a_ouvrir and ETAT.get("regie"):
        r = ETAT["reglages"].tout()
        voulus = s["reglages"].get("douze-points") or {}
        reglages = {"telephones": r["douze_telephones"], "chansons": r["douze_chansons"], **voulus}
        try:
            res["soiree"] = await ETAT["regie"].preparer(detail, reglages)
            if voulus.get("cloturee"):
                await ETAT["regie"].jouer(tempo=0.0, envoyer=True)
                res["soiree"] = await ETAT["regie"].cloturer()
        except Exception as exc:  # noqa: BLE001 — le message va à l'écran
            raise HTTPException(409, f"Soirée impossible à monter : {exc}") from exc
    return res


async def _remettre_la_maison_a_zero(request: Request, sid: int | None, ouvrir: str = "") -> dict:
    """0.4.0 : une seule remise à zéro pour toute la maison simulée (verrou commun : aucun démarrage pendant ce temps),
    toutes les bases vidées (Gazette comprise), puis le scénario reversé."""
    s, detail = _lire_scenario_complet(sid) if sid else (None, [])
    if s and ouvrir and ouvrir not in s["applis"]:
        raise HTTPException(422, "Cette appli ne fait pas partie du scénario.")
    if ETAT.get("regie"):
        await ETAT["regie"].arreter()
        ETAT["regie"].soiree = douze.Soiree()
    try:
        async with g().remise_a_zero():
            if not s:
                ETAT["scenario_maison"] = None
                return {"scenario": None, "ouvertes": [], "personnes": 0}
            return await _reverser(s, detail, request, ouvrir)
    except RuntimeError as exc:
        raise HTTPException(409, str(exc)) from exc


@app.post("/api/scenarios/{sid}/jouer")
async def jouer_scenario(sid: int, request: Request, corps: dict = Body(default={})):
    """0.4.0 : jouer un scénario remet toute la maison simulée à zéro et y verse ce scénario (les applis restent
    cohérentes entre elles), puis ouvre `appli` (et celles qu'elle appelle). Pour Douze points, monte aussi la soirée."""
    ident = str(corps.get("appli", ""))
    s, detail = _lire_scenario_complet(sid)
    if ident not in s["applis"]:
        raise HTTPException(422, "Cette appli ne fait pas partie du scénario.")
    res = await _remettre_la_maison_a_zero(request, sid, ouvrir=ident)
    return {**res, "appli": ident, "adresse": adresse_appli(request, ident), "personnes": len(detail),
            "versees": g().applis[ident].personnes}


def _apercu_remise(sid: int | None) -> dict:
    """Ce que la remise à zéro fera perdre, et ce qu'elle reversera (affiché avant de confirmer)."""
    applis_ = []
    ecritures = photos = 0
    for ident, a in g().applis.items():
        d = g().dossier(ident) / "donnees"
        if d.exists():
            taille = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            applis_.append({"id": ident, "nom": a.nom, "taille_ko": round(taille / 1024)})
        try:
            for ligne in g().journal_appli(ident).read_text(encoding="utf-8", errors="replace").splitlines():
                if '"sorte": "ecriture"' in ligne:
                    ecritures += 1
                    photos += 1 if "/assets" in ligne else 0
        except OSError:
            pass
    regie = ETAT.get("regie")
    soiree = regie.resume() if regie else {}
    reverse = None
    if sid:
        s, detail = _lire_scenario_complet(sid)
        voulus = s["reglages"].get("douze-points") or {}
        reverse = {"id": s["id"], "nom": s["nom"], "personnes": len(detail),
                   "copies": sum(1 for p in detail if p["origine"] == "reelle"),
                   "applis": [g().applis[a].nom for a in s["applis"] if a in g().applis],
                   "soiree": "douze-points" in s["applis"], "soiree_cloturee": bool(voulus.get("cloturee"))}
    return {"perdu": {"applis": applis_, "ecritures": ecritures, "photos": photos,
                      "soiree": bool(soiree.get("soiree_id")), "soiree_cloturee": bool(soiree.get("cloturee"))},
            "reverse": reverse, "scenario_maison": ETAT.get("scenario_maison")}


@app.get("/api/maison/remise-a-zero")
def apercu_remise(scenario: int | None = None):
    return _apercu_remise(scenario if scenario is not None else ETAT.get("scenario_maison"))


@app.post("/api/maison/remise-a-zero")
async def remise_a_zero(request: Request, corps: dict = Body(default={})):
    """Remet toute la maison simulée à zéro (confirmation obligatoire), puis reverse le scénario choisi (s'il y en a)."""
    if corps.get("confirmer") is not True:
        raise HTTPException(422, "Confirme la remise à zéro : tout ce qui a été joué dans la maison simulée sera perdu.")
    sid = corps.get("scenario")
    return await _remettre_la_maison_a_zero(request, int(sid) if sid else None)


@app.get("/api/liens")
def lister_liens():
    """0.4.0 : les liens entre applis simulées (branchés ou coupés, et pourquoi), et la copie figée des flux."""
    figes = liens.flux_figes(Path(cfg().catalogue).parent / "docs" / "flux-maison.json") \
        if (Path(cfg().catalogue).parent / "docs" / "flux-maison.json").is_file() else []
    ecart = liens.comparer(g().liens.tous, figes, g().applis) if figes else {"manquants": [], "en_trop": []}
    return {"liens": g().liens.etat(), "ecart": ecart,
            "vivantes": [a for a, e in g().etats.items() if e.vivant()]}


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


@app.post("/api/douze/cloturer")
async def douze_cloturer():
    """0.4.0 : la soirée jusqu'au bout (dévoilement, fin, clôture) : carnet simulé la reçoit, la Gazette simulée la lit."""
    regie = ETAT.get("regie")
    if not regie or not g().etats["douze-points"].vivant():
        raise HTTPException(409, "Lance d'abord un scénario sur Douze points.")
    try:
        return await regie.cloturer()
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
