"""0.4.0 — liens entre applis simulées, sans lancer d'appli : table `liens:` face à la copie figée des flux du coffre,
cascade sans boucle, adresses et ports permis, jeton simulé, activité propagée, règle de mémoire de toute la maison,
message « arrêtée pour libérer la mémoire », verrou de la remise à zéro, badge « encore en démo », liste blanche de
la Gazette."""
from __future__ import annotations

import asyncio
import importlib.util
import subprocess
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from app import liens as L
from app import main
from app.processus import MESSAGE_MEMOIRE, REMISE_EN_COURS, Appli, Gestionnaire, catalogue

from .conftest import RACINE, config

CATALOGUE = RACINE / "applis.yaml"
FLUX = RACINE / "docs" / "flux-maison.json"


def gestionnaire(tmp_path, **kw) -> Gestionnaire:
    return Gestionnaire(config(tmp_path, **kw), catalogue(CATALOGUE), L.charger(CATALOGUE))


def lanceur_gazette():
    spec = importlib.util.spec_from_file_location("lanceur_gazette", RACINE / "lanceurs" / "gazette.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------------ table liens: et copie figée

def test_table_des_liens_egale_la_copie_figee_des_flux_du_coffre():
    applis = catalogue(CATALOGUE)
    ecart = L.comparer(L.charger(CATALOGUE), L.flux_figes(FLUX), applis)
    assert ecart == {"manquants": [], "en_trop": []}
    assert len(L.flux_figes(FLUX)) == 32                       # le coffre en compte 32 (20/11/2026)


def test_copie_figee_sans_adresse_ni_valeur():
    """Dépôt public : la copie ne garde que de, vers, nature."""
    texte = FLUX.read_text(encoding="utf-8")
    assert "http" not in texte and "jeton" not in texte.lower() and "192.168." not in texte
    assert all(set(f) == {"de", "vers", "nature"} for f in L.flux_figes(FLUX))


def test_liens_branches_et_flux_sans_lanceur_signales():
    applis = catalogue(CATALOGUE)
    liens = L.Liens(L.charger(CATALOGUE), applis)
    branches = {(x.de, x.vers) for x in liens.branches()}
    assert branches == {("carnet", "douze-points"), ("carnet", "gazette"), ("douze-points", "carnet"),
                        ("douze-points", "gazette"), ("gazette", "carnet")}
    coupes = [x for x in liens.etat() if not x["branche"] and x["portee"] == "simule"]
    # chaque flux entre applis dont un bout n'a pas encore de lanceur est signalé, avec son motif
    assert coupes and all("encore en démo" in x["motif"] for x in coupes if x["de"] != "carnet" or x["vers"] != "kit-urgence")
    assert any(x["de"] == "sillage" and x["vers"] == "gazette" and "Sillage encore en démo" in x["motif"] for x in coupes)
    print("flux sans lanceur :", [(x["de"], x["vers"], x["motif"]) for x in coupes])


# ------------------------------------------------------------------ cascade, adresses, ports

def test_cascade_lectures_et_ecritures_sans_boucle():
    applis = catalogue(CATALOGUE)
    liens = L.Liens(L.charger(CATALOGUE), applis)
    assert liens.cascade("gazette") == ["carnet", "douze-points"]       # lit carnet et Douze points, écrit à carnet
    assert liens.cascade("douze-points") == ["carnet"]                  # la clôture écrit à carnet
    assert liens.cascade("carnet") == []
    assert liens.cascade("sillage") == []                               # encore en démo : liens coupés
    # une boucle (A lit B, B écrit à A) : chacun démarre l'autre une fois, jamais sans fin
    deux = {"a": replace(applis["carnet"], id="a"), "b": replace(applis["gazette"], id="b"),
            "c": replace(applis["douze-points"], id="c")}
    boucle = L.Liens([L.Lien("b", "a", "donnees", appelant="a", variable="A_B_URL"),
                      L.Lien("a", "b", "donnees", appelant="b", variable="B_A_URL"),
                      L.Lien("c", "b", "donnees", appelant="b", variable="B_C_URL")], deux)
    assert boucle.cascade("a") == ["c", "b"]
    assert boucle.cascade("b") == ["a", "c"]


def test_variables_ports_et_jeton_par_appli(tmp_path, monkeypatch):
    monkeypatch.setenv("MAISON_JETON", "le-vrai-jeton-de-la-maison")
    g = gestionnaire(tmp_path)
    env = g.environnement(g.applis["gazette"])
    assert env["GAZETTE_CARNET_URL"] == "http://127.0.0.1:9111"
    assert env["GAZETTE_DOUZE_POINTS_URL"] == "http://127.0.0.1:9114"
    assert "GAZETTE_SILLAGE_URL" not in env                              # Sillage encore en démo : lien coupé
    assert env["MAISON_ANNEAU_URL"] == f"http://127.0.0.1:{g.port_annuaire}"
    ports = {int(x) for x in env["BAS_PORTS"].split(",")}
    assert ports == {9115, 9111, 9114, g.port_annuaire}
    assert not ports & {8104, 9113, 8111, 8114}                           # ni le Bac à sable, ni Comptoir, ni les relais
    assert env["MAISON_JETON"] == g.jeton != "le-vrai-jeton-de-la-maison"
    assert len(g.jeton) >= 32 and gestionnaire(tmp_path).jeton != g.jeton  # tiré à chaque démarrage
    dp = g.environnement(g.applis["douze-points"])
    assert dp["DOUZE_POINTS_CARNET_URL"] == "http://127.0.0.1:9111"
    comptoir = g.environnement(g.applis["comptoir"])
    assert not [k for k in comptoir if k.endswith("_URL") and k != "MAISON_ANNEAU_URL"]


def test_lancement_refuse_une_adresse_hors_127_et_le_vrai_jeton(tmp_path, monkeypatch):
    monkeypatch.setenv("MAISON_JETON", "le-vrai-jeton-de-la-maison")
    g = gestionnaire(tmp_path)
    with pytest.raises(RuntimeError, match="ne vise pas 127.0.0.1"):
        g.verifier_environnement("gazette", {"GAZETTE_CARNET_URL": "http://carnet:8096"})
    with pytest.raises(RuntimeError, match="vrai jeton"):
        g.verifier_environnement("gazette", {"QUELQUE_CHOSE": "le-vrai-jeton-de-la-maison"})
    g.applis["comptoir"].env = {"COMPTOIR_MISTRAL_URL": "https://api.mistral.ai/v1"}
    with pytest.raises(RuntimeError):
        g.environnement(g.applis["comptoir"])


def test_autotest_rouge_si_une_adresse_de_lien_sort(client):
    lu = client.get("/api/autotest").json()
    assert lu["liens"]["ok"] is True and "5 liens branchés" in lu["liens"]["message"]
    main.ETAT["gestionnaire"].applis["comptoir"].env = {"COMPTOIR_MISTRAL_URL": "https://api.mistral.ai/v1"}
    r = client.post("/api/autotest").json()
    assert r["ok"] is False and "127.0.0.1" in r["message"]
    assert main.ETAT["gestionnaire"].bloque
    assert client.post("/api/applis/comptoir/demarrer").status_code == 409


def test_api_des_liens_et_badge_encore_en_demo(client):
    liens = client.get("/api/liens").json()
    assert liens["ecart"] == {"manquants": [], "en_trop": []}
    assert sum(1 for x in liens["liens"] if x["branche"]) == 5
    applis = {a["id"]: a for a in client.get("/api/applis").json()["applis"]}
    assert {a for a, x in applis.items() if not x["demo"]} == {"carnet", "douze-points", "gazette"}
    assert applis["sillage"]["demo"] and applis["millesime"]["demo"]
    assert applis["gazette"]["appelle"] == ["carnet", "Douze points"]
    d = client.get("/api/applis").json()
    assert d["memoire_limite_mo"] == 2400 and "max_simultanees" not in d


# ------------------------------------------------------------------ activité et mémoire

def faux_processus() -> subprocess.Popen:
    return subprocess.Popen(["sleep", "60"], start_new_session=True)


def test_activite_propagee_aux_applis_appelees(tmp_path):
    g = gestionnaire(tmp_path)
    for x in g.etats.values():
        x.derniere_requete = 0
    g.toucher("gazette")
    assert all(g.etats[x].derniere_requete > 0 for x in ("gazette", "carnet", "douze-points"))
    assert g.etats["sillage"].derniere_requete == 0
    g.etats["carnet"].derniere_requete = 0
    g.toucher("douze-points")
    assert g.etats["carnet"].derniere_requete > 0 and g.etats["gazette"].derniere_requete > 0


def test_regle_des_2_4_go_sur_toute_la_maison(tmp_path):
    """Au-delà de la limite (mesurée sur l'arbre des processus, ici simulée), l'appli touchée il y a le plus longtemps
    s'arrête — jamais celle qu'on ouvre ni celles qu'elle appelle — et le dit."""
    g = gestionnaire(tmp_path)
    vivantes = ["comptoir", "sillage", "carnet", "gazette"]
    for k, x in enumerate(vivantes):
        g.etats[x].processus = faux_processus()
        g.etats[x].derniere_requete = 1000 + k          # comptoir est la plus ancienne, puis sillage…
    g.mesurer_total = lambda: 900 * sum(1 for e in g.etats.values() if e.vivant())     # 4 × 900 = 3600 Mo
    g.mesurer_appli = lambda pid: 800
    try:
        arretees = asyncio.run(g.liberer_memoire({"gazette", "carnet"}))
        assert arretees == ["comptoir", "sillage"]                   # 3600 → 2700 → 1800 : sous la limite
        assert g.etats["carnet"].vivant() and g.etats["gazette"].vivant()
        e = g.etat("comptoir")
        assert e["arret_memoire"] is True and e["etat"] == "arretee"
        assert e["message"] == f"Comptoir {MESSAGE_MEMOIRE}."
        assert "ses données sont gardées" in e["message"] and "la rouvrir" in e["message"]
        # tout est protégé : rien n'est arrêté, rien ne boucle
        g.mesurer_total = lambda: 9999
        assert asyncio.run(g.liberer_memoire({"gazette", "carnet"})) == []
    finally:
        asyncio.run(g.tout_arreter())


def test_mesure_sur_l_arbre_des_processus():
    """La mémoire d'une appli compte ses petits-enfants (Chromium de la Gazette : pilote node, puis Chromium)."""
    from app.processus import arbre
    p = subprocess.Popen(["sh", "-c", "sh -c 'sleep 30' & sleep 30"], start_new_session=True)
    try:
        for _ in range(50):
            if len(arbre(p.pid)) >= 3:
                break
            asyncio.run(asyncio.sleep(0.05))
        assert len(arbre(p.pid)) >= 3
    finally:
        import os
        import signal
        os.killpg(p.pid, signal.SIGKILL)
        p.wait()


def test_relais_dit_arretee_pour_liberer_la_memoire(client):
    g = main.ETAT["gestionnaire"]
    g.etats["comptoir"].arret_memoire = True
    g.source = lambda ident: Path("/aucune-appli") / ident       # même là où les applis sont installées
    relais = main.ETAT["relais"]["comptoir"]

    async def demander(chemin):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=relais), base_url="http://192.0.2.50:8113",
                                     cookies=dict(client.cookies.items())) as c:
            return await c.get(chemin)
    page = asyncio.run(demander("/"))
    assert page.status_code == 503 and "arrêtée pour libérer la mémoire" in page.text
    assert "ses données" in page.text and "bac-rouvrir=1" in page.text
    api = asyncio.run(demander("/api/session"))
    assert api.status_code == 503 and api.json()["arret_memoire"] is True
    # « La rouvrir » : le relais essaie de la démarrer (ici, elle n'est pas installée : message clair)
    rouvrir = asyncio.run(demander("/?bac-rouvrir=1"))
    assert rouvrir.status_code == 503 and "pas installée" in rouvrir.text


