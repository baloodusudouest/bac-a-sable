# Reprise — Bac à sable

Fichier à lire en premier dans une nouvelle session, et à mettre à jour à chaque fin de session, dans le même commit
que le code.

## État (23/11/2026) — 0.4.4 : listes déroulantes lisibles en sombre (`frontend/src/app.css`, bloc « Listes déroulantes (socle 0.12.2) » : `select option, select optgroup` aux couleurs `--popover`). Jamais essayé sur la vraie installation.

## État (22/11/2026, suite)

- **0.4.3 (22/11/2026)** : L'Anneau 0.18.0 embarqué (applis à mettre à jour dans « À faire quand tu veux » ; dans la démonstration, faux registres en mémoire, rien ne sort). Le faux Immich commun devient 0.4.4. **Jamais essayé sur la vraie installation.**
- **0.4.2 (22/11/2026)** : barre d'onglets collée en bas sur iPhone (`frontend/src/App.svelte`), toutes les applis embarquées aux versions du lot « barre collée en bas » (voir CHANGELOG). Le faux Immich commun devient 0.4.3. **Jamais essayé sur la vraie installation.**

## État (22/11/2026)

- **0.4.1 (22/11/2026)** : L'Anneau 0.17.2, Douze points 1.14.0, Gazette 0.30.0 embarqués (demande de Julien : appliquer au Bac à sable les mises à jour du coffre). Lanceurs inchangés ; `docs/flux-maison.json` retiré de la carte (aucun flux nouveau). Le faux Immich commun, prévu « 0.4.1 », devient 0.4.2. **Jamais essayé sur la vraie installation.**

- **0.4.0 (20/11/2026) « la maison branchée »** : liens entre applis simulées (table `liens:` d'`applis.yaml`, copie
  figée `docs/flux-maison.json`), jeton simulé, faux annuaire de l'Anneau (127.0.0.1:9104), garde par appli, cascade,
  activité propagée, limite de mémoire de toute la maison (2,4 Go), remise à zéro de la maison avec verrou, lanceur de
  la Gazette (carnet et Douze points simulés, personnes inventées seulement), Chromium de la Gazette restreint (proxy
  mort, `<-loopback>`), badge « encore en démo ». Test de livraison vert ici (soirée Portugal, Pologne, Moldavie…
  clôturée → numéro de la Gazette avec ces pays, les invités inventés, leurs commentaires ; aucune copie de vraie
  fiche) ; écrans PC et iPhone vérifiés (aucune erreur de page, aucun débordement). Dossier `docs/ajout-0.4.0.md`,
  conseil `docs/conseil-0.4.0.md`. **Jamais essayé sur la vraie installation** : ni la cascade ni la limite de mémoire
  sur le NAS (mesure réelle de Chromium), ni un vrai iPhone sur la soirée clôturée, ni la copie de vraies fiches suivie
  jusqu'à la Gazette avec le vrai carnet.
- **0.3.3 (20/11/2026)** : Douze points 1.11.0 embarqué.
- **0.3.2 (20/11/2026)** : Douze points 1.10.3 embarqué.
- **0.3.1 (20/11/2026)** : Millésime 2.16.0 embarqué.
- **0.3.0 (20/11/2026)** : toutes les applis embarquées aux versions du chantier « fiches Connexion » (voir CHANGELOG) ; socle 0.11.1.
- **0.2.0** (20/11/2026) : écran « Connexion » commun (contrat 3, socle 0.11.0, `simule` vrai) avec une fiche, carnet
  (le seul vrai lien) ; Douze points 1.10.1 embarqué (commit b6830c9 ; soirée de bout en bout rejouée ici, verte).
  `ANNEAU_CLE` dans compose. Attention : le Bac à sable n'est pas sur le réseau de la stack, l'Anneau doit le lire par
  l'adresse du NAS (port 8104). Jamais essayé sur la vraie installation.
- **0.1.6** (20/11/2026) : Douze points 1.7.1 (erreurs 500 « database is locked » corrigées) ; garde : `_taille()`
  lit `content-length` au lieu du corps (un envoi en flux vers un faux service échouait). Jamais essayé sur la vraie
  installation.
- **0.1.3** (19/11/2026) : Douze points 1.6.2 embarqué ; son lanceur branche le faux Immich des tests de Douze points
  (`tests/test_photos_16.FauxImmich`, clé `cle-de-test`), d'où l'icône 📷 et « Immortaliser ». Repli sur un faux
  minimal si ce module manque (dépôt plus ancien).
