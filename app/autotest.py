"""Autotest de coupure, au démarrage du Bac à sable puis à la demande (Réglages).

On lance un petit processus Python exactement comme une appli simulée (même garde, environnement vide) et il essaie
de joindre la maison et Internet. Vert : chaque essai a été refusé par la garde. Rouge : au moins un essai est
passé, et aucune appli ne démarre tant que c'est rouge.

Le conteneur lui-même (le processus du Bac à sable) peut, lui, joindre son réseau : c'est noté pour information
(il en a besoin pour copier de vraies fiches depuis carnet).
"""
from __future__ import annotations

import json
import socket
import subprocess
import sys
from datetime import datetime

CIBLES_DEFAUT = ["anneau:8094", "immich_server:2283", "homeassistant:8123", "carnet:8096", "1.1.1.1:443",
                 "github.com:443"]

SONDE = r"""
import json, socket, sys
res = []
for cible in json.loads(sys.argv[1]):
    hote, _, port = cible.rpartition(":")
    try:
        s = socket.create_connection((hote, int(port)), timeout=3)
        s.close()
        res.append({"cible": cible, "passe": True, "motif": "connexion établie"})
    except OSError as exc:
        garde = "Bac à sable" in str(exc)
        res.append({"cible": cible, "passe": False, "motif": "refusée par la garde" if garde else type(exc).__name__,
                    "garde": garde})
print(json.dumps(res))
"""


def cibles(cfg) -> list[str]:
    return list(dict.fromkeys(CIBLES_DEFAUT + list(cfg.hotes_autotest)))


def essayer_sans_garde(cible: str) -> bool:
    hote, _, port = cible.rpartition(":")
    try:
        socket.create_connection((hote, int(port)), timeout=2).close()
        return True
    except OSError:
        return False


def lancer(cfg) -> dict:
    liste = cibles(cfg)
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONPATH": str(cfg.garde), "LANG": "C.UTF-8",
           "BAS_APPLI": "autotest"}
    try:
        sortie = subprocess.run([cfg.python if cfg.python else sys.executable, "-c", SONDE, json.dumps(liste)],
                                env=env, capture_output=True, text=True, timeout=60, check=True).stdout
        essais = json.loads(sortie.strip().splitlines()[-1])
    except (subprocess.SubprocessError, ValueError, IndexError, OSError) as exc:
        return {"ok": False, "le": datetime.now().astimezone().isoformat(timespec="seconds"),
                "message": f"Autotest impossible ({type(exc).__name__}) : aucune appli simulée ne démarre.",
                "essais": []}
    passes = [e["cible"] for e in essais if e["passe"]]
    for e in essais:
        e["conteneur"] = essayer_sans_garde(e["cible"])      # pour information seulement
    ok = not passes and all(e.get("garde") for e in essais)
    if passes:
        message = "Une appli simulée pourrait joindre : " + ", ".join(passes) + ". Applis bloquées."
    elif not ok:
        message = "La garde n'a pas répondu comme prévu : applis bloquées."
    else:
        message = f"Rien ne sort : {len(essais)} essais, tous refusés par la garde."
    return {"ok": ok, "le": datetime.now().astimezone().isoformat(timespec="seconds"), "message": message,
            "essais": essais}


def verifier_liens(gestionnaire) -> tuple[bool, str]:
    """0.4.0 (conseil) : avant toute appli, on construit l'environnement de chacune comme au lancement et on vérifie
    que ses adresses (`*_URL`) visent toutes 127.0.0.1 et qu'aucune variable ne vaut le vrai jeton commun de la maison
    (le jeton simulé est tiré au hasard à chaque démarrage). Rouge : aucune appli ne démarre."""
    try:
        n = 0
        for a in gestionnaire.applis.values():
            env = gestionnaire.environnement(a)          # lève RuntimeError si une règle est enfreinte
            n += sum(1 for k in env if k.endswith("_URL"))
    except RuntimeError as exc:
        return False, str(exc)
    branches = len(gestionnaire.liens.branches())
    return True, f"{branches} liens branchés entre applis simulées ; {n} adresses, toutes en 127.0.0.1 ; jeton simulé."
