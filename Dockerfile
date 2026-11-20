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

# ---------- L'Anneau 0.16.1 (anneau @ f2a8114) ----------
FROM python:3.12-slim-bookworm AS py-anneau
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/anneau.git#f2a811486712e361b9d1111fcc7d5029198cdcbe /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-anneau
COPY --from=py-anneau /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- carnet 3.3.1 (carnet @ b4ed56e) ----------
FROM python:3.12-slim-bookworm AS py-carnet
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/carnet.git#b4ed56e4e4b50a38ff36211a116f905c3bb51b84 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-carnet
COPY --from=py-carnet /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Chambre noire 0.9.1 (chambre-noire @ 39434ab) ----------
FROM python:3.12-slim-bookworm AS py-chambre-noire
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/chambre-noire.git#39434ab2d6368b5eacd2dca5448ad97d4a850190 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-chambre-noire
COPY --from=py-chambre-noire /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Comptoir 0.8.1 (comptoir @ 7ba6c47) ----------
FROM python:3.12-slim-bookworm AS py-comptoir
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/comptoir.git#7ba6c47a1404bf97ea3baae249a0cccee184420a /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-comptoir
COPY --from=py-comptoir /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Douze points 1.10.3 (douze-points @ e5dbf81) ----------
FROM python:3.12-slim-bookworm AS py-douze-points
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/douze-points.git#e5dbf8156aa11c2968c6225a63a00a0cd2c1959c /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-douze-points
COPY --from=py-douze-points /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Gazette 0.29.1 (gazette @ 27e96b5) ----------
FROM python:3.12-slim-bookworm AS py-gazette
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/gazette.git#27e96b5e6e33e31d5ec99f6ef061d8d8f8afa564 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-gazette
COPY --from=py-gazette /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Kit d'urgence 2.7.1 (kit-urgence @ 3ff9e86) ----------
FROM python:3.12-slim-bookworm AS py-kit-urgence
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/kit-urgence.git#3ff9e86906da59cc9e5a66db2a19128ba8e3a5fb /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-kit-urgence
COPY --from=py-kit-urgence /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Millésime 2.16.0 (millesime @ 896a7a3) ----------
FROM python:3.12-slim-bookworm AS py-millesime
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/millesime.git#896a7a3cb4323d2a68f474fd3e7e32632c917b60 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-millesime
COPY --from=py-millesime /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Scriptorium 0.8.1 (scriptorium @ fffd96e) ----------
FROM python:3.12-slim-bookworm AS py-scriptorium
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/scriptorium.git#fffd96e633f412b501c904d34274ed2ae20b56ec /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-scriptorium
COPY --from=py-scriptorium /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Sillage 0.21.1 (sillage @ 40ba814) ----------
FROM python:3.12-slim-bookworm AS py-sillage
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/sillage.git#40ba814f75b016a29dc667391898e4b56d372502 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-sillage
COPY --from=py-sillage /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Transhumance 0.9.2 (transhumance @ d3f6fd5) ----------
FROM python:3.12-slim-bookworm AS py-transhumance
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/transhumance.git#d3f6fd59d36366458746ebb6bfb2007beeb53501 /src
RUN pip install --no-cache-dir --target /site -r /src/requirements.txt && rm -rf /src/.github
FROM node:22-bookworm-slim AS ui-transhumance
COPY --from=py-transhumance /src /build
WORKDIR /build/frontend
RUN npm ci --no-audit --no-fund && npx vite build --outDir /out --emptyOutDir

# ---------- Éphéméride 3.3.0 (verif-dates-photos @ 49b8c22) ----------
FROM python:3.12-slim-bookworm AS py-ephemeride
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev && rm -rf /var/lib/apt/lists/*
ADD --keep-git-dir=false https://github.com/baloodusudouest/verif-dates-photos.git#49b8c22c7daaef5fd853368c10f64ff952333a98 /src
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
