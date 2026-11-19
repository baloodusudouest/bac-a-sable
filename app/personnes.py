"""Fabrique de personnes du Bac à sable.

- inventer(n) : des personnes plausibles, avec des liens de famille et d'amitié entre elles.
- pieges() : des cas limites qui cassent les applis (homonymes, accents, dates incomplètes, doublons…).
- copier_depuis_carnet(...) : de vraies fiches, lues dans carnet (lecture seule, jeton commun, depuis ce processus
  seulement). Seuls le prénom, le nom, la date de naissance et le genre sont gardés.

Numéros de téléphone : tranche réservée par l'ARCEP aux œuvres de fiction (06 39 98 xx xx), adresses électroniques
en example.org : rien de ce qui est inventé ne peut joindre quelqu'un.
"""
from __future__ import annotations

import random
from datetime import date

import httpx

PRENOMS_F = ["Agathe", "Alice", "Amandine", "Anaïs", "Bérénice", "Camille", "Capucine", "Chloé", "Clémence", "Colette",
             "Delphine", "Éléonore", "Élise", "Émilie", "Fanny", "Gaëlle", "Hélène", "Inès", "Jeanne", "Joséphine",
             "Juliette", "Laure", "Léa", "Lucie", "Mathilde", "Maëlys", "Margaux", "Nadège", "Noémie", "Océane",
             "Pauline", "Rose", "Salomé", "Solène", "Sophie", "Thaïs", "Valentine", "Victoire", "Yvette", "Zoé"]
PRENOMS_H = ["Adrien", "Alban", "Antoine", "Arthur", "Aurélien", "Basile", "Benoît", "Bertrand", "Clément", "Damien",
             "Édouard", "Émile", "Étienne", "Fabien", "Félix", "Gaspard", "Grégoire", "Hugo", "Jérôme", "Joël",
             "Jules", "Laurent", "Léon", "Loïc", "Lucas", "Marius", "Mathis", "Noël", "Octave", "Pascal",
             "Philippe", "Quentin", "Raphaël", "Rémi", "Sébastien", "Simon", "Théo", "Thibault", "Victor", "Yann"]
NOMS = ["Arnaud", "Barbier", "Bertin", "Besson", "Bouvier", "Brunet", "Carpentier", "Chauvin", "Colin", "Delmas",
        "Dumas", "Duval", "Fabre", "Faure", "Fournier", "Gaillard", "Garnier", "Gautier", "Germain", "Guichard",
        "Hamon", "Joly", "Labbé", "Lacoste", "Lambert", "Laporte", "Lebrun", "Leclerc", "Lemoine", "Marchand",
        "Martel", "Masson", "Mercier", "Morel", "Noël", "Olivier", "Perrin", "Picard", "Poulain", "Renaud",
        "Rolland", "Roussel", "Sabatier", "Tessier", "Thibault", "Vasseur", "Vidal", "Vincent"]
VILLES = ["Annecy", "Auch", "Bordeaux", "Brest", "Lyon", "Dijon", "Montauban", "Nantes", "Colmar", "Paris",
          "Pau", "Périgueux", "Rennes", "Toulouse", "Saint-Malo", "Bruxelles", "Genève", "Montréal"]
RELATIONS = {"frere": "frère", "soeur": "sœur", "conjoint": "conjoint", "parent": "parent", "enfant": "enfant",
             "ami": "ami"}
INVERSE = {"frere": None, "soeur": None, "conjoint": "conjoint", "parent": "enfant", "enfant": "parent", "ami": "ami"}


def _telephone(rng: random.Random) -> str:
    return f"+33 6 39 98 {rng.randint(0, 99):02d} {rng.randint(0, 99):02d}"


def _courriel(prenom: str, nom: str, n: int = 0) -> str:
    import unicodedata
    simple = "".join(c for c in unicodedata.normalize("NFD", f"{prenom}.{nom}".lower()) if unicodedata.category(c) != "Mn")
    simple = "".join(c for c in simple if c.isalnum() or c == ".")
    return f"{simple}{n or ''}@example.org"


