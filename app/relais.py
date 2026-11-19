"""Relais devant chaque appli simulée (un port publié par appli).

Pourquoi : un navigateur ne sépare pas les cookies par port. Sans relais, une appli simulée (l'Anneau surtout)
recevrait le vrai cookie de connexion et pourrait poser le sien par-dessus, ce qui déconnecterait des vraies applis.

Ce que fait le relais, pour chaque requête :
1. il vérifie que le navigateur est connecté au Bac à sable (cookie du Bac à sable ou cookie commun) ; seule
   exception, la porte des invités de Douze points (/invite/…), pour les vrais téléphones ;
2. il démarre l'appli si elle dort ;
3. il retire TOUS les cookies du navigateur et présente à l'appli sa propre session simulée (connexion faite par
   le relais lui-même, avec le mot de passe de démonstration de l'appli) ;
4. il retire tous les `Set-Cookie` de la réponse : aucune appli simulée ne touche aux cookies du navigateur ;
5. il ajoute le bandeau « Bac à sable » en haut des pages.
"""
from __future__ import annotations

import asyncio
import logging
from http.cookies import SimpleCookie

import httpx
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response, StreamingResponse
from starlette.websockets import WebSocket

journal = logging.getLogger("bac-a-sable.relais")

SAUTER = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers",
          "transfer-encoding", "upgrade", "content-length", "content-encoding", "set-cookie"}
BANDEAU = (
    '<div id="bac-a-sable-bandeau" title="{nom} {version} dans le Bac à sable : rien ne sort" '
    'style="position:fixed;z-index:2147483647;left:50%;top:max(4px,env(safe-area-inset-top));white-space:nowrap;'
    'transform:translateX(-50%);pointer-events:none;font:600 10px/1.6 Inter,system-ui,sans-serif;'
    'letter-spacing:.04em;color:#062a2e;background:repeating-linear-gradient(135deg,#5cc6d6 0 10px,#7fd4e0 10px 20px);'
    'padding:1px 10px;border-radius:999px;box-shadow:0 1px 6px rgba(0,0,0,.35);opacity:.92">'
    'Bac à sable</div>')


def portes_publiques(ident: str, chemin: str) -> bool:
    """Ce qu'un vrai téléphone d'invité peut ouvrir sans être connecté au Bac à sable."""
    if ident != "douze-points":
        return False
    return chemin.startswith(("/invite/", "/assets/", "/favicon", "/icone", "/manifest", "/apple-touch"))