# ------------------------------------------------------------------ remise à zéro

def test_verrou_de_la_remise_a_zero(tmp_path):
    """Pendant la remise à zéro, aucun démarrage venu d'ailleurs (cascade, relais, écran) ; ensuite, de nouveau."""
    g = gestionnaire(tmp_path, applis=tmp_path / "aucune-appli")       # rien n'est lancé pour de vrai ici
    (g.dossier("gazette") / "donnees").mkdir(parents=True)
    (g.dossier("gazette") / "donnees" / "gazette.db").write_text("x")

    async def scenario():
        async with g.remise_a_zero():
            assert not g.dossier("gazette").exists()                 # toutes les bases vidées, Gazette comprise
            with pytest.raises(RuntimeError, match="remise à zéro"):
                await g.ouvrir("gazette")
            with pytest.raises(RuntimeError, match="remise à zéro"):
                await g.demarrer("carnet")
        assert not g.remise
        # hors de l'image, l'appli n'est pas installée : le refus n'est plus celui du verrou
        with pytest.raises(RuntimeError, match="pas installée"):
            await g.ouvrir("gazette")
    asyncio.run(scenario())
    assert REMISE_EN_COURS.startswith("La maison simulée")


def test_remise_a_zero_par_l_api_demande_confirmation(client):
    apercu = client.get("/api/maison/remise-a-zero").json()
    assert set(apercu["perdu"]) == {"applis", "ecritures", "photos", "soiree", "soiree_cloturee"}
    assert client.post("/api/maison/remise-a-zero", json={}).status_code == 422
    r = client.post("/api/maison/remise-a-zero", json={"confirmer": True})
    assert r.status_code == 200 and r.json()["scenario"] is None


