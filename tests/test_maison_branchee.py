"""0.4.0 — « la maison branchée », de bout en bout : de vraies applis (carnet, Douze points, Gazette) dans de vrais
processus, reliées entre elles par les liens simulés.

Test de livraison (conseil, point 2) : une soirée simulée avec des pays réels est clôturée dans Douze points simulé ;
la Gazette simulée en fait son numéro avec ces pays, les invités inventés et leurs commentaires — plus de « Pays 6 » —
et aucune copie de vraie fiche n'y paraît (arbitrage de Julien du 20/11/2026).

Demande BAC_ESSAI_APPLIS (comme test_bout_en_bout.py) ; sautés sinon. La CI les lance dans l'image construite.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx
import pytest

from app import base, main

pytestmark = pytest.mark.skipif(not os.environ.get("BAC_ESSAI_APPLIS"), reason="applis embarquées absentes")
ANNUAIRE = True       # le faux annuaire de l'Anneau écoute (conftest)
RACINE = Path(__file__).resolve().parent.parent
PAYS = ["Portugal", "Pologne", "Moldavie", "Suède", "Italie", "Ukraine"]
VRAIE = {"prenom": "Réelline", "nom": "Copievraie", "genre": "femme", "naissance": "1970-01-02", "ville": "",
         "telephone": "", "courriel": "", "liens": []}


def installee(ident: str) -> bool:
    return os.path.isdir(os.path.join(os.environ.get("BAC_ESSAI_APPLIS", ""), ident, "src"))


tout_installe = pytest.mark.skipif(not all(installee(x) for x in ("carnet", "douze-points", "gazette")),
                                   reason="carnet, Douze points ou Gazette absent")


async def par_le_relais(ident: str, methode: str, chemin: str, cookies: dict | None = None, **kw) -> httpx.Response:
    relais = main.ETAT["relais"][ident]
    transport = httpx.ASGITransport(app=relais)
    async with httpx.AsyncClient(transport=transport, base_url=f"http://192.0.2.50:{relais.appli.port}",
                                 cookies=cookies or {}, timeout=180) as c:
        return await c.request(methode, chemin, **kw)


def relais(client, ident, methode, chemin, **kw) -> httpx.Response:
    return asyncio.run(par_le_relais(ident, methode, chemin, cookies=dict(client.cookies.items()), **kw))


def scenario_soiree(client, cloturee: bool = True) -> tuple[int, list[dict], int]:
    ids = client.post("/api/personnes/inventer", json={"nombre": 5, "graine": 11, "variete": 0}).json()["ajoutees"]
    with base.base(main.ETAT["cfg"].data) as cx:          # comme « Copier depuis carnet » (vraie fiche, lecture seule)
        vraie = base.ajouter_personne(cx, "reelle", VRAIE, "vrai-123")
    sid = client.post("/api/scenarios", json={
        "nom": "Soirée branchée", "applis": ["douze-points", "gazette"], "personnes": ids + [vraie],
        "reglages": {"douze-points": {"telephones": 6, "chansons": len(PAYS), "pays": PAYS, "graine": 3,
                                      "cloturee": cloturee}}}).json()["id"]
    gens = [p for p in client.get("/api/personnes").json()["personnes"] if p["id"] in ids]
    return sid, gens, vraie


@tout_installe
def test_livraison_soiree_cloturee_jusque_dans_la_gazette(client):
    sid, inventes, vraie = scenario_soiree(client)
    r = client.post(f"/api/scenarios/{sid}/jouer", json={"appli": "gazette"})
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["soiree"]["cloturee"] is True, res
    assert "envoyé à carnet" in res["soiree"]["cloture"]["carnet"], res["soiree"]       # Douze points → carnet
    applis = {a["id"]: a for a in client.get("/api/applis").json()["applis"]}
    assert all(applis[x]["etat"] == "demarree" for x in ("carnet", "douze-points", "gazette"))
    assert applis["gazette"]["branchee"] and not applis["gazette"]["demo"]

    # la Gazette simulée relit Douze points simulé (comme à l'ouverture d'« À traiter »)
    lu = relais(client, "gazette", "POST", "/api/eurovision/relire")
    assert lu.status_code == 200 and lu.json()["nouveaux"] == 1, lu.text
    numeros = relais(client, "gazette", "GET", "/api/eurovisions").json()["eurovisions"]
    assert len(numeros) == 1
    fiche = relais(client, "gazette", "GET", f"/api/eurovisions/{numeros[0]['id']}")
    assert fiche.status_code == 200, fiche.text
    vue, texte = fiche.json()["vue"], fiche.text

    # les pays réels de la soirée, plus de « Pays 6 »
    assert not re.search(r"Pays \d", texte)
    assert vue["podium_maison"] and set(vue["podium_maison"]) <= set(PAYS), vue["podium_maison"]
    # les invités inventés du scénario et leurs commentaires
    prenoms = {p["prenom"] for p in inventes}
    invites = {x["prenom"].split(" ")[0] for x in fiche.json()["carnet"]}
    assert invites and invites <= prenoms, (invites, prenoms)
    assert all(x["carnet"] for x in fiche.json()["carnet"])           # chacun relié à sa fiche de carnet simulé
    assert vue["commentaires"], vue
    assert all(c["prenom"].split(" ")[0] in prenoms and c["pays"] in PAYS and c["texte"] for c in vue["commentaires"])
    apercu = relais(client, "gazette", "GET", f"/api/eurovisions/{numeros[0]['id']}/apercu")
    assert apercu.status_code == 200
    assert any(p in apercu.text for p in vue["podium_maison"]) and not re.search(r"Pays \d", apercu.text)
    assert any(c["texte"] in apercu.text for c in vue["commentaires"])

    # aucune copie de vraie fiche dans la Gazette (elle est bien dans Douze points et carnet simulés)
    for chemin in (f"/api/eurovisions/{numeros[0]['id']}", f"/api/eurovisions/{numeros[0]['id']}/apercu",
                   "/api/carnet/suggestions?q=R", "/api/carnet/suggestions?q=Copievraie", "/api/a-traiter"):
        page = relais(client, "gazette", "GET", chemin)
        assert "Réelline" not in page.text and "Copievraie" not in page.text.replace("q=Copievraie", ""), chemin
    sugg = relais(client, "gazette", "GET", "/api/carnet/suggestions?q=" + inventes[0]["nom"]).json()
    assert sugg["actif"] and sugg["suggestions"], sugg                   # les inventés, eux, viennent de carnet
    soiree_dp = relais(client, "douze-points", "GET", f"/api/soirees/{res['soiree']['soiree_id']}")
    assert "Réelline" in soiree_dp.text
    contacts = relais(client, "carnet", "GET", "/api/contacts")
    assert "Réelline" in contacts.text or "RÉELLINE" in contacts.text.upper()

    # le PDF du magazine : Chromium de la Gazette démarre avec ses adresses restreintes (proxy mort, sans exception
    # pour la machine elle-même) et imprime quand même (tout y est embarqué en data:)
    pdf = relais(client, "gazette", "GET", f"/api/eurovisions/{numeros[0]['id']}/pdf")
    if pdf.status_code == 503 and "Chromium" in pdf.text:
        print("Chromium absent ici :", pdf.text[:200])
    else:
        assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF", pdf.text[:300]

    # rien n'est sorti vers un vrai service ; aucune appli n'a joint un port hors de ses liens
    journal = client.get("/api/journal", params={"sorte": "sortie_refusee"}).json()["lignes"]
    print("sorties refusées :", [(x["appli"], x.get("vers")) for x in journal])
    assert not [x for x in journal if x["appli"] in ("gazette", "douze-points", "carnet")
                and str(x.get("vers", "")).startswith("127.0.0.1:91")]
    client.post("/api/applis/tout-arreter")


@tout_installe
def test_cascade_activite_et_garde_par_appli(client):
    """Ouvrir la Gazette démarre carnet et Douze points (« lancée pour Gazette ») ; la toucher les touche ; leurs
    adresses sont des 127.0.0.1 et le jeton simulé n'est pas le vrai ; un port hors des liens reste fermé."""
    r = client.post("/api/applis/gazette/demarrer")
    assert r.status_code == 200, r.text
    assert r.json()["cascade"] == ["carnet", "Douze points"]
    applis = {a["id"]: a for a in client.get("/api/applis").json()["applis"]}
    assert applis["carnet"]["lancee_pour"] == "Gazette" and applis["douze-points"]["lancee_pour"] == "Gazette"
    g = main.ETAT["gestionnaire"]
    for x in ("carnet", "douze-points"):
        g.etats[x].derniere_requete = 0
    assert relais(client, "gazette", "GET", "/api/session").json()["connecte"] is True
    assert all(g.etats[x].derniere_requete > 0 for x in ("carnet", "douze-points"))     # activité propagée
    env = g.environnement(g.applis["gazette"])
    assert env["GAZETTE_CARNET_URL"] == f"http://127.0.0.1:{g.applis['carnet'].port_local}"
    assert env["GAZETTE_DOUZE_POINTS_URL"] == f"http://127.0.0.1:{g.applis['douze-points'].port_local}"
    assert env["MAISON_JETON"] == g.jeton and env["MAISON_JETON"] != os.environ.get("MAISON_JETON", "")
    # la Gazette joint carnet par son lien (fiche « Connexion » vérifiée), mais pas le Bac à sable ni Comptoir
    verif = relais(client, "gazette", "POST", "/api/maison/services/carnet/verifier")
    assert verif.status_code == 200 and verif.json()["etat"] == "repond", verif.text
    # le faux annuaire de l'Anneau répond au jeton simulé, pas à un autre
    port = g.port_annuaire
    ok = httpx.get(f"http://127.0.0.1:{port}/externe/services", headers={"Authorization": f"Bearer {g.jeton}"})
    assert ok.status_code == 200 and any(s["nom"] == "Gazette" for s in ok.json()["services"])
    assert httpx.get(f"http://127.0.0.1:{port}/externe/services",
                     headers={"Authorization": "Bearer autre"}).status_code == 404
    client.post("/api/applis/tout-arreter")


