# Journal des versions

## 0.1.5 — 19/11/2026

- **Douze points 1.7.0** embarqué (animation du dernier vote du public, télé et téléphones).
- **Téléphones vus comme des invités** : le relais ne présente plus la session de l'hôte aux pages invité de Douze
  points (`/invite/…`) ni à ce qu'elles appellent (en-tête `Referer`). Avant, chaque téléphone du mur (et un vrai
  iPhone passé par le QR code) était pris pour l'hôte et montrait les boutons « Revenir » / « Suivant ». Douze points,
  lui, les réservait déjà à l'hôte. `relais.page_invite`, tests.

## 0.1.4 — 19/11/2026

- **Journal › Erreurs de l'appli** : la fin du journal du processus de chaque appli simulée (erreurs Python
  comprises), avec le nombre d'erreurs. Route `GET /api/applis/{appli}/sortie`.
- Soirée : un téléphone en erreur dit maintenant quelle réponse Douze points a donnée et où lire la cause, au lieu du
  message brut d'httpx. Origine : erreurs 500 de Douze points 1.6.2 vues par Julien sur le NAS (7 téléphones), pas
  reproduites sur la machine de Claude (disque rapide).

## 0.1.3 — 19/11/2026

- **Douze points 1.6.2 embarqué, avec un faux Immich** (remarque de Julien du 19/11/2026 : ni icône 📷 ni bandeau photo). Douze points n'affiche les photos que si Immich est réglé ; son lanceur (`lanceurs/douze_points.py`) lui donne maintenant le faux Immich de ses propres tests (`httpx.MockTransport`, rien ne sort du processus). L'icône 📷 et « Immortaliser » paraissent sur les téléphones ; chaque photo envoyée est notée au journal (« aurait écrit chez immich.bac-a-sable »). Douze points 1.6.1 et 1.6.2 viennent avec : points du public dans l'ordre du jury, prénoms des jumeaux en entier, jumeau toujours affiché.
- Test de bout en bout : la porte invité de la soirée simulée annonce les photos actives.

## 0.1.2 — 19/11/2026

- **Filigrane** sur tous les écrans : « BAC À SABLE » en diagonale, répété, avec le nom et la version de l'appli
  (« carnet 3.2.0 — simulation »), cyan peu opaque, sans bloquer aucun clic. Posé par le relais sur chaque page des
  applis simulées (mur de téléphones compris) et sur l'écran du Bac à sable lui-même (« écran de pilotage »). Une
  capture d'écran d'un écran du Bac à sable se reconnaît ainsi au premier coup d'œil. `app/filigrane.py`,
  `frontend/src/lib/Filigrane.svelte` (même dessin), test `tests/test_filigrane.py`.

## 0.1.1 — 19/11/2026

- Journal du conteneur lisible : les serveurs du relais ne changent plus le niveau du journal commun d'uvicorn
  (« Application startup complete » et « Uvicorn running on » étaient masqués) ; une ligne « Bac à sable … prêt »
  donne les ports et le résultat de l'autotest.
- Rappel : « Invalid HTTP request received » veut dire qu'on a parlé en https à un port http (le Bac à sable n'a pas
  de https : ouvrir http://<NAS>:8104).

## 0.1.0 — 19/11/2026

Première version (dossier `docs/dossier.md`, deux passages du conseil).

- 12 applis embarquées, construites depuis leurs dépôts publics au commit noté (`applis.yaml`, `tools/dockerfile.py`),
  lancées à la demande dans leur propre processus, arrêtées après 30 min sans usage ou au-delà de leur mémoire,
  4 au plus en même temps.
- Garde réseau dans chaque appli simulée (aucune sortie, aucun nom résolu), proxy local inexistant pour le reste,
  autotest au démarrage qui bloque tout s'il échoue.
- Relais par port : cookies du navigateur jamais transmis, session de l'appli simulée tenue par le relais, aucun
  `Set-Cookie` renvoyé, bandeau « Bac à sable ».
- Personnes inventées, pièges, copies de vraies fiches de carnet (lecture seule, champs réduits, effacées pour de bon :
  `secure_delete` + `VACUUM`, après 30 jours sauf épinglées).
- Scénarios ; carnet reçoit les personnes (faux iCloud, doubles dans le faux Immich) ; Douze points : soirée montée
  par son API, téléphones simulés à profils, mur de téléphones, QR code pour vrais iPhone.
- Journal des écritures reçues par les faux services et des sorties refusées.
