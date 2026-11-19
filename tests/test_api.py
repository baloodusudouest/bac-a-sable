"""API du Bac à sable, sans réseau et sans lancer d'appli."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from app import base, main
from tests.test_personnes import faux_carnet


def test_connexion_obligatoire(client):
    client.post("/api/deconnexion")
    assert client.get("/api/applis").status_code == 401
    assert client.get("/api/session").json()["connecte"] is False


def test_sante_ne_donne_que_des_nombres(client):
    client.post("/api/personnes/pieges")
    sante = client.get("/health").json()
    assert sante["ok"] and sante["personnes"] == 11 and sante["applis_lancees"] == 0
    assert "Marie" not in str(sante)


def test_autotest_vert_sans_reseau(client):
    r = client.post("/api/autotest").json()
    assert r["ok"], r
    assert r["essais"] and all(e["garde"] and not e["passe"] for e in r["essais"])
    assert main.ETAT["gestionnaire"].bloque == ""


def test_autotest_rouge_bloque_les_applis(client, monkeypatch):
    monkeypatch.setattr(main.autotest, "lancer", lambda cfg: {"ok": False, "message": "fuite", "essais": []})
    main.ETAT["cfg"] = main.ETAT["cfg"].__class__(**{**main.ETAT["cfg"].__dict__, "autotest": True})
    client.post("/api/autotest")
    r = client.post("/api/applis/douze-points/demarrer")
    assert r.status_code == 409 and "fuite" in r.json()["detail"]


def test_douze_applis_au_catalogue(client):
    applis = client.get("/api/applis").json()["applis"]
    assert len(applis) == 12
    ports = sorted(a["port"] for a in applis)
    assert ports == list(range(8110, 8122))
    assert all(a["adresse"].endswith(f":{a['port']}") for a in applis)


def test_inventer_puis_liens_en_identifiants(client):
    ids = client.post("/api/personnes/inventer", json={"nombre": 20, "graine": 3, "variete": 90}).json()["ajoutees"]
    gens = {p["id"]: p for p in client.get("/api/personnes").json()["personnes"]}
    assert set(ids) == set(gens)
    for p in gens.values():
        for lien in p["liens"]:
            assert lien["vers"] in gens


def test_copie_de_vraies_fiches_puis_effacement_pour_de_bon(client, monkeypatch):
    t, _ = faux_carnet([{"carnet_id": "C9", "prenom": "Odile", "nom_carnet": "Odile Unique", "naissance": "1970-01-02"}])
    main.ETAT["transport_carnet"] = t
    main.ETAT["cfg"] = main.ETAT["cfg"].__class__(**{**main.ETAT["cfg"].__dict__, "carnet_url": "http://c", "carnet_jeton": "j"})
    assert client.get("/api/carnet/personnes", params={"q": "odi"}).json()["fiches"][0]["copiee"] is False
    ids = client.post("/api/personnes/copier", json={"carnet_ids": ["C9"]}).json()["ajoutees"]
    assert len(ids) == 1
    assert client.post("/api/personnes/copier", json={"carnet_ids": ["C9"]}).json()["ajoutees"] == []   # pas deux fois
    assert client.put(f"/api/personnes/{ids[0]}", json={"prenom": "Autre"}).status_code == 409
    client.post("/api/personnes/effacer", json={"origine": "reelle"})
    donnees = main.ETAT["cfg"].data / "bac-a-sable.db"
    assert b"Unique" not in donnees.read_bytes()       # secure_delete + VACUUM : plus aucune trace dans le fichier


def test_copies_perimees_apres_30_jours_sauf_epinglees(client):
    data = main.ETAT["cfg"].data
    with base.base(data) as cx:
        vieux = (datetime.now().astimezone() - timedelta(days=31)).isoformat(timespec="seconds")
        a = base.ajouter_personne(cx, "reelle", {"prenom": "A"}, "X1")
        b = base.ajouter_personne(cx, "reelle", {"prenom": "B"}, "X2")
        c = base.ajouter_personne(cx, "reelle", {"prenom": "C"}, "X3")
        d = base.ajouter_personne(cx, "inventee", {"prenom": "D"})
        cx.execute("UPDATE personne SET cree_le=?", (vieux,))
        cx.execute("UPDATE personne SET epinglee=1 WHERE id=?", (b,))
        base.ecrire_scenario(cx, {"nom": "gardé", "applis": ["carnet"], "personnes": [c], "epingle": True})
        assert base.copies_perimees(cx, 30) == [a]
        assert d not in base.copies_perimees(cx, 30)


def test_scenario_complet(client):
    ids = client.post("/api/personnes/inventer", json={"nombre": 4, "graine": 1}).json()["ajoutees"]
    assert client.post("/api/scenarios", json={"nom": "", "applis": ["carnet"]}).status_code == 422
    assert client.post("/api/scenarios", json={"nom": "x", "applis": ["inconnue"]}).status_code == 422
    sid = client.post("/api/scenarios", json={"nom": "Famille", "applis": ["carnet", "douze-points"],
                                              "personnes": ids}).json()["id"]
    copie = client.post(f"/api/scenarios/{sid}/dupliquer").json()["id"]
    noms = [s["nom"] for s in client.get("/api/scenarios").json()["scenarios"]]
    assert noms == ["Famille (copie)", "Famille"]
    assert client.post(f"/api/scenarios/{sid}/jouer", json={"appli": "gazette"}).status_code == 422
    client.post("/api/personnes/effacer", json={"ids": ids[:2]})
    s = client.put(f"/api/scenarios/{sid}", json={"epingle": True}).json()
    assert s["personnes"] == ids[2:] and s["epingle"]
    client.delete(f"/api/scenarios/{copie}")
    assert len(client.get("/api/scenarios").json()["scenarios"]) == 1


def test_appli_non_installee(client, tmp_path):
    import dataclasses
    g = main.ETAT["gestionnaire"]
    g.cfg = dataclasses.replace(g.cfg, applis=tmp_path / "aucune-appli")      # dans l'image, toutes sont installées
    r = client.post("/api/applis/gazette/demarrer")
    assert r.status_code == 409 and "pas installée" in r.json()["detail"]


def test_journal_vide_puis_lu(client):
    g = main.ETAT["gestionnaire"]
    chemin = g.journal_appli("carnet")
    chemin.parent.mkdir(parents=True)
    chemin.write_text('{"quand":"2026-11-19T10:00:00","appli":"carnet","sorte":"ecriture","service":"icloud","action":"PUT /x"}\n'
                      '{"quand":"2026-11-19T10:00:01","appli":"carnet","sorte":"demarrage"}\n'
                      'pas du json\n')
    j = client.get("/api/journal").json()
    assert j["compte"]["ecriture"] == 1 and len(j["lignes"]) == 1


def test_erreurs_de_l_appli_lisibles(client):
    """0.1.4 : la fin du journal du processus simulé, avec le nombre d'erreurs Python."""
    g = main.ETAT["gestionnaire"]
    assert client.get("/api/applis/douze-points/sortie").json() == {"appli": "douze-points", "lignes": [], "total": 0, "erreurs": 0}
    d = g.dossier("douze-points")
    d.mkdir(parents=True)
    (d / "sortie.log").write_text("démarrage\nERROR:    Exception in ASGI application\nTraceback (most recent call last):\n"
                                  "sqlite3.OperationalError: database is locked\n", encoding="utf-8")
    r = client.get("/api/applis/douze-points/sortie").json()
    assert r["erreurs"] == 2 and r["lignes"][-1].endswith("database is locked")
    assert client.get("/api/applis/inconnue/sortie").status_code == 404