def _frere_ou_soeur(genre: str) -> str:
    return "soeur" if genre == "femme" else "frere"


def inventer(n: int, graine: int | None = None, variete: int = 50) -> list[dict]:
    """`n` personnes ; `variete` (0-100) : proportion de fiches incomplètes et de liens. Les liens sont des indices
    dans la liste rendue (`vers`), traduits en identifiants une fois les personnes enregistrées."""
    rng = random.Random(graine)
    n = max(1, min(int(n), 200))
    gens: list[dict] = []
    familles: list[str] = []
    for i in range(n):
        genre = rng.choice(["femme", "homme"])
        prenom = rng.choice(PRENOMS_F if genre == "femme" else PRENOMS_H)
        # une personne sur trois rejoint une famille déjà créée (même nom)
        if familles and rng.random() < 0.35:
            nom = rng.choice(familles)
        else:
            nom = rng.choice(NOMS)
            familles.append(nom)
        annee = rng.randint(1938, 2016)
        incomplete = rng.randint(0, 100) < variete // 3
        naissance = (f"{annee:04d}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}" if not incomplete
                     else rng.choice(["", f"--{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}", f"{annee:04d}"]))
        gens.append({"prenom": prenom, "nom": nom, "genre": genre, "naissance": naissance,
                     "ville": rng.choice(VILLES), "telephone": _telephone(rng) if rng.random() > 0.1 else "",
                     "courriel": _courriel(prenom, nom, i) if rng.random() > 0.3 else "", "liens": []})
    # liens : même nom = fratrie ou parent/enfant selon l'écart d'âge ; quelques conjoints et amis
    def annee_de(p):
        try:
            return int(p["naissance"][:4])
        except ValueError:
            return None
    for i, p in enumerate(gens):
        for j in range(i + 1, len(gens)):
            q = gens[j]
            if p["nom"] != q["nom"] or rng.randint(0, 100) > variete + 30:
                continue
            a, b = annee_de(p), annee_de(q)
            if a and b and abs(a - b) >= 20:
                aine, cadet = (i, j) if a < b else (j, i)
                gens[aine]["liens"].append({"vers": cadet, "relation": "enfant"})
                gens[cadet]["liens"].append({"vers": aine, "relation": "parent"})
            else:
                p["liens"].append({"vers": j, "relation": _frere_ou_soeur(q["genre"])})
                q["liens"].append({"vers": i, "relation": _frere_ou_soeur(p["genre"])})
    seuls = [i for i, p in enumerate(gens) if not p["liens"]]
    rng.shuffle(seuls)
    while len(seuls) >= 2 and rng.randint(0, 100) < variete + 20:
        a, b = seuls.pop(), seuls.pop()
        relation = "conjoint" if rng.random() < 0.6 else "ami"
        gens[a]["liens"].append({"vers": b, "relation": relation})
        gens[b]["liens"].append({"vers": a, "relation": relation})
    return gens


