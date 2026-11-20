"""La garde chargée dans chaque appli simulée : rien ne sort, tout est noté."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

GARDE = Path(__file__).resolve().parent.parent / "garde"


def lancer(code: str, journal: Path, *args, ports: str = "") -> subprocess.CompletedProcess:
    env = {"PATH": os.environ["PATH"], "PYTHONPATH": os.pathsep.join([str(GARDE), *sys.path[1:]]),
           "BAS_APPLI": "essai", "BAS_JOURNAL": str(journal), "BAS_PORTS": ports}
    return subprocess.run([sys.executable, "-c", code, *args], env=env, capture_output=True, text=True, timeout=60)


def lignes(journal: Path) -> list[dict]:
    return [json.loads(x) for x in journal.read_text().splitlines()] if journal.exists() else []


def test_sortie_refusee_vers_le_reseau(tmp_path):
    j = tmp_path / "j.jsonl"
    code = ("import socket\n"
            "for h in ('192.0.2.1', '10.0.0.1', '1.1.1.1'):\n"
            "    try:\n"
            "        socket.create_connection((h, 80), timeout=2)\n"
            "        print('PASSE', h)\n"
            "    except OSError as e:\n"
            "        print('REFUS', 'Bac à sable' in str(e))\n")
    r = lancer(code, j)
    assert r.stdout.split().count("REFUS") == 3 and "PASSE" not in r.stdout, r.stdout + r.stderr
    assert "True" in r.stdout
    assert [x["vers"] for x in lignes(j) if x["sorte"] == "sortie_refusee"] == ["192.0.2.1", "10.0.0.1", "1.1.1.1"]


def test_aucun_nom_resolu_sauf_localhost(tmp_path):
    j = tmp_path / "j.jsonl"
    code = ("import socket\n"
            "try:\n"
            "    socket.getaddrinfo('immich_server', 2283)\n"
            "    print('RESOLU')\n"
            "except socket.gaierror:\n"
            "    print('NON')\n"
            "print(len(socket.getaddrinfo('localhost', 80)) > 0)\n")
    r = lancer(code, j)
    assert r.stdout.split() == ["NON", "True"], r.stdout + r.stderr
    assert any(x["sorte"] == "nom_refuse" and x["nom"] == "immich_server" for x in lignes(j))


def test_requests_et_httpx_vers_l_exterieur_echouent(tmp_path):
    j = tmp_path / "j.jsonl"
    code = ("import httpx, urllib.request\n"
            "for f in (lambda: httpx.get('http://192.0.2.7:2283/api'), lambda: urllib.request.urlopen('http://192.0.2.8/', timeout=2)):\n"
            "    try:\n"
            "        f(); print('PASSE')\n"
            "    except Exception as e:\n"
            "        print('REFUS')\n")
    r = lancer(code, j)
    assert r.stdout.split() == ["REFUS", "REFUS"], r.stdout + r.stderr


def test_machine_locale_permise_et_ecritures_notees(tmp_path):
    class Rep(BaseHTTPRequestHandler):
        def do_PUT(self):
            self.rfile.read(int(self.headers.get("content-length", 0)))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *a):
            pass

    serveur = HTTPServer(("127.0.0.1", 0), Rep)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    j = tmp_path / "j.jsonl"
    code = ("import sys, urllib.request, httpx\n"
            "req = urllib.request.Request(f'http://127.0.0.1:{sys.argv[1]}/api/assets/x', data=b'{}', method='PUT')\n"
            "print(urllib.request.urlopen(req).status)\n"
            "t = httpx.MockTransport(lambda r: httpx.Response(200))\n"
            "httpx.Client(transport=t).post('http://immich/api/albums', json={'a': 1})\n"
            "httpx.Client(transport=t).get('http://immich/api/people')\n")
    r = lancer(code, j, str(serveur.server_port), ports=str(serveur.server_port))   # 0.4.0 : un port de ses liens
    serveur.shutdown()
    assert r.stdout.strip() == "204", r.stdout + r.stderr
    ecritures = [x for x in lignes(j) if x["sorte"] == "ecriture"]
    assert {"service": "immich", "action": "POST /api/albums"} in [{k: x[k] for k in ("service", "action")} for x in ecritures]
    assert any(x["action"].startswith("PUT /api/assets/x") for x in ecritures)
    assert not any("GET" in x["action"] for x in ecritures)        # les lectures ne sont pas des écritures


def test_envoi_en_flux_vers_un_faux_service(tmp_path):
    """0.1.6 : un envoi en flux (la photo de Douze points vers le faux Immich) passe, et sa taille est notée.
    Avant, la garde lisait `requete.content` d'un corps pas encore lu : « Attempted to access streaming request
    content, without having called `read()` », et l'envoi échouait."""
    j = tmp_path / "j.jsonl"
    code = ("import httpx\n"
            "def rep(r):\n"
            "    return httpx.Response(201, json={'taille': len(r.read())})\n"
            "def flux():\n"
            "    yield b'a' * 1000\n"
            "    yield b'b' * 500\n"
            "c = httpx.Client(transport=httpx.MockTransport(rep))\n"
            "print(c.post('http://immich/api/assets', content=flux()).json()['taille'])\n"
            "print(c.post('http://immich/api/assets', content=b'x' * 42, headers={'content-length': '42'}).status_code)\n")
    r = lancer(code, j)
    assert r.stdout.split() == ["1500", "201"], r.stdout + r.stderr
    tailles = [x.get("taille") for x in lignes(j) if x["sorte"] == "ecriture"]
    assert tailles[-1] == 42 and len(tailles) == 2


