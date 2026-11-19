"""Garde du Bac à sable, chargée d'office par Python dans chaque appli simulée (dossier mis dans PYTHONPATH).

1. Coupure : toute connexion réseau vers autre chose que la machine elle-même (127.0.0.0/8, ::1, fichiers
   Unix) est refusée, et aucun nom autre que « localhost » n'est résolu (pas même une requête DNS).
   Une appli simulée ne peut donc joindre ni le NAS, ni Immich, ni Home Assistant, ni Internet, quelle que soit
   la bibliothèque (httpx, requests, urllib, telethon…). Chaque refus est noté dans le journal.
2. Journal : chaque écriture reçue par un faux service (httpx.MockTransport des démonstrations, ou faux
   serveur local) est notée : « carnet aurait écrit dans … ».

Le journal est un fichier JSON Lines (une ligne par évènement) dont le chemin est dans BAS_JOURNAL.
Ce fichier ne doit rien importer de l'appli : il tourne avant elle.
"""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import threading
import time

_APPLI = os.environ.get("BAS_APPLI", "?")
_JOURNAL = os.environ.get("BAS_JOURNAL", "")
_VERROU = threading.Lock()
_ECRITURES = {"POST", "PUT", "PATCH", "DELETE"}


def noter(sorte: str, **champs) -> None:
    """Une ligne au journal ; ne lève jamais (la garde ne doit pas casser l'appli)."""
    if not _JOURNAL:
        return
    ligne = {"quand": time.strftime("%Y-%m-%dT%H:%M:%S"), "appli": _APPLI, "sorte": sorte, **champs}
    try:
        with _VERROU, open(_JOURNAL, "a", encoding="utf-8") as f:
            f.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    except OSError:
        pass


class SortieRefusee(ConnectionRefusedError):
    """Le Bac à sable refuse toute sortie : l'appli simulée n'a que de faux services."""


def _locale(hote) -> bool:
    if hote is None:
        return False
    if isinstance(hote, bytes):
        hote = hote.decode(errors="replace")
    hote = str(hote).strip("[]").lower()
    if hote in ("localhost", "localhost.localdomain", ""):
        return hote != ""
    try:
        return ipaddress.ip_address(hote.split("%")[0]).is_loopback
    except ValueError:
        return False


def _verifier(adresse, famille) -> None:
    if famille == getattr(socket, "AF_UNIX", object()):
        return
    hote = adresse[0] if isinstance(adresse, tuple) and adresse else adresse
    if not _locale(hote):
        noter("sortie_refusee", vers=str(hote))
        raise SortieRefusee(f"Bac à sable : sortie vers {hote} refusée (rien ne sort).")


_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex
_getaddrinfo = socket.getaddrinfo
_gethostbyname = socket.gethostbyname


def _connect_garde(self, adresse):
    _verifier(adresse, self.family)
    return _connect(self, adresse)


def _connect_ex_garde(self, adresse):
    _verifier(adresse, self.family)
    return _connect_ex(self, adresse)


def _est_adresse(hote) -> bool:
    try:
        ipaddress.ip_address(str(hote.decode() if isinstance(hote, bytes) else hote).strip("[]").split("%")[0])
        return True
    except ValueError:
        return False


def _getaddrinfo_garde(hote, *args, **kw):
    if hote is not None and not _locale(hote) and _est_adresse(hote):
        noter("sortie_refusee", vers=str(hote))
        raise SortieRefusee(f"Bac à sable : sortie vers {hote} refusée (rien ne sort).")
    if hote is not None and not _locale(hote):
        noter("nom_refuse", nom=str(hote))
        raise socket.gaierror(socket.EAI_NONAME, f"Bac à sable : nom {hote} non résolu (rien ne sort).")
    return _getaddrinfo(hote, *args, **kw)


def _gethostbyname_garde(hote):
    if not _locale(hote):
        noter("nom_refuse", nom=str(hote))
        raise socket.gaierror(socket.EAI_NONAME, f"Bac à sable : nom {hote} non résolu (rien ne sort).")
    return _gethostbyname(hote)


socket.socket.connect = _connect_garde
socket.socket.connect_ex = _connect_ex_garde
socket.getaddrinfo = _getaddrinfo_garde
socket.gethostbyname = _gethostbyname_garde


# ------------------------------------------------------------------ journal des écritures

def _brancher_httpx() -> None:
    """httpx.MockTransport : les faux services des démonstrations. Chaque écriture y est notée."""
    try:
        import httpx
    except Exception:  # noqa: BLE001 — appli sans httpx
        return
    for nom in ("handle_request", "handle_async_request"):
        origine = getattr(httpx.MockTransport, nom, None)
        if origine is None or getattr(origine, "_bac", False):
            continue

        def enveloppe(self, requete, _origine=origine):
            if requete.method in _ECRITURES:
                noter("ecriture", service=requete.url.host or "?", action=f"{requete.method} {requete.url.path}",
                      taille=len(requete.content or b"") if hasattr(requete, "content") else None)
            return _origine(self, requete)

        enveloppe._bac = True
        setattr(httpx.MockTransport, nom, enveloppe)


def _brancher_http_client() -> None:
    """requests et urllib passent par http.client : les faux serveurs locaux (Millésime, Éphéméride)."""
    import http.client
    origine = http.client.HTTPConnection.request
    if getattr(origine, "_bac", False):
        return

    def request(self, methode, url, *args, **kw):
        if str(methode).upper() in _ECRITURES:
            noter("ecriture", service=f"{self.host}:{self.port}", action=f"{methode} {str(url).split('?')[0]}")
        return origine(self, methode, url, *args, **kw)

    request._bac = True
    http.client.HTTPConnection.request = request


class _Crochet:
    """Branche le journal httpx juste après que l'appli a importé httpx (sans l'importer nous-mêmes trop tôt) :
    on trouve le vrai paquet, et on enveloppe son chargeur pour brancher le journal une fois le module exécuté."""

    def find_spec(self, nom, chemin=None, cible=None):
        if nom != "httpx":
            return None
        import importlib.machinery
        import sys
        sys.meta_path.remove(self)
        spec = importlib.machinery.PathFinder.find_spec(nom, chemin)
        if spec is None or spec.loader is None:
            return spec
        executer = spec.loader.exec_module

        def exec_module(module, _executer=executer):
            _executer(module)
            _brancher_httpx()

        spec.loader.exec_module = exec_module
        return spec


try:
    import importlib.util  # noqa: F401
    import sys as _sys
    _brancher_http_client()
    if "httpx" in _sys.modules:
        _brancher_httpx()
    else:
        _sys.meta_path.insert(0, _Crochet())
except Exception:  # noqa: BLE001 — la garde réseau reste en place même si le journal échoue
    pass

noter("demarrage")