class Relais:
    """Un relais par appli. `connecte(cookies)` dit si le navigateur est connecté au Bac à sable."""

    def __init__(self, gestionnaire, ident: str, connecte):
        self.g = gestionnaire
        self.ident = ident
        self.appli = gestionnaire.applis[ident]
        self.connecte = connecte
        self.session: dict[str, str] = {}      # le cookie de session de l'appli simulée, tenu par le relais
        self._verrou = asyncio.Lock()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.appli.port_local}"

    async def ouvrir_session(self, client: httpx.AsyncClient) -> None:
        """Le relais se connecte à l'appli simulée avec son mot de passe de démonstration."""
        async with self._verrou:
            r = await client.post(f"{self.base}/api/connexion", json={"mot_de_passe": self.appli.mot_de_passe})
            if r.status_code >= 400:
                raise RuntimeError(f"connexion refusée par {self.appli.nom} ({r.status_code})")
            cookies = SimpleCookie()
            for entete in r.headers.get_list("set-cookie"):
                cookies.load(entete)
            self.session = {k: m.value for k, m in cookies.items() if m.value}

    def entetes_amont(self, request: Request) -> dict:
        entetes = {k: v for k, v in request.headers.items() if k.lower() not in SAUTER | {"cookie", "host"}}
        entetes["accept-encoding"] = "identity"
        entetes["x-forwarded-host"] = request.headers.get("host", "")
        entetes["x-forwarded-proto"] = request.url.scheme
        if self.session:
            entetes["cookie"] = "; ".join(f"{k}={v}" for k, v in self.session.items())
        return entetes

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            return
        if scope["type"] == "websocket":
            await self.websocket(WebSocket(scope, receive, send))
            return
        request = Request(scope, receive)
        reponse = await self.http(request)
        await reponse(scope, receive, send)

    async def preparer(self, request: Request) -> Response | None:
        chemin = request.url.path
        if not portes_publiques(self.ident, chemin) and not self.connecte(request.cookies):
            adresse = f"{request.url.scheme}://{request.url.hostname}:{self.g.cfg_port_bac}/"
            return HTMLResponse(
                f'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
                f'<body style="background:#151311;color:#f2ece2;font:16px system-ui;padding:2rem">'
                f'<p>Connecte-toi d\'abord au <a style="color:#5cc6d6" href="{adresse}">Bac à sable</a>, '
                f'à la même adresse, puis reviens ici.</p>', status_code=401)
        if self.g.bloque:
            return HTMLResponse(f"<p>{self.g.bloque}</p>", status_code=503)
        if not self.g.etats[self.ident].vivant():
            try:
                adresse = f"{request.url.scheme}://{request.headers.get('host', '')}"
                await self.g.demarrer(self.ident, adresse_publique=adresse)
                self.session = {}
            except RuntimeError as exc:
                return HTMLResponse(f"<p>{exc}</p>", status_code=503)
        self.g.toucher(self.ident)
        return None

    async def http(self, request: Request) -> Response:
        refus = await self.preparer(request)
        if refus is not None:
            return refus
        corps = await request.body()
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=5)) as client:
            if not self.session:
                try:
                    await self.ouvrir_session(client)
                except (RuntimeError, httpx.HTTPError) as exc:
                    journal.warning("%s : %s", self.ident, exc)
            for essai in (1, 2):
                amont = client.build_request(request.method, f"{self.base}{request.url.path}",
                                             params=request.url.query, headers=self.entetes_amont(request),
                                             content=corps)
                r = await client.send(amont, stream=True)
                # session perdue (« Se déconnecter » dans l'appli simulée) : nouvelle connexion, une fois
                if r.status_code == 401 and essai == 1 and request.url.path.startswith("/api/") \
                        and request.url.path != "/api/connexion":
                    await r.aclose()
                    try:
                        await self.ouvrir_session(client)
                    except (RuntimeError, httpx.HTTPError):
                        break
                    continue
                break
            entetes = [(k, v) for k, v in r.headers.multi_items() if k.lower() not in SAUTER]
            type_ = r.headers.get("content-type", "")
            if "text/html" in type_:
                texte = (await r.aread()).decode(r.encoding or "utf-8", errors="replace")
                await r.aclose()
                bandeau = BANDEAU.format(nom=self.appli.nom, version=self.appli.version)
                texte = texte.replace("</body>", bandeau + "</body>", 1) if "</body>" in texte else texte + bandeau
                return Response(texte, status_code=r.status_code, headers=dict(entetes), media_type="text/html")
            contenu = await r.aread()
            await r.aclose()
            return Response(contenu, status_code=r.status_code, headers=dict(entetes))

    async def websocket(self, ws: WebSocket) -> None:
        """Relais WebSocket (aucune appli n'en utilise aujourd'hui ; prêt si l'une s'y met)."""
        if not portes_publiques(self.ident, ws.url.path) and not self.connecte(ws.cookies):
            await ws.close(code=4401)
            return
        try:
            import websockets
        except ImportError:
            await ws.close(code=1011)
            return
        await ws.accept()
        cible = f"ws://127.0.0.1:{self.appli.port_local}{ws.url.path}"
        if ws.url.query:
            cible += "?" + ws.url.query
        entetes = [("cookie", "; ".join(f"{k}={v}" for k, v in self.session.items()))] if self.session else []
        try:
            async with websockets.connect(cible, additional_headers=entetes) as amont:
                async def vers_amont():
                    while True:
                        message = await ws.receive()
                        if message["type"] == "websocket.disconnect":
                            await amont.close()
                            return
                        await amont.send(message.get("text") if message.get("text") is not None else message.get("bytes"))

                async def vers_navigateur():
                    async for message in amont:
                        await (ws.send_text(message) if isinstance(message, str) else ws.send_bytes(message))
                await asyncio.gather(vers_amont(), vers_navigateur())
        except Exception:  # noqa: BLE001 — fin de connexion d'un côté ou de l'autre
            pass
        finally:
            try:
                await ws.close()
            except RuntimeError:
                pass


async def servir(relais: list[Relais], hote: str = "0.0.0.0") -> list[asyncio.Task]:
    """Un serveur uvicorn par port, dans la boucle du Bac à sable."""
    import uvicorn
    taches = []
    for r in relais:
        # log_config et log_level à None : ne pas toucher au journal commun d'uvicorn (sinon le niveau « warning »
        # s'applique aussi au serveur du Bac à sable et masque « Application startup complete », 0.1.1)
        config = uvicorn.Config(r, host=hote, port=r.appli.port, log_config=None, log_level=None, lifespan="off",
                                proxy_headers=True, access_log=False)
        serveur = uvicorn.Server(config)
        # _serve : sans reprendre les signaux d'arrêt (c'est le serveur du Bac à sable qui les tient)
        lancer = getattr(serveur, "_serve", None) or serveur.serve
        taches.append(asyncio.create_task(lancer()))
    return taches
