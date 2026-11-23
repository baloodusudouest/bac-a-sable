# Journal des versions

## 0.4.5 — 23/11/2026 (applis du jour embarquées)

- **Toutes les applis embarquées aux versions du 23/11/2026** (listes déroulantes lisibles en sombre, socle 0.12.2) : L'Anneau 0.18.3, carnet 3.5.1 (avec les nouveautés de la 3.5 : alimentation vers Home Assistant, conjoint et couple dans Treemich, livre d'or), Chambre noire 0.9.3, Comptoir 0.8.3, Douze points 1.14.2, Gazette 0.30.2, Kit d'urgence 2.7.3, Millésime 2.16.2, Scriptorium 0.8.3, Sillage 0.21.3, Éphéméride 3.3.2. Transhumance reste en 0.9.5 (en cours de travail). Dîme n'est pas embarquée (dépôt privé).
- Essai ici de la maison branchée avec carnet 3.5.1, Douze points 1.14.2 et Gazette 0.30.2 bâtis depuis leurs dépôts : 9 essais verts (le PDF de la Gazette, qui demande Chromium, non rejoué).
- Lanceurs inchangés. Jamais essayé sur la vraie installation.

## 0.4.4 — 23/11/2026 (listes déroulantes lisibles en sombre)

- **Listes déroulantes illisibles sur PC** (constaté par Julien dans Dîme, 23/11/2026) : la liste ouverte d'un `<select>` gardait un fond blanc tout en reprenant le texte crème de l'appli. `frontend/src/app.css` reprend le bloc du socle 0.12.2 (« Listes déroulantes (socle 0.12.2) ») : choix aux couleurs des menus, titres de groupe en gras, choix désactivés en gris.
- Jamais essayé sur la vraie installation.

## 0.4.3 — 22/11/2026

- L'Anneau 0.18.0 embarqué : « À faire quand tu veux » montre les applis de la stack à mettre à jour (ligne repliée, bouton par appli, double confirmation pour les protégés). Dans la démonstration, les registres d'images sont simulés en mémoire : rien ne sort.

## 0.4.2 — 22 novembre 2026 (barre d'onglets collée en bas, applis à jour)
- **iPhone : barre d'onglets du Bac à sable collée au bord bas**, sur toute la largeur (demande de Julien du 22/11/2026, socle 0.12.1).
- **Toutes les applis embarquées aux versions du même jour**, qui ont aussi leur barre collée en bas : L'Anneau 0.17.3, carnet 3.3.2 (avec l'index des lettres corrigé), Chambre noire 0.9.2, Comptoir 0.8.2, Douze points 1.14.1, Gazette 0.30.1, Kit d'urgence 2.7.2, Millésime 2.16.1, Scriptorium 0.8.2, Sillage 0.21.2, Transhumance 0.9.5, Éphéméride 3.3.1.
- Lanceurs inchangés.

## 0.4.1 — 22 novembre 2026 (applis embarquées à jour)

- **L'Anneau 0.17.2**, **Douze points 1.14.0** et **Gazette 0.30.0** embarqués : versions et commits relevés dans le coffre et sur les étiquettes des dépôts le 22/11/2026.
- Lanceurs de Douze points et de la Gazette inchangés. Pour la Gazette, les nouveaux réglages Paperless restent vides : rien n'est rangé, et aucune adresse n'est ouverte.
- Copie figée des flux (`docs/flux-maison.json`) retirée de la carte du coffre : aucun flux nouveau entre applis embarquées.
- Les autres applis étaient déjà à jour. Dîme n'est pas embarquée (dépôt privé).

## 0.4.0 — 20 novembre 2026 (« la maison branchée »)
Dossier `docs/ajout-0.4.0.md`, avis du conseil `docs/conseil-0.4.0.md` (points 1 à 11). Origine : la Gazette du Bac à sable affichait « Pays 6, Pays 12 » alors que Douze points simulé avait joué une soirée Portugal, Pologne…