- **0.1.5** (19/11/2026) : Douze points 1.7.0 ; pages invité de Douze points relayées sans la session de l'hôte
  (`relais.page_invite`, d'après le chemin `/invite/…` ou le `Referer`).
- **0.1.4** (19/11/2026) : Journal › « Erreurs de l'appli » (`/api/applis/{appli}/sortie`) ; message clair sous un
  téléphone en erreur. **Ouvert** : erreurs 500 de Douze points 1.6.2 sur `/invite/…/api/prenom` et `/api/note` vues
  sur le NAS (5 téléphones sur 7), pas reproduites ici ; lire la cause dans ce nouvel écran.
- **0.1.2** (19/11/2026) : filigrane « BAC À SABLE — <appli> <version> — simulation » sur tous les écrans (relais pour
  les applis simulées, `Filigrane.svelte` pour l'écran du Bac à sable). Les deux dessins doivent rester pareils.
- **0.1.1** (19/11/2026) : journal du conteneur lisible (relais sans `log_config`, ligne « prêt » avec l'autotest).
  Premier démarrage sur le NAS vu dans les journaux de Julien : conteneur lancé (UID 1026), avertissements
  « Invalid HTTP request received » = accès en https à un port http.
- **0.1.0** : première version (voir `CHANGELOG.md`, `docs/dossier.md`). Port 8104 (écran), 8110-8121 (applis).
- Testé ici : API, garde, personnes (20 essais sans réseau) ; bout en bout avec de vrais processus pour carnet,
  Douze points, Sillage, Comptoir (soirée complète : 4 téléphones notent et envoient ; carnet reçoit les personnes
  du scénario ; relais : cookies protégés, reconnexion après « Se déconnecter »). Écrans vérifiés sur PC et
  iPhone (aucune erreur de page, aucun débordement).
- **CI verte le 19/11/2026** : image `0.1.0` publiée ; dans l'image, 35 essais sur 35 (les 12 applis démarrent et
  s'ouvrent par le relais, soirée Douze points, carnet) ; conteneur démarré, autotest « coupure » vert.
- **Jamais essayé** : l'installation sur le NAS (service ajouté à la stack du coffre le 19/11, pas encore déployé ;
  réseau `bac-a-sable` en 192.168.96.0/20, absent du pare-feu de DSM), la copie depuis le vrai carnet, un vrai
  iPhone sur la soirée simulée, Chromium de Gazette derrière le proxy inexistant.

## Prochaine étape

1. Paquet ghcr `bac-a-sable` : le rendre public si Portainer ne peut pas le tirer (paquet neuf, privé par défaut).
2. Installer sur le NAS (stack), lancer l'autotest avec `BAC_AUTOTEST` (adresses réelles de la maison).
3. **0.4.4** : faux Immich commun (service à part sous la garde, son journal, tests de contrat rejouant les faux Immich
   des dépôts) ; ajouter son port à `ports_permis` ; les photos des duos de Douze points arrivent alors dans la Gazette.
4. **0.4.x** : un lanceur par appli restante (Sillage, Millésime, Chambre noire, Kit, Comptoir, Scriptorium,
   Transhumance, Éphéméride) ; chaque nouveau lanceur branche ses liens (rien d'autre à changer : `liens:` les porte
   déjà, la variable devient obligatoire dans son lanceur).
5. **0.5.0** : page « Liens », voyants verts des fiches « Connexion » entre applis simulées, instantanés nommés,
   répétition générale.

## Décisions tranchées

- Image `latest`, mise à jour par Watchtower la nuit (Julien, 19/11/2026 ; avant : version figée dans la stack).

- Une seule appli commune, aucune appli en service modifiée (seule exception : lien dans les Réglages de l'Anneau).
- Applis lancées depuis les lanceurs de démonstration de leurs dépôts (ils coupent les tâches de fond et branchent
  les faux services) ; lanceurs écrits ici pour carnet (personnes du scénario) et Douze points (pas de démo).
- 0.4.0 : lanceur écrit ici pour la Gazette ; copies de vraies fiches jamais montrées à la Gazette simulée (arbitrage
  de Julien, liste blanche) ; Chromium restreint par ses propres réglages de proxy (choix fait en codant) ; une seule
  remise à zéro pour toute la maison ; faux Immich commun reporté à la 0.4.1 (conseil).
- Un environnement Python par appli (`/applis/<appli>/site`) : leurs versions épinglées se contredisent.
- Anneau simulé sans connexion : le relais tient les sessions, jamais le navigateur.
- Millésime sur ses faux services (âges inventés) : on teste les écrans, pas la datation.

## Pièges

- 0.4.0 : une appli simulée qui doit joindre une autre passe par un **lien branché** (`liens:`) ; sinon la garde
  refuse le port (journal : « sortie refusée 127.0.0.1:<port> »). Les adresses de l'annuaire sont celles du relais
  vues par le navigateur : une appli qui s'en servirait côté serveur est refusée (normal).
- 0.4.0 : la Gazette simulée ne voit que les fiches « BAS-<id> » des personnes inventées ou pièges du scénario : sans
  scénario joué, elle est vide (exprès). Un invité de Douze points ajouté à la main (prénom tapé, pas de fiche de
  carnet) n'apparaît pas dans la Gazette.
- 0.4.0 : `BAC_MAX_SIMULTANEES` n'existe plus (remplacé par `BAC_MEMOIRE_MO`).

- Pas de https : « Invalid HTTP request received » dans le journal = un navigateur (ou l'adresse Tailscale en
  `https://`) qui parle https au port 8104 ou 8110-8121.

- Le mot de passe de démonstration de chaque appli est dans `applis.yaml` : s'il change dans le dépôt, le relais ne se
  connecte plus (le test de fumée le voit).
- Les cookies ne sont pas séparés par port : ne jamais laisser une réponse d'appli simulée poser un cookie.
- `tools/dockerfile.py --verifier` échoue si le Dockerfile n'a pas été refait après un changement d'`applis.yaml`.
- Mur de téléphones : les écrans s'ouvrent par le lien de saisie de l'hôte (« #saisie=<jeton> ») ; ils partagent le
  stockage de l'onglet, ce qui suffit au premier affichage mais pas à un rechargement de chaque cadre.
- Caméra de Chambre noire : il lui faut du https ; dans le Bac à sable (http), la prise de vue ne marche pas.
