"""Soirée Douze points simulée.

1. preparer() : la soirée est montée par l'API de l'appli simulée, comme le ferait l'hôte (invités venus des
   personnes du scénario, concours, chansons inventées, ouverture).
2. Téléphones simulés : une tâche par téléphone qui choisit son prénom puis note et commente au fil du temps,
   selon un profil, range son classement et l'envoie. Les autres prénoms restent libres pour de vrais iPhone.
3. Mur : chaque téléphone simulé s'affiche dans l'écran invité réel (lien « #saisie=<jeton> » de l'appli).

Les chansons sont inventées (pays réels, artistes et titres fictifs).
"""
from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field

import httpx

PAYS = [("France", "FR"), ("Suède", "SE"), ("Italie", "IT"), ("Espagne", "ES"), ("Norvège", "NO"), ("Ukraine", "UA"),
        ("Portugal", "PT"), ("Finlande", "FI"), ("Irlande", "IE"), ("Grèce", "GR"), ("Croatie", "HR"),
        ("Suisse", "CH"), ("Belgique", "BE"), ("Pays-Bas", "NL"), ("Islande", "IS"), ("Pologne", "PL"),
        ("Lituanie", "LT"), ("Estonie", "EE"), ("Chypre", "CY"), ("Malte", "MT"), ("Australie", "AU"),
        ("Autriche", "AT"), ("Arménie", "AM"), ("Moldavie", "MD"), ("Serbie", "RS"), ("Danemark", "DK")]
ARTISTES = ["Lumen Vale", "Les Grenadines", "Kasimir & Nova", "Aurore Boréale", "Velvet Comète", "Mira Solstice",
            "Os Faróis", "Nordlys", "Duo Cassiopée", "Iris Volta", "The Paper Kites of Elm", "Tamsin Rook",
            "Zorya", "Albatros Club", "Selene Marr", "Kid Equinoxe", "Mélusine", "Brume", "Ondine Rae",
            "Polaris Kids", "Saffron Lane", "Fata Morgana", "Cobalt Rose", "Halvard", "Nymphéa", "Ostara"]
MOTS = ["Lumière", "Vertige", "Tempête", "Minuit", "Comète", "Horizon", "Satellite", "Brasier", "Écho", "Marée",
        "Rêverie", "Volcan", "Mirage", "Aurore", "Cristal", "Tonnerre", "Sirène", "Phénix", "Électrique", "Velours"]
COMMENTAIRES = {
    "haut": ["Frissons !", "On tient la gagnante", "Le refrain reste en tête", "Mise en scène dingue", "Douze points direct",
             "Quelle voix", "J'ai dansé sur le canapé"],
    "milieu": ["Sympa sans plus", "Bien chanté", "Le pont est réussi", "Un peu long", "Jolie robe", "Ça passe"],
    "bas": ["Pas pour moi", "Trop de fumée", "Faux dans le refrain", "On a vu mieux", "Pause toilettes", "Bof"],
}
PROFILS = {"genereux": "Généreux", "severe": "Sévère", "fan": "Fan d'un pays", "hasard": "Au hasard",
           "taiseux": "Ne commente jamais"}


def chansons(n: int, graine: int | None = None) -> list[dict]:
    rng = random.Random(graine)
    pays = rng.sample(PAYS, k=min(max(int(n), 1), len(PAYS)))
    artistes = rng.sample(ARTISTES, k=len(pays))
    return [{"pays": p, "code_pays": c, "artiste": a, "titre": f"{rng.choice(MOTS)}" + rng.choice(["", " " + rng.choice(MOTS).lower()])}
            for (p, c), a in zip(pays, artistes)]


def note_pour(profil: str, rng: random.Random, pays: str, prefere: str, pas: float) -> float:
    if profil == "genereux":
        v = rng.gauss(15, 3)
    elif profil == "severe":
        v = rng.gauss(8, 3.5)
    elif profil == "fan":
        v = 20 if pays == prefere else rng.gauss(10, 4)
    else:
        v = rng.uniform(0, 20)
    v = min(20.0, max(0.0, v))
    return round(round(v / pas) * pas, 2)


