"""Fabrique de personnes : inventées, pièges, copies de vraies fiches (lecture seule, champs réduits)."""
from __future__ import annotations

import httpx
import pytest

from app import personnes


def test_inventer_est_reproductible_et_relie():
    a, b = personnes.inventer(30, graine=4), personnes.inventer(30, graine=4)
    assert a == b and len(a) == 30
    liens = [(i, l["vers"], l["relation"]) for i, p in enumerate(a) for l in p["liens"]]
    assert liens, "des liens de famille ou d'amitié"
    for i, j, rel in liens:          # chaque lien a sa réciproque
        inverse = {"parent": "enfant", "enfant": "parent"}.get(rel)
        retour = [l["relation"] for l in a[j]["liens"] if l["vers"] == i]
        assert retour, (i, j, rel)
        if inverse:
            assert inverse in retour


def test_rien_d_invente_ne_joint_quelqu_un():
    for p in personnes.inventer(60, graine=1) + personnes.pieges():
        assert not p["courriel"] or p["courriel"].endswith("@example.org")
        tel = p["telephone"].replace(" ", "")
        assert not tel or tel.startswith(("+33639", "+4122000"))


def test_pieges_disent_ce_qu_ils_testent():
    pieges = personnes.pieges()
    assert len(pieges) >= 10 and all(p["note"] for p in pieges)
    assert sum(1 for p in pieges if (p["prenom"], p["nom"]) == ("Marie", "Martin")) == 2


def faux_carnet(personnes_):
    vus = []

    def repondre(r: httpx.Request):
        vus.append((r.method, r.url.path, r.headers.get("authorization")))
        return httpx.Response(200, json={"personnes": personnes_})
    return httpx.MockTransport(repondre), vus


def test_copie_ne_garde_que_nom_prenom_naissance_genre():
    t, vus = faux_carnet([{"carnet_id": "A1", "personne_id": "p1", "nom": "Odile Personne", "nom_carnet": "Odile Personne",
                           "prenom": "Odile", "naissance": "1970-01-02", "genre": "femme", "immich_id": "im-1",
                           "journaux": "secret", "parus": [1], "livre_or": [{"message": "x"}]},
                          {"carnet_id": "A2", "prenom": "Jo", "nom_carnet": "Jo", "jour": 3, "mois": 4, "annee": None}])
    fiches = personnes.lire_carnet("http://carnet.exemple", "jeton", t)
    assert vus == [("GET", "/gazette/personnes", "Bearer jeton")]
    assert fiches[0] == {"carnet_id": "A1", "prenom": "Odile", "nom": "Personne", "genre": "femme", "naissance": "1970-01-02"}
    assert fiches[1]["naissance"] == "--04-03"
    p = personnes.depuis_carnet(fiches[0])
    assert p["telephone"] == "" and p["liens"] == [] and "journaux" not in p


def test_copie_sans_reglage_ou_carnet_muet():
    with pytest.raises(personnes.CarnetInjoignable):
        personnes.lire_carnet("", "", None)
    muet = httpx.MockTransport(lambda r: httpx.Response(503))
    with pytest.raises(personnes.CarnetInjoignable):
        personnes.lire_carnet("http://carnet.exemple", "j", muet)