def _serveur_local():
    class Rep(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *a):
            pass
    serveur = HTTPServer(("127.0.0.1", 0), Rep)
    threading.Thread(target=serveur.serve_forever, daemon=True).start()
    return serveur


def test_garde_par_appli_refuse_un_port_local_hors_des_liens(tmp_path):
    """0.4.0 (garde resserrée) : sur la machine elle-même, seuls les ports des liens de l'appli passent. Un autre port
    local (le Bac à sable, une appli simulée sans lien, un relais) est refusé et noté."""
    lie, autre = _serveur_local(), _serveur_local()
    j = tmp_path / "j.jsonl"
    code = ("import sys, httpx\n"
            "for port in sys.argv[1:]:\n"
            "    try:\n"
            "        print(httpx.get(f'http://127.0.0.1:{port}/', timeout=3).text)\n"
            "    except Exception as e:\n"
            "        print('REFUS', 'Bac à sable' in str(e) or 'Bac à sable' in repr(e.__context__))\n")
    r = lancer(code, j, str(lie.server_port), str(autre.server_port), ports=f"{lie.server_port},9104")
    lie.shutdown()
    autre.shutdown()
    assert r.stdout.split() == ["ok", "REFUS", "True"], r.stdout + r.stderr
    refus = [x for x in lignes(j) if x["sorte"] == "sortie_refusee"]
    assert refus and refus[0]["vers"] == f"127.0.0.1:{autre.server_port}"


def test_garde_laisse_les_serveurs_ouverts_par_l_appli_elle_meme(tmp_path):
    """Les faux serveurs d'une démonstration (Millésime : ThreadingHTTPServer sur un port tiré au hasard) restent
    joignables : le port ouvert par le processus lui-même est permis."""
    j = tmp_path / "j.jsonl"
    code = ("import threading, urllib.request\n"
            "from http.server import HTTPServer, BaseHTTPRequestHandler\n"
            "class R(BaseHTTPRequestHandler):\n"
            "    def do_GET(self):\n"
            "        self.send_response(200); self.end_headers(); self.wfile.write(b'dedans')\n"
            "    def log_message(self, *a): pass\n"
            "s = HTTPServer(('127.0.0.1', 0), R)\n"
            "threading.Thread(target=s.serve_forever, daemon=True).start()\n"
            "print(urllib.request.urlopen(f'http://127.0.0.1:{s.server_port}/').read().decode())\n")
    r = lancer(code, j)
    assert r.stdout.split() == ["dedans"], r.stdout + r.stderr


def test_garde_refuse_les_adresses_de_la_vraie_stack(tmp_path):
    """Les noms de la vraie stack (carnet:8096, douze-points:8088, anneau:8094) ne sont jamais résolus."""
    j = tmp_path / "j.jsonl"
    code = ("import httpx\n"
            "for u in ('http://carnet:8096/gazette/personnes', 'http://douze-points:8088/externe/soirees', 'http://anneau:8094/externe/services'):\n"
            "    try:\n"
            "        httpx.get(u, timeout=2, trust_env=False); print('PASSE')\n"
            "    except Exception:\n"
            "        print('REFUS')\n")
    r = lancer(code, j, ports="9111,9114")
    assert r.stdout.split() == ["REFUS"] * 3, r.stdout + r.stderr
    assert {x["nom"] for x in lignes(j) if x["sorte"] == "nom_refuse"} == {"carnet", "douze-points", "anneau"}
