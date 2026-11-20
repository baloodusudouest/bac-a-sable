"""Fabrique le Dockerfile du Bac à sable depuis applis.yaml.

Usage : python tools/dockerfile.py            (écrit ./Dockerfile)
        python tools/dockerfile.py --verifier (échoue si le Dockerfile n'est pas à jour : la CI s'en sert)

Chaque appli embarquée est construite depuis son dépôt public, au commit noté (`sha`) :
- étape py-<appli> : code source (avec tests/ et tools/, d'où viennent les lanceurs de démonstration) et
  dépendances Python installées à part dans /site (une appli = un jeu de versions, aucun conflit) ;
- étape ui-<appli> : son interface Svelte bâtie ;
- image finale : /applis/<appli>/src (code + interface dans app/static) et /applis/<appli>/site.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent

ENTETE = """# syntax=docker/dockerfile:1.7
# ============================================================================================================
# FICHIER FABRIQUÉ par tools/dockerfile.py depuis applis.yaml : ne pas le modifier à la main.
# ============================================================================================================

# ---------- Interface du Bac à sable ----------
FROM node:22-bookworm-slim AS interface
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN mkdir -p /app && npx vite build --outDir /app/static --emptyOutDir

# ---------- Dépendances du Bac à sable ----------
FROM python:3.12-slim-bookworm AS roues
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---------- Outils communs des lanceurs de démonstration (ils importent des modules de tests) ----------
FROM python:3.12-slim-bookworm AS commun
RUN pip install --no-cache-dir --target /commun pytest==8.4.2

# ---------- pandoc 3.1.3 pour Kit d'urgence (paquet amd64 du projet pandoc, comme son image) ----------
FROM python:3.12-slim-bookworm AS pandoc
ADD https://github.com/jgm/pandoc/releases/download/3.1.3/pandoc-3.1.3-1-amd64.deb /pandoc.deb
"""

APPLI = """
# ---------- {nom} {version} ({depot} @ {court}) ----------
FROM python:3.12-slim-bookworm AS py-{id}
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/{depot}.git#{sha} /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-{id}
COPY --from=py-{id} /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir
"""

FINALE = """
# ---------- Image d'exécution ----------
FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.title="bac-a-sable" \\
      org.opencontainers.image.description="Bac à sable : les applis maison lancées à la demande sur une fausse maison" \\
      org.opencontainers.image.source="https://github.com/baloodusudouest/bac-a-sable"

# Paquets système de toutes les applis embarquées : gosu, tzdata (toutes) ; polices (carnet, kit) ;
# tesseract, pango, harfbuzz (Scriptorium, Kit) ; qpdf, pandoc (Kit) ; exiftool, ffmpeg (Éphéméride)
COPY --from=pandoc /pandoc.deb /tmp/pandoc.deb
RUN apt-get update && apt-get install -y --no-install-recommends \\
        gosu tzdata fonts-dejavu-core tesseract-ocr libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \\
        libharfbuzz-subset0 qpdf libimage-exiftool-perl ffmpeg /tmp/pandoc.deb \\
    && rm -rf /var/lib/apt/lists/* /tmp/pandoc.deb

COPY --from=roues /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY --from=commun /commun /applis/_commun
{copies}
# Chromium de Gazette, installé par sa propre version de Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN if [ -d /applis/gazette/site/playwright ]; then \\
        PYTHONPATH=/applis/gazette/site python -m playwright install --with-deps chromium \\
        && chmod -R a+rX /ms-playwright && rm -rf /var/lib/apt/lists/*; fi

WORKDIR /app
COPY applis.yaml ./applis.yaml
COPY app ./app
COPY garde ./garde
COPY lanceurs ./lanceurs
COPY tests ./tests
COPY docs/flux-maison.json ./docs/flux-maison.json
COPY --from=interface /app/static ./app/static
COPY entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh && chmod -R a+rX /applis /app

ENV TZ=Europe/Paris \\
    BAC_DATA=/data \\
    BAC_APPLIS=/applis \\
    BAC_PORT=8104 \\
    PYTHONUNBUFFERED=1

EXPOSE 8104 {ports}
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \\
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8104/health')" || exit 1
ENTRYPOINT ["/entrypoint.sh"]
"""

COPIE = """COPY --from=py-{id} /src /applis/{id}/src
COPY --from=py-{id} /site /applis/{id}/site
COPY --from=ui-{id} /out /applis/{id}/src/app/static"""


def fabriquer() -> str:
    applis = (yaml.safe_load((RACINE / "applis.yaml").read_text(encoding="utf-8")) or {})["applis"]
    morceaux = [ENTETE]
    copies = []
    for ident, a in applis.items():
        morceaux.append(APPLI.format(id=ident, nom=a["nom"], version=a["version"], depot=a["depot"], sha=a["sha"],
                                     court=a["sha"][:7]))
        copies.append(COPIE.format(id=ident))
    ports = sorted(int(a["port"]) for a in applis.values())
    morceaux.append(FINALE.format(copies="\n".join(copies), ports=f"{ports[0]}-{ports[-1]}"))
    return "".join(morceaux)


if __name__ == "__main__":
    texte = fabriquer()
    cible = RACINE / "Dockerfile"
    if "--verifier" in sys.argv:
        if cible.read_text(encoding="utf-8") != texte:
            sys.exit("Dockerfile pas à jour : lance python tools/dockerfile.py")
        print("Dockerfile à jour.")
    else:
        cible.write_text(texte, encoding="utf-8")
        print(f"Dockerfile écrit ({len(applis_ := texte.splitlines())} lignes).")
