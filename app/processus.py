"""Lancement à la demande des applis simulées.

Chaque appli tourne dans son propre processus Python (toutes s'appellent `app`), avec :
- un environnement construit de zéro (rien n'est hérité du conteneur : ni MAISON_PASSWORD, ni jeton, ni adresse) ;
- PYTHONPATH = la garde (sitecustomize : aucune sortie réseau), son code, son site-packages, les outils communs ;
- son dossier de données propre, <données>/applis/<appli>/ ;
- un port local (port publié + 1000), joint seulement par le relais.

Une appli sans requête depuis `arret_minutes` est arrêtée ; une appli qui dépasse sa mémoire aussi.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import yaml

journal = logging.getLogger("bac-a-sable.processus")
DECALAGE = 1000            # l'appli écoute sur port + DECALAGE, en 127.0.0.1
ATTENTE_DEMARRAGE = 90     # secondes pour répondre à /health


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
    demarrage: asyncio.Lock = field(default_factory=asyncio.Lock)

    def vivant(self) -> bool:
        return self.processus is not None and self.processus.poll() is None


def memoire_mo(pid: int) -> float:
    """Mémoire résidente du processus et de ses enfants (Chromium de Gazette compris), en Mo."""
    total = 0
    pids = [pid]
    try:
        enfants = Path(f"/proc/{pid}/task/{pid}/children").read_text().split()
        pids += [int(e) for e in enfants]
    except OSError:
        pass
    for p in pids:
        try:
            for ligne in Path(f"/proc/{p}/status").read_text().splitlines():
                if ligne.startswith("VmRSS:"):
                    total += int(ligne.split()[1])
        except (OSError, ValueError):
            continue
    return total / 1024


class Gestionnaire:
    def __init__(self, cfg, applis: dict[str, Appli]):
        self.cfg = cfg
        self.applis = applis
        self.etats: dict[str, Etat] = {a: Etat() for a in applis}
        self.bloque = ""        # message de l'autotest quand il a échoué : aucune appli ne démarre
        self.cfg_port_bac = int(os.environ.get("BAC_PORT", "8104") or 8104)   # pour renvoyer vers l'écran de connexion

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
            "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",
            "BAS_APPLI": a.id,
            "BAS_JOURNAL": str(self.journal_appli(a.id)),
            "BAS_SCENARIO": str(d / "scenario.json"),
            "BAS_ADRESSE": adresse_publique,
            "BAS_MOT_DE_PASSE": a.mot_de_passe,
            # Seconde barrière, pour ce qui n'est pas du Python (Chromium de Gazette, outils en ligne de commande) :
            # tout passe par un proxy local qui n'existe pas ; seule la machine elle-même reste joignable.
            "http_proxy": "http://127.0.0.1:9", "https_proxy": "http://127.0.0.1:9", "all_proxy": "http://127.0.0.1:9",
            "HTTP_PROXY": "http://127.0.0.1:9", "HTTPS_PROXY": "http://127.0.0.1:9", "ALL_PROXY": "http://127.0.0.1:9",
            "no_proxy": "localhost,127.0.0.1,::1", "NO_PROXY": "localhost,127.0.0.1,::1",
        }
        for k, v in a.env.items():
            env[k] = str(v).format(**valeurs)
        return env

    # ------------------------------------------------------------ état
    def etat(self, ident: str) -> dict:
        a, e = self.applis[ident], self.etats[ident]
        vivant = e.vivant()
        return {"id": ident, "nom": a.nom, "version": a.version, "port": a.port, "personnes": a.personnes,
                "etat": "demarree" if vivant else ("erreur" if e.erreur else "arretee"),
                "erreur": e.erreur, "scenario": e.scenario if vivant else None,
                "memoire_mo": round(memoire_mo(e.processus.pid)) if vivant else 0, "memoire_max": a.memoire,
                "depuis": int(time.time() - e.demarre_le) if vivant else 0,
                "inactive_depuis": int(time.time() - e.derniere_requete) if vivant else 0,
                "installee": self.source(ident).is_dir()}

    def toucher(self, ident: str) -> None:
        self.etats[ident].derniere_requete = time.time()

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

    async def demarrer(self, ident: str, scenario: dict | None = None, remettre_a_zero: bool = False,
                       adresse_publique: str = "") -> dict:
        if self.bloque:
            raise RuntimeError(self.bloque)
        a, e = self.applis[ident], self.etats[ident]
        async with e.demarrage:
            if e.vivant() and not remettre_a_zero and scenario is None:
                self.toucher(ident)
                return self.etat(ident)
            await self.arreter(ident)
            if not self.source(ident).is_dir():
                e.erreur = f"{a.nom} n'est pas installée dans cette image."
                raise RuntimeError(e.erreur)
            vivantes = [x for x, s in self.etats.items() if s.vivant() and x != ident]
            if len(vivantes) >= self.cfg.max_simultanees:
                plus_vieille = min(vivantes, key=lambda x: self.etats[x].derniere_requete)
                journal.info("trop d'applis lancées : %s est arrêtée pour faire place à %s", plus_vieille, ident)
                await self.arreter(plus_vieille)
            self.preparer_dossier(ident, scenario, remettre_a_zero)
            sortie = open(self.dossier(ident) / "sortie.log", "ab")
            e.erreur = ""
            e.processus = subprocess.Popen(self.commande(a), cwd=self.source(ident),
                                           env=self.environnement(a, adresse_publique),
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

    async def tout_arreter(self) -> None:
        for ident in self.applis:
            await self.arreter(ident)

    async def vider(self, ident: str) -> None:
        await self.arreter(ident)
        shutil.rmtree(self.dossier(ident), ignore_errors=True)
        self.etats[ident].scenario = None
        self.etats[ident].erreur = ""

    # ------------------------------------------------------------ veille
    async def veiller(self) -> None:
        """Toutes les 20 s : arrêt des applis inactives ou trop gourmandes ; une appli morte seule est signalée."""
        while True:
            await asyncio.sleep(20)
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
                elif memoire_mo(e.processus.pid) > a.memoire:
                    await self.arreter(ident)
                    e.erreur = f"{a.nom} arrêtée : plus de {a.memoire} Mo de mémoire."
