"""Bout en bout : de vraies applis lancées dans des processus, derrière le relais.

Demande BAC_ESSAI_APPLIS (dossier <appli>/src et <appli>/site, comme /applis dans l'image) ; sautés sinon.
La CI les lance dans l'image construite (voir .github/workflows/tests.yml).
"""
from __future__ import annotations

import asyncio
import os

import httpx
import pytest

from app import main

pytestmark = pytest.mark.skipif(not os.environ.get("BAC_ESSAI_APPLIS"), reason="applis embarquées absentes")
ANNUAIRE = True       # 0.4.0 : le faux annuaire de l'Anneau écoute (conftest)


def installee(ident: str) -> bool:
    return os.path.isdir(os.path.join(os.environ.get("BAC_ESSAI_APPLIS", ""), ident, "src"))


async def par_le_relais(ident: str, methode: str, chemin: str, cookies: dict | None = None, **kw) -> httpx.Response:
    relais = main.ETAT["relais"][ident]
    transport = httpx.ASGITransport(app=relais)
    async with httpx.AsyncClient(transport=transport, base_url=f"http://192.0.2.50:{relais.appli.port}",
                                 cookies=cookies or {}) as c:
        return await c.request(methode, chemin, **kw)


def cookies_du_bac(client) -> dict:
    return {k: v for k, v in client.cookies.items()}


@pytest.mark.skipif(not installee("douze-points"), reason="Douze points absent")
def test_soiree_douze_points_complete(client):
    ids = client.post("/api/personnes/inventer", json={"nombre": 5, "graine": 9}).json()["ajoutees"]
    client.post("/api/personnes/pieges")
    sid = client.post("/api/scenarios", json={"nom": "Soirée", "applis": ["douze-points"], "personnes": ids,
                                              "reglages": {"douze-points": {"telephones": 4, "chansons": 6}}}).json()["id"]
    r = client.post(f"/api/scenarios/{sid}/jouer", json={"appli": "douze-points"})
    assert r.status_code == 200, r.text
    soiree = r.json()["soiree"]
    assert len(soiree["telephones"]) == 4 and len(soiree["libres"]) == 1 and soiree["chansons"] == 6
    client.post("/api/douze/jouer", json={"avance_rapide": True})
    for _ in range(100):
        etat = client.get("/api/douze").json()
        if not etat["en_cours"]:
            break
        asyncio.run(asyncio.sleep(0.1))
    assert [t["etat"] for t in etat["telephones"]] == ["envoyé"] * 4, etat
    assert all(t["notees"] == 6 and t["jeton"] for t in etat["telephones"])
    assert etat["lien_invites"].endswith("/invite/" + etat["jeton_invite"])
    assert client.get("/api/douze/qr.svg").headers["content-type"].startswith("image/svg")

    # la régie (hôte) voit 4 envois sur 5 ; le 5e prénom attend un vrai iPhone
    detail = asyncio.run(par_le_relais("douze-points", "GET", f"/api/soirees/{soiree['soiree_id']}",
                                       cookies=cookies_du_bac(client))).json()
    assert sorted(p["etat"] for p in detail["participants"]) == ["attendu"] + ["envoye"] * 4
    # un vrai téléphone, sans connexion au Bac à sable, passe par la porte invité
    porte = asyncio.run(par_le_relais("douze-points", "GET", f"/invite/{etat['jeton_invite']}/api/etat"))
    assert porte.status_code == 200 and porte.json()["etat"] == "ouverte"
    # 0.1.3 : Douze points a son faux Immich, l'icône 📷 et « Immortaliser » paraissent sur les téléphones
    assert porte.json()["photos"]["actives"] is True
    client.post("/api/applis/douze-points/arreter")


