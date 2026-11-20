"""0.4.0 — faux annuaire de l'Anneau, pour les applis simulées (conseil, point 6).

Les applis maison cherchent les adresses des autres dans l'annuaire de l'Anneau (`maison.Annuaire`, GET
/externe/services, jeton commun, adresse MAISON_ANNEAU_URL ; défaut : l'Anneau de la vraie stack). Chaque appli
simulée reçoit MAISON_ANNEAU_URL = ce faux annuaire, servi par le Bac à sable en 127.0.0.1 seulement (jamais publié),
avec le jeton commun simulé. Il donne pour chaque appli l'adresse de son relais vue par le navigateur (même hôte que
l'écran du Bac à sable, port de l'appli). Pas de tuiles, de voyants ni de sauvegarde simulés.
"""
from __future__ import annotations

import hmac

from starlette.requests import Request
from starlette.responses import JSONResponse


class FauxAnnuaire:
    def __init__(self, gestionnaire):
        self.g = gestionnaire

    def services(self) -> list[dict]:
        hote = self.g.hote or "localhost"
        return [{"nom": a.nom, "id": a.id, "locale": f"http://{hote}:{a.port}", "privee": "", "simule": True}
                for a in self.g.applis.values()]

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            return
        if scope["type"] != "http":
            return
        request = Request(scope, receive)
        if request.url.path == "/health":
            reponse = JSONResponse({"ok": True, "simule": True})
        elif request.url.path == "/externe/services" and request.method == "GET":
            propose = request.headers.get("authorization", "")
            if hmac.compare_digest(propose.encode(), f"Bearer {self.g.jeton}".encode()):
                reponse = JSONResponse({"services": self.services(), "simule": True})
            else:
                reponse = JSONResponse({"detail": "Introuvable."}, status_code=404)
        else:
            reponse = JSONResponse({"detail": "Introuvable."}, status_code=404)
        await reponse(scope, receive, send)


async def servir(annuaire: FauxAnnuaire, port: int):
    """Le faux annuaire écoute en 127.0.0.1 seulement : seules les applis simulées (et le Bac à sable) le joignent."""
    import asyncio

    import uvicorn
    config = uvicorn.Config(annuaire, host="127.0.0.1", port=port, log_config=None, log_level=None, lifespan="off",
                            access_log=False)
    serveur = uvicorn.Server(config)
    lancer = getattr(serveur, "_serve", None) or serveur.serve
    return asyncio.create_task(lancer())