- **Liens entre applis simulées** : table `liens:` dans `applis.yaml` (les 32 flux du coffre entre applis maison, avec l'appli appelante et sa variable d'adresse de la vraie stack). Un lien est branché quand ses deux bouts ont un lanceur écrit ici ; en 0.4.0 : carnet ↔ Douze points, carnet → Gazette, Douze points → Gazette, Gazette → carnet. Les autres sont coupés, avec leur motif (`GET /api/liens`). Copie figée des flux tirée de la carte du coffre : `docs/flux-maison.json` (de, vers, nature ; aucune adresse), refaite par `tools/flux_maison.py` ; un test compare les deux. Le Bac à sable ne lit jamais le coffre.
- **Adresses et jeton** : chaque appli appelante reçoit sa variable (`GAZETTE_CARNET_URL`, `GAZETTE_DOUZE_POINTS_URL`, `DOUZE_POINTS_CARNET_URL`) pointée vers `http://127.0.0.1:<port local de l'autre>`, et un jeton commun simulé `MAISON_JETON` tiré par `secrets` à chaque démarrage (jamais lu dans l'environnement du conteneur). Lancement refusé si une variable `*_URL` vise autre chose que 127.0.0.1 ou si une variable vaut le vrai jeton ; vérifié aussi à l'autotest (rouge = applis bloquées). Une variable de lien manquante arrête le lanceur, sans repli sur la vraie stack.
- **Faux annuaire de l'Anneau** (`app/annuaire.py`, 127.0.0.1:9104, jamais publié) : `MAISON_ANNEAU_URL` des applis simulées y pointe ; il donne l'adresse du relais de chaque appli.
- **Garde resserrée** : une appli ne joint plus que les ports de ses liens, le faux annuaire, son propre port et ceux qu'elle ouvre elle-même (faux serveurs de démonstration) ; le Bac à sable (8104), les autres applis et les relais lui sont fermés (`BAS_PORTS`).
- **Démarrage en cascade** : ouvrir une appli démarre d'abord celles qu'elle lit et celles à qui elle écrit (la Gazette démarre carnet et Douze points ; Douze points démarre carnet, qui reçoit la clôture), sans boucle. L'écran dit « Lancée pour Gazette ». **Activité propagée** : toucher une appli touche celles qu'elle appelle.
- **Mémoire** : la limite de 4 applis à la fois est remplacée par une limite de toute la maison, 2,4 Go (`BAC_MEMOIRE_MO`), mesurée sur l'arbre des processus du conteneur (Chromium compris, petits-enfants compris). Au-delà, l'appli touchée il y a le plus longtemps s'arrête (jamais celle qu'on ouvre ni celles qu'elle appelle) et le dit : « arrêtée pour libérer la mémoire ; ses données sont gardées ; la rouvrir » (écran Applis et page du relais, avec « La rouvrir »). Barre de mémoire sur l'écran Applis.
- **Remettre la maison à zéro** : un seul bouton pour toute la maison simulée (remplace « Vider » par appli à l'écran), avec ce qui sera perdu (données des applis, soirée jouée, journaux, photos envoyées) et ce qui sera reversé (le scénario choisi : personnes, soirée Douze points à jouer ou déjà clôturée). Verrou commun : aucun démarrage (relais, écran, cascade) pendant la remise. Jouer un scénario remet aussi toute la maison à zéro, puis verse le scénario dans les applis branchées. Routes `GET` et `POST /api/maison/remise-a-zero` (confirmation obligatoire).
- **Lanceur de la Gazette** (`lanceurs/gazette.py`) : la démonstration du dépôt (`DS.exemple()`, cause des « Pays 6 ») n'est plus lancée. Fiches lues dans carnet simulé, **personnes inventées seulement** (arbitrage de Julien) : liste blanche des identifiants « BAS-<id> » des personnes inventées ou pièges du scénario ; fiche complète, parutions et « journaux » limités à elles. Soirées lues dans Douze points simulé (`/externe/soirees…`), journal filtré de la même façon (invités, notes, commentaires, palmarès, duos, flair). Immich et Ollama minimaux sans données de démo, sources Wikipédia des fixtures, Sillage coupé.
- **Chromium de la Gazette** (point 11) : restreint. Le lanceur ajoute `--proxy-server=http://127.0.0.1:9` et `--proxy-bypass-list=<-loopback>` à chaque lancement : Chromium ne joint plus aucun port local (en plus du blocage des pages par la Gazette elle-même). Le PDF du magazine s'imprime toujours.
- **Douze points** : son lanceur reçoit carnet simulé (`DOUZE_POINTS_CARNET_URL`) ; la régie choisit les invités dans carnet simulé (journal avec identifiant de carnet), accepte une liste de pays (`pays`) et sait clôturer la soirée (`POST /api/douze/cloturer`, bouton « Clôturer la soirée », réglage de scénario « soirée déjà clôturée »). La clôture envoie la soirée à carnet simulé.
- **carnet** : sans scénario, il démarre sans fiche (plus de contacts de démonstration) ; Sillage, encore en démo, n'est pas lu.
- **Badge « encore en démo »** sur les applis sans lanceur ici (leurs liens restent coupés).
- Tests : `tests/test_liens.py` (table et copie figée, cascade sans boucle, adresses, ports, jeton simulé, autotest des liens, activité, règle des 2,4 Go simulée, message mémoire, verrou, badge, liste blanche de la Gazette, ports 8110-8121 derrière le relais) ; garde par appli dans `tests/test_garde.py` ; `tests/test_maison_branchee.py` (bout en bout : test de livraison, cascade, Chromium, remise à zéro).
- **Jamais essayé sur la vraie installation.**

## 0.3.3 — 20 novembre 2026 (Douze points 1.11.0)
- Douze points embarqué en 1.11.0 (sons sur la télé, compte à rebours avant la révélation, commentaires dans le classement), au lieu de 1.10.3. `applis.yaml` et Dockerfile refait.
- **Jamais essayé sur la vraie installation.**

## 0.3.2 — 20 novembre 2026 (Douze points 1.10.3)
- Douze points embarqué en 1.10.3 (écran télé lisible sur un petit écran en paysage : QR code et mode d'emploi), au lieu de 1.10.2. `applis.yaml` et Dockerfile refait.
- **Jamais essayé sur la vraie installation.**

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
