"""Fiches « Connexion » communes (contrat 3, socle 0.11.0) : forme de /api/maison/services, accès par session ou
ANNEAU_CLE seulement (jamais MAISON_JETON), « Vérifier » d'un service pas relié n'essaie rien, copies non retouchées
du module commun et de l'interface commune."""
from pathlib import Path

from app import maison
from app.config import APPLI
import pytest
from fastapi.testclient import TestClient

from app import main
from tests.conftest import MOT_DE_PASSE, config


@pytest.fixture()
def nu(tmp_path):
    """Le Bac à sable sans session (la fixture « client » des autres tests est déjà connectée)."""
    main.ETAT.clear()
    main.ETAT["cfg"] = config(tmp_path)
    with TestClient(main.app) as c:
        yield c
    main.ETAT.clear()


def connecter(c):
    if not main.ETAT["sessions"].connecte(c.cookies):
        assert c.post("/api/connexion", json={"mot_de_passe": MOT_DE_PASSE}).status_code == 200

RACINE = Path(__file__).resolve().parent.parent
CLE = "cle-anneau-de-test-1234567890"
IDS = ["carnet"]
CHAMPS = {"id", "nom", "genre", "cible", "etat", "lit", "ecrit", "reglage", "detail", "verifie_le", "guide",
          "derniere_ecriture", "gestes"}


def test_forme_du_contrat_3(client):
    connecter(client)
    r = client.get("/api/maison/services")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    corps = r.json()
    assert corps["contrat"] == 3 and corps["appli"] == APPLI and corps["simule"] is True
    assert [s["id"] for s in corps["services"]] == IDS
    for s in corps["services"]:
        assert set(s) == CHAMPS and s["lit"] and s["ecrit"] and s["etat"] in maison.ETATS_SERVICE
        assert len(s["gestes"]) <= 1
        if s["etat"] == "pas_relie":
            assert s["reglage"]


def test_acces_session_ou_cle_anneau(nu, monkeypatch):
    client = nu
    assert client.get("/api/maison/services").status_code == 401
    monkeypatch.setenv("MAISON_JETON", "jeton-commun-de-test-12345")
    entete = {"Authorization": "Bearer jeton-commun-de-test-12345"}
    assert client.get("/api/maison/services", headers=entete).status_code == 401
    monkeypatch.setenv("ANNEAU_CLE", CLE)
    assert client.get("/api/maison/services", headers={"Authorization": f"Bearer {CLE}"}).status_code == 200
    assert client.get("/api/maison/services", headers={"Authorization": "Bearer mauvaise"}).status_code == 401


def test_verifier_inconnu_et_pas_relie(client):
    connecter(client)
    assert client.post("/api/maison/services/inconnu/verifier").status_code == 404
    for s in client.get("/api/maison/services").json()["services"]:
        if s["etat"] == "pas_relie":
            apres = client.post(f"/api/maison/services/{s['id']}/verifier").json()
            assert apres["etat"] == "pas_relie" and apres["verifie_le"] is None


def test_copies_communes_non_retouchees():
    assert maison.CONTRAT == 3 and maison.VERSION_SOCLE == "0.11.0"
    assert maison.empreinte_calculee() == maison.empreinte_ecrite()
    for nom in maison.FICHIERS_INTERFACE:
        ecrite, calculee = maison.empreinte_interface(RACINE / "frontend" / "src" / "lib" / "services" / nom)
        assert ecrite and ecrite == calculee, nom


def test_carnet_relie_essai_en_lecture(tmp_path):
    """0.2.0 : avec BAC_CARNET_URL et le jeton, « Vérifier » relit les fiches de carnet (un GET), sans rien écrire."""
    import httpx
    vus = []

    def repondre(req: httpx.Request) -> httpx.Response:
        vus.append((req.method, req.url.path))
        return httpx.Response(200, json={"personnes": [{"carnet_id": "1", "prenom": "Ada", "nom": "Ada L"}]})

    main.ETAT.clear()
    main.ETAT["cfg"] = config(tmp_path, carnet_url="http://carnet.essai", carnet_jeton="jeton-de-test-123456")
    main.ETAT["transport_carnet"] = httpx.MockTransport(repondre)
    with TestClient(main.app) as c:
        connecter(c)
        (fiche,) = c.get("/api/maison/services").json()["services"]
        assert fiche["etat"] == "relie" and fiche["cible"] == "carnet" and fiche["genre"] == "maison"
        apres = c.post("/api/maison/services/carnet/verifier").json()
        assert apres["etat"] == "repond" and "1 fiches" in apres["detail"]
    assert vus == [("GET", "/gazette/personnes")]
    main.ETAT.clear()