@pytest.mark.skipif(not installee("gazette"), reason="Gazette absente")
def test_chromium_de_la_gazette_ne_joint_aucun_port_local(tmp_path):
    """Point 11 du conseil : Chromium échappe à la garde Python. Le lanceur de la Gazette lui donne un proxy mort et
    retire son exception « machine locale » : même un port local ouvert reste injoignable."""
    navigateurs = os.environ.get("BAC_ESSAI_NAVIGATEURS", "/ms-playwright")
    if not Path(navigateurs).is_dir():
        pytest.skip("Chromium absent")

    class Rep(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"atteint")

        def log_message(self, *a):
            pass
    serveur = HTTPServer(("127.0.0.1", 0), Rep)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    code = ("import sys\n"
            "sys.path.insert(0, sys.argv[2])\n"
            "import gazette as L\n"
            "assert L.restreindre_chromium()\n"
            "from playwright.sync_api import sync_playwright\n"
            "with sync_playwright() as pw:\n"
            "    nav = pw.chromium.launch(args=['--no-sandbox'])\n"
            "    pg = nav.new_page()\n"
            "    try:\n"
            "        pg.goto(f'http://127.0.0.1:{sys.argv[1]}/', timeout=8000); print('PASSE')\n"
            "    except Exception as e:\n"
            "        print('REFUS', 'PROXY' in str(e))\n"
            "    nav.close()\n")
    site = Path(os.environ["BAC_ESSAI_APPLIS"]) / "gazette" / "site"
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONPATH": str(site), "HOME": str(tmp_path),
           "PLAYWRIGHT_BROWSERS_PATH": navigateurs}
    r = subprocess.run([os.environ.get("BAC_ESSAI_PYTHON", sys.executable), "-c", code, str(serveur.server_port),
                        str(RACINE / "lanceurs")], env=env, capture_output=True, text=True, timeout=120)
    serveur.shutdown()
    assert r.stdout.split() == ["REFUS", "True"], r.stdout + r.stderr