# ------------------------------------------------------------------ liste blanche de la Gazette

def test_gazette_ne_garde_que_les_personnes_inventees():
    G = lanceur_gazette()
    scenario = {"personnes_detail": [{"id": 1, "origine": "inventee"}, {"id": 2, "origine": "reelle"},
                                     {"id": 3, "origine": "piege"}]}
    permis = G.permis_du_scenario(scenario)
    assert permis == {"BAS-00001", "BAS-00003"}
    liste = [{"carnet_id": "BAS-00001", "nom": "Inventée"}, {"carnet_id": "BAS-00002", "nom": "Copie"},
             {"carnet_id": "F-07", "nom": "Inconnue"}, {"nom": "Sans identifiant"}]
    assert [p["nom"] for p in G.filtrer_personnes(liste, permis)] == ["Inventée"]
    assert G.permis_du_scenario(None) == set()


def test_gazette_ecarte_les_copies_du_journal_de_la_soiree():
    G = lanceur_gazette()
    j = {"format": 1, "invites": [{"id": 1, "prenom": "Alice", "carnet_id": "BAS-00001"},
                                  {"id": 2, "prenom": "Réelline", "carnet_id": "BAS-00002"},
                                  {"id": 3, "prenom": "Tapé", "carnet_id": None}],
         "chansons": [{"id": 9, "pays": "Portugal", "notes": [{"invite": 1}, {"invite": 2}, {"invite": 3}]}],
         "palmares": [{"invite": 2, "complet": True}, {"invite": 1, "complet": True}], "plus_proche": 2,
         "commentaires": [{"invite": 2, "chanson": 9, "texte": "secret"}, {"invite": 1, "chanson": 9, "texte": "Frissons !"}],
         "duos": [{"cle": "1-2", "invites": [1, 2]}, {"cle": "1-3", "invites": [1, 3]}],
         "demi": {"flair": [{"invite": 2}, {"invite": 1}]}}
    f = G.filtrer_journal(j, {"BAS-00001"})
    texte = str(f)
    assert "Réelline" not in texte and "secret" not in texte and "Tapé" not in texte
    assert [i["prenom"] for i in f["invites"]] == ["Alice"]
    assert f["chansons"][0]["notes"] == [{"invite": 1}] and f["plus_proche"] == 1 and f["duos"] == []
    assert f["demi"]["flair"] == [{"invite": 1}] and f["bac_a_sable"]["invites_ecartes"] == 2
    assert j["invites"][1]["prenom"] == "Réelline"              # l'original n'est pas touché


