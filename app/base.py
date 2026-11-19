"""Base du Bac à sable (SQLite, dans le dossier de données) : personnes et scénarios.

Les données de chaque appli simulée vivent ailleurs, dans <données>/applis/<appli>/ (sa propre base, au schéma de
sa version embarquée) ; elles sont jetées à chaque « Rejouer » ou « Vider ».
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS personne (
    id          INTEGER PRIMARY KEY,
    origine     TEXT NOT NULL CHECK (origine IN ('inventee', 'piege', 'reelle')),
    carnet_id   TEXT,
    donnees     TEXT NOT NULL,
    epinglee    INTEGER NOT NULL DEFAULT 0,
    cree_le     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scenario (
    id          INTEGER PRIMARY KEY,
    nom         TEXT NOT NULL,
    applis      TEXT NOT NULL,      -- liste JSON d'identifiants d'applis
    personnes   TEXT NOT NULL,      -- liste JSON d'identifiants de personnes
    reglages    TEXT NOT NULL,      -- réglages propres à chaque appli, JSON {appli: {...}}
    epingle     INTEGER NOT NULL DEFAULT 0,
    cree_le     TEXT NOT NULL,
    joue_le     TEXT
);
"""


def maintenant() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def fichier(data: Path) -> Path:
    return data / "bac-a-sable.db"


@contextmanager
def base(data: Path):
    data.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(fichier(data), timeout=10)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys=ON")
    cx.execute("PRAGMA secure_delete=ON")     # une fiche effacée est écrasée, pas seulement marquée libre
    try:
        yield cx
        cx.commit()
    finally:
        cx.close()


def preparer(data: Path) -> None:
    with base(data) as cx:
        cx.executescript(SCHEMA)


# ---------------------------------------------------------------- personnes

def personne(r: sqlite3.Row) -> dict:
    return {"id": r["id"], "origine": r["origine"], "carnet_id": r["carnet_id"], "epinglee": bool(r["epinglee"]),
            "cree_le": r["cree_le"], **json.loads(r["donnees"])}


def personnes(cx, ids: list[int] | None = None) -> list[dict]:
    if ids is None:
        lignes = cx.execute("SELECT * FROM personne ORDER BY id").fetchall()
    else:
        if not ids:
            return []
        marques = ",".join("?" * len(ids))
        lignes = cx.execute(f"SELECT * FROM personne WHERE id IN ({marques}) ORDER BY id", ids).fetchall()
    return [personne(r) for r in lignes]


def ajouter_personne(cx, origine: str, donnees: dict, carnet_id: str | None = None) -> int:
    return cx.execute("INSERT INTO personne(origine, carnet_id, donnees, cree_le) VALUES(?,?,?,?)",
                      (origine, carnet_id, json.dumps(donnees, ensure_ascii=False), maintenant())).lastrowid


def changer_donnees(cx, pid: int, donnees: dict) -> None:
    cx.execute("UPDATE personne SET donnees=? WHERE id=?", (json.dumps(donnees, ensure_ascii=False), pid))


def effacer_personnes(cx, ids: list[int] | None = None) -> int:
    """Efface pour de bon (secure_delete + VACUUM par l'appelant). Retire aussi ces personnes des scénarios."""
    if ids is None:
        n = cx.execute("DELETE FROM personne").rowcount
        cx.execute("UPDATE scenario SET personnes='[]'")
        return n
    if not ids:
        return 0
    marques = ",".join("?" * len(ids))
    n = cx.execute(f"DELETE FROM personne WHERE id IN ({marques})", ids).rowcount
    for s in cx.execute("SELECT id, personnes FROM scenario").fetchall():
        reste = [p for p in json.loads(s["personnes"]) if p not in ids]
        cx.execute("UPDATE scenario SET personnes=? WHERE id=?", (json.dumps(reste), s["id"]))
    return n


def copies_perimees(cx, jours: int) -> list[int]:
    """Les copies de vraies fiches plus vieilles que `jours`, ni épinglées ni dans un scénario épinglé."""
    limite = (datetime.now().astimezone() - timedelta(days=jours)).isoformat(timespec="seconds")
    gardees = set()
    for s in cx.execute("SELECT personnes FROM scenario WHERE epingle=1"):
        gardees.update(json.loads(s["personnes"]))
    return [r["id"] for r in cx.execute(
        "SELECT id FROM personne WHERE origine='reelle' AND epinglee=0 AND cree_le < ?", (limite,))
        if r["id"] not in gardees]


def compacter(data: Path) -> None:
    """VACUUM : réécrit le fichier, aucune page libre ne garde une fiche effacée."""
    cx = sqlite3.connect(fichier(data))
    try:
        cx.execute("VACUUM")
    finally:
        cx.close()


# ---------------------------------------------------------------- scénarios

def scenario(r: sqlite3.Row) -> dict:
    return {"id": r["id"], "nom": r["nom"], "applis": json.loads(r["applis"]), "personnes": json.loads(r["personnes"]),
            "reglages": json.loads(r["reglages"]), "epingle": bool(r["epingle"]), "cree_le": r["cree_le"],
            "joue_le": r["joue_le"]}


def scenarios(cx) -> list[dict]:
    return [scenario(r) for r in cx.execute("SELECT * FROM scenario ORDER BY id DESC")]


def lire_scenario(cx, sid: int) -> dict | None:
    r = cx.execute("SELECT * FROM scenario WHERE id=?", (sid,)).fetchone()
    return scenario(r) if r else None


def ecrire_scenario(cx, s: dict, sid: int | None = None) -> int:
    valeurs = (s["nom"], json.dumps(s["applis"]), json.dumps(s["personnes"]),
               json.dumps(s.get("reglages") or {}, ensure_ascii=False), int(bool(s.get("epingle"))))
    if sid is None:
        return cx.execute("INSERT INTO scenario(nom, applis, personnes, reglages, epingle, cree_le) VALUES(?,?,?,?,?,?)",
                          (*valeurs, maintenant())).lastrowid
    cx.execute("UPDATE scenario SET nom=?, applis=?, personnes=?, reglages=?, epingle=? WHERE id=?", (*valeurs, sid))
    return sid