@tout_installe
def test_remise_a_zero_de_la_maison(client):
    """Une seule remise à zéro : toutes les bases vidées (Gazette comprise), le scénario reversé, soirée comprise."""
    sid, inventes, _ = scenario_soiree(client, cloturee=False)
    assert client.post(f"/api/scenarios/{sid}/jouer", json={"appli": "gazette"}).status_code == 200
    g = main.ETAT["gestionnaire"]
    temoin = g.dossier("gazette") / "donnees" / "temoin.txt"
    temoin.write_text("joué avant")
    apercu = client.get("/api/maison/remise-a-zero", params={"scenario": sid}).json()
    assert {a["id"] for a in apercu["perdu"]["applis"]} >= {"carnet", "douze-points", "gazette"}
    assert apercu["perdu"]["soiree"] is True and apercu["reverse"]["nom"] == "Soirée branchée"
    assert apercu["reverse"]["soiree"] is True and apercu["reverse"]["soiree_cloturee"] is False
    assert client.post("/api/maison/remise-a-zero", json={"scenario": sid}).status_code == 422     # sans confirmer
    r = client.post("/api/maison/remise-a-zero", json={"scenario": sid, "confirmer": True})
    assert r.status_code == 200, r.text
    assert not temoin.exists()
    assert r.json()["soiree"]["soiree_id"] and not r.json()["soiree"]["cloturee"]
    scen = json.loads((g.dossier("gazette") / "scenario.json").read_text())
    assert {p["id"] for p in scen["personnes_detail"]} >= {p["id"] for p in inventes}
    client.post("/api/applis/tout-arreter")