def pieges() -> list[dict]:
    """Les cas qui font trébucher : chacun porte une `note` qui dit ce qu'il teste."""
    return [
        {"prenom": "Marie", "nom": "Martin", "genre": "femme", "naissance": "1980-03-12", "ville": "Annecy",
         "telephone": "+33 6 39 98 10 01", "courriel": "", "liens": [], "note": "homonyme (1/2)"},
        {"prenom": "Marie", "nom": "Martin", "genre": "femme", "naissance": "1992-07-30", "ville": "Lyon",
         "telephone": "+33 6 39 98 10 02", "courriel": "", "liens": [], "note": "homonyme (2/2), autre personne"},
        {"prenom": "Jean-Édouard", "nom": "de La Tour-Ségur", "genre": "homme", "naissance": "1951-02-29",
         "ville": "Colmar", "telephone": "", "courriel": "", "liens": [],
         "note": "prénom composé, particule, trait d'union ; 29 février d'une année non bissextile"},
        {"prenom": "Anaïs", "nom": "Ågren-Øster", "genre": "femme", "naissance": "--05-14", "ville": "Genève",
         "telephone": "+41 22 000 00 00", "courriel": "", "liens": [], "note": "lettres étrangères, année inconnue"},
        {"prenom": "Zoé", "nom": "Lefèvre", "genre": "femme", "naissance": "1988", "ville": "Paris",
         "telephone": "+33 6 39 98 10 03", "courriel": "zoe.lefevre@example.org", "liens": [],
         "note": "année seule"},
        {"prenom": "Zoé", "nom": "Lefevre", "genre": "femme", "naissance": "1988-04-02", "ville": "Paris",
         "telephone": "+33639981003", "courriel": "zoe.lefevre@example.org", "liens": [],
         "note": "doublon de la précédente (accent perdu, numéro écrit autrement)"},
        {"prenom": "Maximilien-Alexandre", "nom": "Vandenbroucke-Delacroix-Montgolfier", "genre": "homme",
         "naissance": "1975-11-01", "ville": "Bruxelles", "telephone": "", "courriel": "", "liens": [],
         "note": "nom très long (débordements d'écran)"},
        {"prenom": "Lou", "nom": "", "genre": "", "naissance": "", "ville": "", "telephone": "", "courriel": "",
         "liens": [], "note": "prénom seul, genre inconnu, aucune date"},
        {"prenom": "Noël", "nom": "Noël", "genre": "homme", "naissance": "1960-12-25", "ville": "Auch",
         "telephone": "+33 6 39 98 10 04", "courriel": "", "liens": [], "note": "prénom = nom, né un jour férié"},
        {"prenom": "Gabriel", "nom": "Roux", "genre": "homme", "naissance": f"{date.today().year}-01-01",
         "ville": "Annecy", "telephone": "", "courriel": "", "liens": [], "note": "bébé de l'année"},
        {"prenom": "Germaine", "nom": "Roux", "genre": "femme", "naissance": "1919-06-06", "ville": "Annecy",
         "telephone": "", "courriel": "", "liens": [], "note": "centenaire"},
    ]


# ---------------------------------------------------------------- vraies fiches (lecture seule)

class CarnetInjoignable(Exception):
    pass


def lire_carnet(url: str, jeton: str, transport: httpx.BaseTransport | None = None) -> list[dict]:
    """Les personnes de carnet (adresse de Gazette : nom, prénom, naissance, genre). Rien d'autre n'est gardé."""
    if not url or not jeton:
        raise CarnetInjoignable("La copie depuis carnet n'est pas réglée (BAC_CARNET_URL et MAISON_JETON).")
    try:
        with httpx.Client(transport=transport, timeout=10) as client:
            r = client.get(f"{url}/gazette/personnes", headers={"Authorization": f"Bearer {jeton}"})
            r.raise_for_status()
            lues = r.json().get("personnes") or []
    except (httpx.HTTPError, ValueError) as exc:
        raise CarnetInjoignable(f"carnet ne répond pas ({type(exc).__name__}).") from exc
    res = []
    for p in lues:
        if not p.get("carnet_id"):
            continue
        nom_complet = str(p.get("nom_carnet") or p.get("nom") or "").strip()
        prenom = str(p.get("prenom") or "").strip()
        nom = nom_complet[len(prenom):].strip() if prenom and nom_complet.startswith(prenom) else nom_complet
        if p.get("naissance"):
            naissance = p["naissance"]
        elif p.get("jour") and p.get("mois"):
            naissance = f"--{int(p['mois']):02d}-{int(p['jour']):02d}"
        else:
            naissance = f"{int(p['annee']):04d}" if p.get("annee") else ""
        res.append({"carnet_id": str(p["carnet_id"]), "prenom": prenom, "nom": nom,
                    "genre": str(p.get("genre") or ""), "naissance": naissance})
    return res


def depuis_carnet(fiche: dict) -> dict:
    """Une vraie fiche devient une personne du Bac à sable : sans téléphone ni adresse, aucun lien."""
    return {"prenom": fiche["prenom"], "nom": fiche["nom"], "genre": fiche["genre"], "naissance": fiche["naissance"],
            "ville": "", "telephone": "", "courriel": "", "liens": []}