@pytest.mark.skipif(not installee("douze-points"), reason="Douze points absent")
def test_relais_garde_les_cookies(client):
    client.post("/api/applis/douze-points/demarrer")
    # sans connexion au Bac à sable : refus (sauf porte invité)
    assert asyncio.run(par_le_relais("douze-points", "GET", "/api/soirees")).status_code == 401
    vrais = {**cookies_du_bac(client), "maison_session": "VRAI-COOKIE", "carnet_session": "AUTRE"}
    r = asyncio.run(par_le_relais("douze-points", "GET", "/api/soirees", cookies=vrais))
    assert r.status_code == 200, r.text
    assert "set-cookie" not in r.headers                 # rien n'est posé sur le navigateur
    # la connexion de l'appli simulée est faite par le relais, son cookie reste chez lui
    assert "douze-points_session" in main.ETAT["relais"]["douze-points"].session
    # « Se déconnecter » dans l'appli simulée ne touche pas aux cookies du navigateur
    r = asyncio.run(par_le_relais("douze-points", "POST", "/api/deconnexion", cookies=vrais))
    assert "set-cookie" not in r.headers
    # et la requête suivante se reconnecte seule
    assert asyncio.run(par_le_relais("douze-points", "GET", "/api/soirees", cookies=vrais)).status_code == 200
    # 0.1.5 : depuis une page invité (/invite/…), Douze points ne voit pas l'hôte : pas de boutons Revenir / Suivant
    hote = asyncio.run(par_le_relais("douze-points", "GET", "/api/session", cookies=vrais)).json()
    invite = asyncio.run(par_le_relais("douze-points", "GET", "/api/session", cookies=vrais,
                                       headers={"referer": "http://192.0.2.50:8114/invite/abc"})).json()
    assert hote["connecte"] is True and invite["connecte"] is False
    client.post("/api/applis/douze-points/arreter")


@pytest.mark.skipif(not installee("carnet"), reason="carnet absent")
def test_carnet_avec_les_personnes_du_scenario(client):
    ids = client.post("/api/personnes/inventer", json={"nombre": 12, "graine": 5, "variete": 90}).json()["ajoutees"]
    pieges = client.post("/api/personnes/pieges").json()["ajoutees"]
    sid = client.post("/api/scenarios", json={"nom": "Contacts", "applis": ["carnet"],
                                              "personnes": ids + pieges}).json()["id"]
    r = client.post(f"/api/scenarios/{sid}/jouer", json={"appli": "carnet"})
    assert r.status_code == 200, r.text
    contacts = asyncio.run(par_le_relais("carnet", "GET", "/api/contacts", cookies=cookies_du_bac(client)))
    assert contacts.status_code == 200, contacts.text
    texte = contacts.text.casefold()          # carnet écrit les noms de famille en capitales
    assert "vandenbroucke" in texte and "ågren" in texte
    gens = {p["id"]: p for p in client.get("/api/personnes").json()["personnes"]}
    assert all(gens[i]["nom"].casefold() in texte for i in ids if gens[i]["nom"])
    assert len(contacts.json()) == len(ids) + len(pieges)
    page = asyncio.run(par_le_relais("carnet", "GET", "/", cookies=cookies_du_bac(client)))
    # l'interface n'est pas bâtie hors de l'image : on vérifie seulement que la réponse passe le relais
    assert page.status_code in (200, 404)
    # rien n'est sorti : le journal n'a aucune sortie refusée vers un vrai service pendant la lecture
    journal = client.get("/api/journal", params={"appli": "carnet"}).json()
    assert all(x["sorte"] != "sortie_refusee" or x["vers"].startswith("127.") for x in journal["lignes"])
    client.post("/api/applis/carnet/vider")
    assert not main.ETAT["gestionnaire"].dossier("carnet").exists()


TOUTES = ["anneau", "carnet", "chambre-noire", "comptoir", "douze-points", "gazette", "kit-urgence", "millesime",
          "scriptorium", "sillage", "transhumance", "ephemeride"]


@pytest.mark.parametrize("ident", TOUTES)
def test_chaque_appli_demarre_et_s_ouvre_par_le_relais(client, ident):
    """Test de fumée de l'image : chaque appli embarquée démarre, et le relais s'y connecte seul."""
    if not installee(ident):
        pytest.skip(f"{ident} absente")
    r = client.post(f"/api/applis/{ident}/demarrer")
    assert r.status_code == 200, r.text
    session = asyncio.run(par_le_relais(ident, "GET", "/api/session", cookies=cookies_du_bac(client)))
    assert session.status_code == 200 and session.json().get("connecte") is True, session.text
    page = asyncio.run(par_le_relais(ident, "GET", "/", cookies=cookies_du_bac(client)))
    if page.status_code == 200 and "text/html" in page.headers.get("content-type", ""):
        assert "bac-a-sable-bandeau" in page.text               # le bandeau
        assert "bac-a-sable-filigrane" in page.text             # le filigrane (0.1.2)
    journal = client.get("/api/journal", params={"appli": ident}).json()["lignes"]
    fuites = [x for x in journal if x["sorte"] == "sortie_refusee"]
    client.post(f"/api/applis/{ident}/arreter")
    # une sortie refusée n'est pas une fuite (la garde a tenu), mais on la veut visible dans le rapport
    print(ident, "sorties refusées :", [x.get("vers") for x in fuites])