def commentaire_pour(note: float, profil: str, rng: random.Random) -> str:
    if profil == "taiseux" or rng.random() < 0.35:
        return ""
    bande = "haut" if note >= 15 else ("milieu" if note >= 9 else "bas")
    return rng.choice(COMMENTAIRES[bande])


@dataclass
class Telephone:
    participation_id: int
    prenom: str
    profil: str
    prefere: str = ""
    jeton: str = ""
    notees: int = 0
    etat: str = "en attente"
    erreur: str = ""


@dataclass
class Soiree:
    soiree_id: int = 0
    jeton_invite: str = ""
    telephones: list[Telephone] = field(default_factory=list)
    libres: list[dict] = field(default_factory=list)      # prénoms laissés aux vrais iPhone
    chansons: list[dict] = field(default_factory=list)
    taches: list[asyncio.Task] = field(default_factory=list)
    message: str = ""


class Regie:
    """Parle à Douze points comme l'hôte (session tenue par le relais) et comme les téléphones (porte invité)."""

    def __init__(self, relais):
        self.relais = relais
        self.soiree = Soiree()

    async def _client(self) -> httpx.AsyncClient:
        if not self.relais.session:
            async with httpx.AsyncClient(timeout=20) as provisoire:
                await self.relais.ouvrir_session(provisoire)
        return httpx.AsyncClient(base_url=self.relais.base, timeout=20, cookies=self.relais.session)

    async def preparer(self, personnes: list[dict], reglages: dict) -> dict:
        """Monte la soirée. Réglages : telephones (nb simulés), chansons (nb), profils (liste), pas (1, 0.5, 0.25)."""
        await self.arreter()
        graine = reglages.get("graine")
        rng = random.Random(graine)
        n_chansons = int(reglages.get("chansons", 12))
        async with await self._client() as c:
            concours = (await c.get("/api/concours")).json()
            actifs = [x["nom"] for x in concours if x.get("actif")]
            nom_concours = actifs[0] if actifs else "Concours simulé"
            if not actifs:
                (await c.post("/api/concours", json={"nom": nom_concours})).raise_for_status()
            r = await c.post("/api/soirees", json={"concours": nom_concours, "annee": int(reglages.get("annee", 2027)),
                                                   "emission": "finale", "nom": reglages.get("nom") or "Soirée simulée",
                                                   "ville": "Bac à sable"})
            r.raise_for_status()
            sid = r.json()["id"]
            liste = chansons(n_chansons, graine)
            (await c.put(f"/api/soirees/{sid}/chansons", json={"chansons": liste})).raise_for_status()
            ids = []
            vus: set[str] = set()
            for p in personnes:
                prenom = (p.get("prenom") or "Invité").strip()[:30]
                if prenom.lower() in vus:
                    prenom = f"{prenom} {(p.get('nom') or '?')[:1]}."
                vus.add(prenom.lower())
                r = await c.post("/api/invites", json={"prenom": prenom})
                if r.status_code == 409:            # déjà dans la liste (rejouer) : on le retrouve
                    existants = (await c.get("/api/invites")).json()
                    trouve = next((x for x in existants if x["prenom"].lower() == prenom.lower()), None)
                    if trouve:
                        ids.append(trouve["id"])
                    continue
                r.raise_for_status()
                ids.append(r.json()["id"])
            if not ids:
                raise ValueError("Il faut au moins une personne dans le scénario pour une soirée.")
            (await c.put(f"/api/soirees/{sid}/attendus", json={"invites": ids})).raise_for_status()
            (await c.post(f"/api/soirees/{sid}/ouvrir")).raise_for_status()
            detail = (await c.get(f"/api/soirees/{sid}")).json()
        participants = detail.get("participants") or []
        n_sim = max(0, min(int(reglages.get("telephones", len(participants))), len(participants)))
        profils = [x for x in (reglages.get("profils") or list(PROFILS)) if x in PROFILS] or list(PROFILS)
        self.soiree = Soiree(soiree_id=sid, jeton_invite=detail["jeton_invite"], chansons=detail.get("chansons") or [])
        for i, part in enumerate(participants):
            pid = part.get("id") or part.get("participation_id")
            prenom = part.get("prenom", "?")
            if i < n_sim:
                profil = profils[i % len(profils)]
                self.soiree.telephones.append(Telephone(pid, prenom, profil, prefere=rng.choice(liste)["pays"]))
            else:
                self.soiree.libres.append({"participation_id": pid, "prenom": prenom})
        return self.resume()

    def resume(self) -> dict:
        s = self.soiree
        return {"soiree_id": s.soiree_id, "jeton_invite": s.jeton_invite, "chansons": len(s.chansons),
                "message": s.message, "libres": s.libres,
                "telephones": [{"participation_id": t.participation_id, "prenom": t.prenom, "profil": t.profil,
                                "profil_nom": PROFILS[t.profil], "prefere": t.prefere if t.profil == "fan" else "",
                                "jeton": t.jeton, "notees": t.notees, "etat": t.etat, "erreur": t.erreur}
                               for t in s.telephones],
                "en_cours": any(not t.done() for t in s.taches)}

    async def jouer(self, tempo: float = 4.0, envoyer: bool = True) -> dict:
        """Lance les téléphones : `tempo` secondes en moyenne entre deux notes d'un même téléphone (0 : avance rapide)."""
        s = self.soiree
        if not s.jeton_invite:
            raise ValueError("Prépare d'abord la soirée.")
        for t in s.taches:
            t.cancel()
        s.taches = [asyncio.create_task(self._telephone(t, tempo, envoyer)) for t in s.telephones]
        return self.resume()

    async def arreter(self) -> None:
        for t in self.soiree.taches:
            t.cancel()
        self.soiree.taches = []

    async def _telephone(self, t: Telephone, tempo: float, envoyer: bool) -> None:
        rng = random.Random(t.participation_id * 7919)
        base = f"/invite/{self.soiree.jeton_invite}/api"
        try:
            async with httpx.AsyncClient(base_url=self.relais.base, timeout=20) as c:
                if not t.jeton:
                    t.etat = "choisit son prénom"
                    r = await c.post(f"{base}/prenom", json={"participation_id": t.participation_id})
                    r.raise_for_status()
                    t.jeton = r.json()["jeton_telephone"]
                entetes = {"X-Telephone": t.jeton}
                etat = (await c.get(f"{base}/etat", headers=entetes)).json()
                pas = float(etat.get("pas_note") or 1)
                ordre = list(etat.get("chansons") or [])
                deja = set((etat.get("moi") or {}).get("notes", {}).keys())
                t.etat = "note"
                for chanson in ordre:
                    if str(chanson["id"]) in deja:
                        continue
                    if tempo:
                        await asyncio.sleep(max(0.2, rng.gauss(tempo, tempo / 3)))
                    note = note_pour(t.profil, rng, chanson["pays"], t.prefere, pas)
                    r = await c.put(f"{base}/note", headers=entetes,
                                    json={"chanson_id": chanson["id"], "valeur": note,
                                          "commentaire": commentaire_pour(note, t.profil, rng)})
                    if r.status_code == 409:      # notes closes par l'hôte
                        t.etat = "notes closes"
                        return
                    r.raise_for_status()
                    t.notees += 1
                if envoyer:
                    if tempo:
                        await asyncio.sleep(rng.uniform(0.5, tempo))
                    (await c.post(f"{base}/envoyer", headers=entetes)).raise_for_status()
                    t.etat = "envoyé"
                else:
                    t.etat = "a noté, pas envoyé"
        except asyncio.CancelledError:
            t.etat = "arrêté"
            raise
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            t.etat = "erreur"
            t.erreur = str(exc)[:200]
