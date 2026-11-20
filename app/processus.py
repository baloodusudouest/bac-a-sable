"""Lancement à la demande des applis simulées.

Chaque appli tourne dans son propre processus Python (toutes s'appellent `app`), avec :
- un environnement construit de zéro (rien n'est hérité du conteneur : ni MAISON_PASSWORD, ni vrai jeton, ni adresse) ;
- PYTHONPATH = la garde (sitecustomize : aucune sortie réseau), son code, son site-packages, les outils communs ;
- son dossier de données propre, <données>/applis/<appli>/ ;
- un port local (port publié + 1000), joint seulement par le relais et par les applis qui ont un lien vers elle.

0.4.0 — « la maison branchée » (dossier docs/ajout-0.4.0.md, conseil docs/conseil-0.4.0.md) :
- liens entre applis simulées (app/liens.py) : variables d'adresse vers 127.0.0.1, jeton commun simulé tiré au hasard
  à chaque démarrage (`secrets`, jamais lu dans l'environnement du conteneur), faux annuaire de l'Anneau
  (MAISON_ANNEAU_URL), ports permis à la garde (BAS_PORTS) ;
- contrôle avant chaque lancement : toute variable `*_URL` doit viser 127.0.0.1, aucune variable ne vaut le vrai
  MAISON_JETON ;
- démarrage en cascade : ouvrir une appli démarre d'abord celles qu'elle appelle (lecture ou écriture), sans boucle ;
- activité propagée : toucher une appli touche aussi celles-là (sinon carnet, lu par la Gazette, s'arrêtait seul) ;
- mémoire : une seule limite pour toute la maison (2,4 Go par défaut), mesurée sur l'arbre des processus du conteneur,
  Chromium compris ; au-delà, l'appli touchée il y a le plus longtemps s'arrête (jamais celle qu'on ouvre ni celles
  qu'elle appelle) et le dit ; la limite de 4 applis à la fois disparaît ;
- verrou de la remise à zéro de la maison : aucun démarrage (cascade, relais) pendant qu'on vide et reverse.

Une appli sans requête depuis `arret_minutes` est arrêtée.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import secrets
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml

from . import liens as L

journal = logging.getLogger("bac-a-sable.processus")
DECALAGE = 1000            # l'appli écoute sur port + DECALAGE, en 127.0.0.1
ATTENTE_DEMARRAGE = 90     # secondes pour répondre à /health
PORT_ANNUAIRE = 9104       # faux annuaire de l'Anneau, en 127.0.0.1 seulement (app/annuaire.py)
MESSAGE_MEMOIRE = "arrêtée pour libérer la mémoire ; ses données sont gardées ; la rouvrir"
REMISE_EN_COURS = "La maison simulée est en cours de remise à zéro : réessaie dans un instant."


@dataclass
class Appli:
    id: str
    nom: str
    depot: str
    version: str
    sha: str
    port: int
    lanceur: str
    mot_de_passe: str
    site: str
    static: str
    module: str = ""
    args: list = field(default_factory=list)
    env: dict = field(default_factory=dict)
    personnes: bool = False
    memoire: int = 400

    @property
    def port_local(self) -> int:
        return self.port + DECALAGE

    @property
    def branchee(self) -> bool:
        """0.4.0 : lanceur écrit ici, données prises dans le scénario et chez les autres applis simulées."""
        return self.lanceur == "bac"


def catalogue(chemin: Path) -> dict[str, Appli]:
    brut = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
    res = {}
    for ident, a in (brut.get("applis") or {}).items():
        res[ident] = Appli(id=ident, nom=a["nom"], depot=a["depot"], version=str(a["version"]), sha=a["sha"],
                           port=int(a["port"]), lanceur=a["lanceur"], mot_de_passe=a["mot_de_passe"],
                           site=a["site"], static=a["static"], module=a.get("module", ""),
                           args=list(a.get("args") or []), env=dict(a.get("env") or {}),
                           personnes=str(a.get("personnes", "non")).lower() in ("oui", "true", "1"),
                           memoire=int(a.get("memoire", 400)))
    return res


@dataclass
class Etat:
    processus: subprocess.Popen | None = None
    demarre_le: float = 0.0
    derniere_requete: float = 0.0
    scenario: int | None = None
    erreur: str = ""
    lancee_pour: str = ""          # 0.4.0 : « gazette » quand elle a démarré en cascade pour la Gazette
    arret_memoire: bool = False    # 0.4.0 : arrêtée pour libérer la mémoire (données gardées)
    demarrage: asyncio.Lock = field(default_factory=asyncio.Lock)

    def vivant(self) -> bool:
        return self.processus is not None and self.processus.poll() is None


def _enfants(pid: int) -> list[int]:
    res = []
    try:
        for tache in Path(f"/proc/{pid}/task").iterdir():
            try:
                res += [int(x) for x in (tache / "children").read_text().split()]
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    return res


def arbre(pid: int) -> list[int]:
    """Le processus et tous ses descendants (Chromium de la Gazette est un petit-enfant : pilote node, puis Chromium)."""
    vus, pile = [], [pid]
    while pile:
        p = pile.pop()
        if p in vus:
            continue
        vus.append(p)
        pile += _enfants(p)
    return vus


def memoire_mo(pid: int) -> float:
    """Mémoire résidente du processus et de toute sa descendance, en Mo."""
    total = 0
    for p in arbre(pid):
        try:
            for ligne in Path(f"/proc/{p}/status").read_text().splitlines():
                if ligne.startswith("VmRSS:"):
                    total += int(ligne.split()[1])
                    break
        except (OSError, ValueError):
            continue
    return total / 1024


class Gestionnaire:
    def __init__(self, cfg, applis: dict[str, Appli], table_liens: list[L.Lien] | None = None):
        self.cfg = cfg
        self.applis = applis
        self.etats: dict[str, Etat] = {a: Etat() for a in applis}
        self.liens = L.Liens(table_liens or [], applis)
        self.bloque = ""        # message de l'autotest quand il a échoué : aucune appli ne démarre
        self.cfg_port_bac = int(os.environ.get("BAC_PORT", "8104") or 8104)   # pour renvoyer vers l'écran de connexion
        # 0.4.0 : jeton commun simulé, tiré à chaque démarrage, jamais lu dans l'environnement du conteneur
        self.jeton = secrets.token_urlsafe(32)
        self.port_annuaire = int(getattr(cfg, "port_annuaire", PORT_ANNUAIRE) or PORT_ANNUAIRE)
        self.hote = ""          # hôte vu par le navigateur (dernière adresse publique reçue), pour l'annuaire
        self.remise = False     # 0.4.0 : remise à zéro de la maison en cours (verrou commun)
        self.verrou_maison = asyncio.Lock()
        # mesure de la mémoire, remplaçable dans les essais (règle des 2,4 Go simulable)
        self.mesurer_total = lambda: memoire_mo(os.getpid())
        self.mesurer_appli = memoire_mo

    # ------------------------------------------------------------ chemins
    def dossier(self, ident: str) -> Path:
        return self.cfg.data / "applis" / ident

    def journal_appli(self, ident: str) -> Path:
        return self.dossier(ident) / "journal.jsonl"

    def source(self, ident: str) -> Path:
        return self.cfg.applis / ident / "src"

    def commande(self, a: Appli) -> list[str]:
        dossier = str(self.dossier(a.id) / "donnees")
        valeurs = {"dossier": dossier, "port": str(a.port_local)}
        if a.lanceur == "bac":
            script = self.cfg.lanceurs / f"{a.id.replace('-', '_')}.py"
            return [self.cfg.python, str(script), dossier, str(a.port_local)]
        args = [str(x).format(**valeurs) for x in a.args]
        if a.module.endswith(".py"):
            return [self.cfg.python, a.module, *args]
        return [self.cfg.python, "-m", a.module, *args]

    def ports_permis(self, ident: str) -> list[int]:
        a = self.applis[ident]
        return sorted({a.port_local, self.port_annuaire, *self.liens.ports(ident)})

    def environnement(self, a: Appli, adresse_publique: str = "") -> dict:
        d = self.dossier(a.id)
        valeurs = {"dossier": str(d / "donnees"), "port": str(a.port_local)}
        chemins = [str(self.cfg.garde), str(self.source(a.id)), str(self.cfg.applis / a.id / "site"),
                   str(self.cfg.applis / "_commun")]
        env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": str(d / "maison"),
            "TMPDIR": str(d / "tmp"),
            "LANG": "C.UTF-8",
            "TZ": "Europe/Paris",
            "PYTHONPATH": os.pathsep.join(chemins),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "PLAYWRIGHT_BROWSERS_PATH": str(getattr(self.cfg, "navigateurs", "/ms-playwright")),
            "BAS_APPLI": a.id,
            "BAS_JOURNAL": str(self.journal_appli(a.id)),
            "BAS_SCENARIO": str(d / "scenario.json"),
            "BAS_ADRESSE": adresse_publique,
            "BAS_MOT_DE_PASSE": a.mot_de_passe,
            "BAS_PORTS": ",".join(str(p) for p in self.ports_permis(a.id)),
            # 0.4.0 : jeton commun simulé et faux annuaire de l'Anneau (jamais l'Anneau de la vraie stack)
            "MAISON_JETON": self.jeton,
            "MAISON_ANNEAU_URL": f"http://127.0.0.1:{self.port_annuaire}",
            # Seconde barrière, pour ce qui n'est pas du Python (Chromium de Gazette, outils en ligne de commande) :
            # tout passe par un proxy local qui n'existe pas ; seule la machine elle-même reste joignable.
            "http_proxy": "http://127.0.0.1:9", "https_proxy": "http://127.0.0.1:9", "all_proxy": "http://127.0.0.1:9",
            "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9", "ALL_PROXY": "http://127.0.0.1:9",
            "no_proxy": "localhost,127.0.0.1,::1", "NO_PROXY": "localhost,127.0.0.1,::1",
        }
        env.update(self.liens.variables(a.id))          # 0.4.0 : adresses des applis qu'elle appelle
        for k, v in a.env.items():
            env[k] = str(v).format(**valeurs)
        self.verifier_environnement(a.id, env)
        return env

    def verifier_environnement(self, ident: str, env: dict) -> None:
        """0.4.0 (conseil) : refus de lancer si une adresse vise autre chose que 127.0.0.1, ou si une variable vaut le
        vrai jeton commun de la maison (celui du conteneur, s'il y en a un)."""
        for k, v in env.items():
            if k.upper().endswith("_URL") and k.lower() not in ("http_proxy", "https_proxy", "all_proxy"):
                hote = urlsplit(str(v)).hostname or ""
                if hote != "127.0.0.1":
                    raise RuntimeError(f"{ident} : {k} ne vise pas 127.0.0.1 ({hote or 'vide'}) : lancement refusé.")
        vrais = {os.environ.get(n, "").strip() for n in ("MAISON_JETON", "MAISON_JETON_ANCIEN")} - {""}
        if any(str(v) in vrais for v in env.values()) or self.jeton in vrais:
            raise RuntimeError(f"{ident} : une variable vaut le vrai jeton commun de la maison : lancement refusé.")

    # ------------------------------------------------------------ état
    def etat(self, ident: str) -> dict:
        a, e = self.applis[ident], self.etats[ident]
        vivant = e.vivant()
        return {"id": ident, "nom": a.nom, "version": a.version, "port": a.port, "personnes": a.personnes,
                "etat": "demarree" if vivant else ("erreur" if e.erreur else "arretee"),
                "erreur": e.erreur, "scenario": e.scenario if vivant else None,
                "memoire_mo": round(self.mesurer_appli(e.processus.pid)) if vivant else 0, "memoire_max": a.memoire,
                "depuis": int(time.time() - e.demarre_le) if vivant else 0,
                "inactive_depuis": int(time.time() - e.derniere_requete) if vivant else 0,
                "installee": self.source(ident).is_dir(),
                # 0.4.0
                "branchee": a.branchee, "demo": not a.branchee,
                "lancee_pour": self.applis[e.lancee_pour].nom if vivant and e.lancee_pour in self.applis else "",
                "arret_memoire": (not vivant) and e.arret_memoire,
                "message": f"{a.nom} {MESSAGE_MEMOIRE}." if (not vivant and e.arret_memoire) else "",
                "appelle": [self.applis[c].nom for c in self.liens.cibles(ident)]}

    def toucher(self, ident: str) -> None:
        """0.4.0 : toucher une appli touche aussi celles qu'elle appelle (en cascade), qui ne voient pas passer ces
        requêtes par le relais."""
        maintenant = time.time()
        for x in [ident, *self.liens.cascade(ident)]:
            self.etats[x].derniere_requete = maintenant

    # ------------------------------------------------------------ mémoire
    def memoire_totale(self) -> float:
        return float(self.mesurer_total())

    async def liberer_memoire(self, proteger: set[str]) -> list[str]:
        """Au-delà de la limite, arrête l'appli touchée il y a le plus longtemps, hors `proteger`, jusqu'à repasser
        sous la limite. Rend les applis arrêtées."""
        arretees = []
        limite = float(getattr(self.cfg, "memoire_limite_mo", 2400) or 2400)
        while self.memoire_totale() > limite:
            candidates = [x for x, e in self.etats.items() if e.vivant() and x not in proteger]
            if not candidates:
                journal.warning("mémoire au-delà de %d Mo, mais aucune appli à arrêter", limite)
                break
            vieille = min(candidates, key=lambda x: self.etats[x].derniere_requete)
            journal.warning("mémoire au-delà de %d Mo : %s %s", limite, vieille, MESSAGE_MEMOIRE)
            await self.arreter(vieille)
            self.etats[vieille].arret_memoire = True
            arretees.append(vieille)
        return arretees

    # ------------------------------------------------------------ démarrer / arrêter
    def preparer_dossier(self, ident: str, scenario: dict | None, remettre_a_zero: bool) -> None:
        d = self.dossier(ident)
        if remettre_a_zero and (d / "donnees").exists():
            shutil.rmtree(d / "donnees")
        for sous in ("donnees", "maison", "tmp"):
            (d / sous).mkdir(parents=True, exist_ok=True)
        if scenario is not None:
            (d / "scenario.json").write_text(json.dumps(scenario, ensure_ascii=False, indent=1), encoding="utf-8")
        elif remettre_a_zero:
            (d / "scenario.json").unlink(missing_ok=True)

    def noter_hote(self, adresse_publique: str) -> None:
        hote = urlsplit(adresse_publique or "").hostname
        if hote:
            self.hote = hote

    async def ouvrir(self, ident: str, adresse_publique: str = "", interne: bool = False,
                     scenario: dict | None = None, remettre_a_zero: bool = False) -> dict:
        """0.4.0 : démarre d'abord les applis qu'`ident` appelle (cascade, sans boucle), puis `ident`."""
        if self.remise and not interne:
            raise RuntimeError(REMISE_EN_COURS)
        self.noter_hote(adresse_publique)
        avant = self.liens.cascade(ident)
        proteger = {ident, *avant}
        for dep in avant:
            if not self.etats[dep].vivant():
                await self.demarrer(dep, interne=interne, lancee_pour=ident, proteger=proteger)
        etat = await self.demarrer(ident, scenario=scenario, remettre_a_zero=remettre_a_zero,
                                   adresse_publique=adresse_publique, interne=interne, proteger=proteger)
        self.toucher(ident)
        return etat

    async def demarrer(self, ident: str, scenario: dict | None = None, remettre_a_zero: bool = False,
                       adresse_publique: str = "", interne: bool = False, lancee_pour: str = "",
                       proteger: set[str] | None = None) -> dict:
        if self.bloque:
            raise RuntimeError(self.bloque)
        if self.remise and not interne:
            raise RuntimeError(REMISE_EN_COURS)
        a, e = self.applis[ident], self.etats[ident]
        self.noter_hote(adresse_publique)
        async with e.demarrage:
            if e.vivant() and not remettre_a_zero and scenario is None:
                self.toucher(ident)
                return self.etat(ident)
            await self.arreter(ident)
            if not self.source(ident).is_dir():
                e.erreur = f"{a.nom} n'est pas installée dans cette image."
                raise RuntimeError(e.erreur)
            await self.liberer_memoire((proteger or set()) | {ident})
            self.preparer_dossier(ident, scenario, remettre_a_zero)
            if not adresse_publique and self.hote:
                adresse_publique = f"http://{self.hote}:{a.port}"
            env = self.environnement(a, adresse_publique)
            sortie = open(self.dossier(ident) / "sortie.log", "ab")
            e.erreur = ""
            e.arret_memoire = False
            e.lancee_pour = lancee_pour
            e.processus = subprocess.Popen(self.commande(a), cwd=self.source(ident), env=env,
                                           stdout=sortie, stderr=subprocess.STDOUT, start_new_session=True)
            sortie.close()
            e.demarre_le = e.derniere_requete = time.time()
            e.scenario = (scenario or {}).get("id") if scenario else e.scenario
            if not await self._attendre(a, e):
                fin = self._fin_du_journal(ident)
                await self.arreter(ident)
                e.erreur = f"{a.nom} n'a pas démarré. {fin}".strip()
                raise RuntimeError(e.erreur)
            return self.etat(ident)

    async def _attendre(self, a: Appli, e: Etat) -> bool:
        limite = time.monotonic() + ATTENTE_DEMARRAGE
        async with httpx.AsyncClient(timeout=2) as client:
            while time.monotonic() < limite:
                if not e.vivant():
                    return False
                try:
                    r = await client.get(f"http://127.0.0.1:{a.port_local}/health")
                    if r.status_code < 500:
                        return True
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.5)
        return False

    def _fin_du_journal(self, ident: str, lignes: int = 6) -> str:
        try:
            texte = (self.dossier(ident) / "sortie.log").read_text(errors="replace").strip().splitlines()
            return " / ".join(texte[-lignes:])[-600:]
        except OSError:
            return ""

    async def arreter(self, ident: str) -> None:
        e = self.etats[ident]
        p = e.processus
        if p is None:
            return
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            for _ in range(50):
                if p.poll() is not None:
                    break
                await asyncio.sleep(0.1)
            if p.poll() is None:
                try:
                    os.killpg(p.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                p.wait(timeout=5)
        e.processus = None
        e.lancee_pour = ""

    async def tout_arreter(self) -> None:
        for ident in self.applis:
            await self.arreter(ident)

    async def vider(self, ident: str) -> None:
        await self.arreter(ident)
        shutil.rmtree(self.dossier(ident), ignore_errors=True)
        self.etats[ident].scenario = None
        self.etats[ident].erreur = ""
        self.etats[ident].arret_memoire = False

    @contextlib.asynccontextmanager
    async def remise_a_zero(self):
        """0.4.0 : la maison simulée entière repart de zéro. Pendant ce bloc, aucun démarrage venu d'ailleurs (relais,
        écran, cascade) : seuls ceux marqués `interne` (le reversement du scénario) passent."""
        async with self.verrou_maison:
            self.remise = True
            try:
                await self.tout_arreter()
                for ident in self.applis:
                    await self.vider(ident)
                yield
            finally:
                self.remise = False

    # ------------------------------------------------------------ veille
    async def veiller(self) -> None:
        """Toutes les 20 s : arrêt des applis inactives ; mémoire de la maison au-delà de la limite ; une appli morte
        seule est signalée."""
        while True:
            await asyncio.sleep(20)
            await self.tour_de_veille()

    async def tour_de_veille(self) -> None:
        for ident, e in self.etats.items():
            if e.processus is None:
                continue
            a = self.applis[ident]
            if not e.vivant():
                e.erreur = f"{a.nom} s'est arrêtée seule. {self._fin_du_journal(ident)}".strip()
                e.processus = None
                continue
            if time.time() - e.derniere_requete > self.cfg.arret_minutes * 60:
                journal.info("%s arrêtée : inactive depuis %d min", ident, self.cfg.arret_minutes)
                await self.arreter(ident)
        vivantes = [x for x, e in self.etats.items() if e.vivant()]
        if vivantes and not self.remise:
            recente = max(vivantes, key=lambda x: self.etats[x].derniere_requete)
            await self.liberer_memoire({recente, *self.liens.cascade(recente)})
