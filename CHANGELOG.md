# Journal des versions

## 0.3.1 — 20 novembre 2026 (Millésime 2.16.0)
- Millésime embarqué en 2.16.0 (fiche « Sillage » dans Connexion), au lieu de 2.15.1. `applis.yaml` et Dockerfile refait.
- **Jamais essayé sur la vraie installation.**

## 0.3.0 — 20 novembre 2026 (toutes les applis embarquées à jour, socle 0.11.1)
- Les applis embarquées passent aux versions du chantier « fiches Connexion » : l'Anneau 0.16.1 (au lieu de 0.14.0), carnet 3.3.1 (3.2.0), Chambre noire 0.9.1 (0.8.0), Comptoir 0.8.1 (0.7.0), Douze points 1.10.2 (1.10.1), Gazette 0.29.1 (0.27.0), kit d'urgence 2.7.1 (2.6.1), Millésime 2.15.1 (2.14.0), Scriptorium 0.8.1 (0.7.0), Sillage 0.21.1 (0.20.0), Transhumance 0.9.2 (0.8.0) ; Éphéméride inchangée (3.3.0). `applis.yaml` et Dockerfile refait par `tools/dockerfile.py`.
- Copies communes du socle 0.11.1 (« Pour le relier » quand le réglage est dans l'appli).
- **Jamais essayé sur la vraie installation** ; les lanceurs de démonstration des applis n'ont pas été rejoués un par un ici.

## 0.2.0 — 20/11/2026 (fiches « Connexion » communes, contrat 3, et Douze points 1.10.1)

- **Écran « Connexion »** (choix de Julien) : nouvelle entrée de la navigation, entre Journal et Réglages, avec l'écran
  commun `$lib/services/Services.svelte` (socle 0.11.0, copie non retouchée, empreinte contrôlée). Routes
  `GET /api/maison/services` et `POST /api/maison/services/{id}/verifier` (session du Bac à sable ou `ANNEAU_CLE`),
  réponse `"simule": true` : l'Anneau met un bandeau « Simulé » sur ses fiches.
- **Une fiche, carnet** : le seul vrai lien du Bac à sable (copie de vraies fiches, `BAC_CARNET_URL` et
  `MAISON_JETON`), en lecture seule, sans geste. « Vérifier » relit la liste des fiches (un GET, rien n'est gardé).
  Les applis embarquées (Douze points, carnet simulé…) ne joignent que des faux services : pas de fiche pour elles.
  L'écran du mot de passe (`pages/Connexion.svelte`) ne change pas ; aucune ancienne route à retirer (il n'y avait pas
  d'écran des services ; « Copie depuis carnet : réglée » reste aussi dans Réglages).
- `app/maison.py` passe au contrat 3 (socle 0.11.0). `ANNEAU_CLE` ajoutée dans `docker-compose.yml` et `.env.example`.
- **Douze points 1.10.1** embarqué (avant : 1.7.1) : 1.8.0 (public sans cliquer, pays en lice, selfies des duos à la
  télé, saisie directe de la grille), 1.9.0 (dévoilement réglable, À traiter et clôture, résultat officiel pour
  Gazette, photo apéro, mode d'emploi), 1.10.0 et 1.10.1 (fiches « Connexion » communes). Seuls `applis.yaml`
  (version, commit b6830c9) et le Dockerfile refait par `tools/dockerfile.py` changent ; le lanceur et la régie de la
  soirée restent les mêmes (réglages et API de Douze points inchangés pour eux).
- Tests : `tests/test_fiches_connexion.py` (forme du contrat 3, `simule` vrai, accès session ou `ANNEAU_CLE` seulement,
  Vérifier d'un service pas relié, copies communes non retouchées, essai de carnet en lecture seule). Bout en bout
  rejoué ici avec Douze points 1.10.1 (soirée complète, 4 téléphones, relais, cookies) : vert.
- **Jamais essayé sur la vraie installation.**

## 0.1.6 — 20/11/2026

- **Douze points 1.7.1** embarqué : plus d'erreurs 500 « database is locked » quand plusieurs téléphones notent en même
  temps (cause trouvée grâce à Journal › Erreurs de l'appli).
- **Garde** : un envoi en flux vers un faux service (la photo de Douze points vers le faux Immich) n'échoue plus. La
  garde lisait le corps pas encore lu pour noter sa taille (« Attempted to access streaming request content… ») ; elle
  prend maintenant la taille dans l'en-tête `content-length`, ou ne la note pas.
- Test : `test_envoi_en_flux_vers_un_faux_service`.

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