def test_lanceur_gazette_sans_variable_de_lien_ne_demarre_pas(monkeypatch):
    G = lanceur_gazette()
    monkeypatch.delenv("GAZETTE_CARNET_URL", raising=False)
    with pytest.raises(SystemExit, match="GAZETTE_CARNET_URL"):
        G.lien("GAZETTE_CARNET_URL")
    monkeypatch.setenv("GAZETTE_CARNET_URL", "http://carnet:8096")
    with pytest.raises(SystemExit):
        G.lien("GAZETTE_CARNET_URL")
    monkeypatch.setenv("GAZETTE_CARNET_URL", "http://127.0.0.1:9111/")
    assert G.lien("GAZETTE_CARNET_URL") == "http://127.0.0.1:9111"
    assert G.ARGS_CHROMIUM == ["--proxy-server=http://127.0.0.1:9", "--proxy-bypass-list=<-loopback>"]


def test_catalogue_gazette_branchee():
    a: Appli = catalogue(CATALOGUE)["gazette"]
    assert a.lanceur == "bac" and a.branchee and a.personnes
    assert (RACINE / "lanceurs" / "gazette.py").is_file()
    assert Path(RACINE / "docs" / "flux-maison.json").is_file()


def test_ports_des_applis_derriere_le_relais_et_sa_connexion(client):
    """Les ports 8110 à 8121 (carnet simulé y garde des copies de vraies fiches) passent tous par le relais : sans
    connexion au Bac à sable, rien (seule la porte des invités de Douze points reste ouverte aux vrais téléphones)."""
    async def sans_connexion(relais, chemin):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=relais),
                                     base_url=f"http://192.0.2.50:{relais.appli.port}") as c:
            return await c.get(chemin)
    for ident, relais in main.ETAT["relais"].items():
        for chemin in ("/", "/api/session", "/gazette/personnes", "/externe/soirees"):
            assert asyncio.run(sans_connexion(relais, chemin)).status_code == 401, (ident, chemin)
