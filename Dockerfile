# syntax=docker/dockerfile:1.7
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

# ---------- L'Anneau 0.18.0 (anneau @ 430873b) ----------
FROM python:3.12-slim-bookworm AS py-anneau
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/anneau.git#430873bd1b7991d9eb29551332cedc35f5cbe27c /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-anneau
COPY --from=py-anneau /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- carnet 3.3.2 (carnet @ 8df82ab) ----------
FROM python:3.12-slim-bookworm AS py-carnet
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/carnet.git#8df82ab90755fc5013a9d1c90b97f8f90796062a /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-carnet
COPY --from=py-carnet /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Chambre noire 0.9.2 (chambre-noire @ 1e624a8) ----------
FROM python:3.12-slim-bookworm AS py-chambre-noire
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/chambre-noire.git#1e624a8c0faa8c334468289731f77060b096c8c6 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-chambre-noire
COPY --from=py-chambre-noire /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Comptoir 0.8.2 (comptoir @ 6cf994d) ----------
FROM python:3.12-slim-bookworm AS py-comptoir
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/comptoir.git#6cf994dcaf5dfb2567030618032b155f95e0fc12 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-comptoir
COPY --from=py-comptoir /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Douze points 1.14.1 (douze-points @ 816690e) ----------
FROM python:3.12-slim-bookworm AS py-douze-points
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/douze-points.git#816690ec7f539c273256465d391fe75a5bb7c635 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-douze-points
COPY --from=py-douze-points /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Gazette 0.30.1 (gazette @ 442c70b) ----------
FROM python:3.12-slim-bookworm AS py-gazette
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/gazette.git#442c70be204e066692f8ff5e348db95081a285bc /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-gazette
COPY --from=py-gazette /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Kit d'urgence 2.7.2 (kit-urgence @ e8e8aba) ----------
FROM python:3.12-slim-bookworm AS py-kit-urgence
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/kit-urgence.git#e8e8aba279bf30f49b4ef3a367da0ffe01a4b233 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-kit-urgence
COPY --from=py-kit-urgence /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Millésime 2.16.1 (millesime @ 67d78cd) ----------
FROM python:3.12-slim-bookworm AS py-millesime
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/millesime.git#67d78cd1d3281d942cc164a49d585d9271a16ddf /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-millesime
COPY --from=py-millesime /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Scriptorium 0.8.2 (scriptorium @ a3ff141) ----------
FROM python:3.12-slim-bookworm AS py-scriptorium
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/scriptorium.git#a3ff1412b85fd6ffef86f38738023f9782d454a4 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-scriptorium
COPY --from=py-scriptorium /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Sillage 0.21.2 (sillage @ 4479351) ----------
FROM python:3.12-slim-bookworm AS py-sillage
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/sillage.git#4479351334e4fc58cd927be36a93da174199bf9a /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-sillage
COPY --from=py-sillage /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Transhumance 0.9.5 (transhumance @ ebd0275) ----------
FROM python:3.12-slim-bookworm AS py-transhumance
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/transhumance.git#ebd0275f1218e0db2a8e27905ef17f8e6e124ed5 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-transhumance
COPY --from=py-transhumance /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Éphéméride 3.3.1 (verif-dates-photos @ 8879db4) ----------
FROM python:3.12-slim-bookworm AS py-ephemeride
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/verif-dates-photos.git#8879db43b50c09fe9f3557c16d2941c767ef639f /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-ephemeride
COPY --from=py-ephemeride /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Image d'exécution ----------
FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.title="bac-a-sable" \
      org.opencontainers.image.description="Bac à sable : les applis maison lancées à la demande sur une fausse maison" \
      org.opencontainers.image.source="https://github.com/baloodusudouest/bac-a-sable"

# Paquets système de toutes les applis embarquées : gosu, tzdata (toutes) ; polices (carnet, kit) ;
# tesseract, pango, harfbuzz (Scriptorium, Kit) ; qpdf, pandoc (Kit) ; exiftool, ffmpeg (Éphéméride)
COPY --from=pandoc /pandoc.deb /tmp/pandoc.deb
RUN apt-get update && apt-get install -y --no-install-recommends \
        gosu tzdata fonts-dejavu-core tesseract-ocr libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
        libharfbuzz-subset0 qpdf libimage-exiftool-perl ffmpeg /tmp/pandoc.deb \
    && rm -rf /var/lib/apt/lists/* /tmp/pandoc.deb

COPY --from=roues /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY --from=commun /commun /applis/_commun
COPY --from=py-anneau /src /applis/anneau/src
COPY --from=py-anneau /site /applis/anneau/site
COPY --from=ui-anneau /out /applis/anneau/src/app/static
COPY --from=py-carnet /src /applis/carnet/src
COPY --from=py-carnet /site /applis/carnet/site
COPY --from=ui-carnet /out /applis/carnet/src/app/static
COPY --from=py-chambre-noire /src /applis/chambre-noire/src
COPY --from=py-chambre-noire /site /applis/chambre-noire/site
COPY --from=ui-chambre-noire /out /applis/chambre-noire/src/app/static
COPY --from=py-comptoir /src /applis/comptoir/src
COPY --from=py-comptoir /site /applis/comptoir/site
COPY --from=ui-comptoir /out /applis/comptoir/src/app/static
COPY --from=py-douze-points /src /applis/douze-points/src
COPY --from=py-douze-points /site /applis/douze-points/site
COPY --from=ui-douze-points /out /applis/douze-points/src/app/static
COPY --from=py-gazette /src /applis/gazette/src
COPY --from=py-gazette /site /applis/gazette/site
COPY --from=ui-gazette /out /applis/gazette/src/app/static
COPY --from=py-kit-urgence /src /applis/kit-urgence/src
COPY --from=py-kit-urgence /site /applis/kit-urgence/site
COPY --from=ui-kit-urgence /out /applis/kit-urgence/src/app/static
COPY --from=py-millesime /src /applis/millesime/src
COPY --from=py-millesime /site /applis/millesime/site
COPY --from=ui-millesime /out /applis/millesime/src/app/static
COPY --from=py-scriptorium /src /applis/scriptorium/src
COPY --from=py-scriptorium /site /applis/scriptorium/site
COPY --from=ui-scriptorium /out /applis/scriptorium/src/app/static
COPY --from=py-sillage /src /applis/sillage/src
COPY --from=py-sillage /site /applis/sillage/site
COPY --from=ui-sillage /out /applis/sillage/src/app/static
COPY --from=py-transhumance /src /applis/transhumance/src
COPY --from=py-transhumance /site /applis/transhumance/site
COPY --from=ui-transhumance /out /applis/transhumance/src/app/static
COPY --from=py-ephemeride /src /applis/ephemeride/src
COPY --from=py-ephemeride /site /applis/ephemeride/site
COPY --from=ui-ephemeride /out /applis/ephemeride/src/app/static
# Chromium de Gazette, installé par sa propre version de Playwright
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN if [ -d /applis/gazette/site/playwright ]; then \
        PYTHONPATH=/applis/gazette/site python -m playwright install --with-deps chromium \
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

ENV TZ=Europe/Paris \
    BAC_DATA=/data \
    BAC_APPLIS=/applis \
    BAC_PORT=8104 \
    PYTHONUNBUFFERED=1

EXPOSE 8104 8110-8121
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8104/health')" || exit 1
ENTRYPOINT ["/entrypoint.sh"]
