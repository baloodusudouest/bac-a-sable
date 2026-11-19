# Bac à sable — dossier (19/11/2026, version 3, après le 2e conseil)

> Nouvelle appli maison commune : **Bac à sable** fait tourner les vraies applis maison, à la demande, sur une fausse maison, avec des personnes réelles (copiées depuis carnet) ou inventées, pour les tester et les améliorer sans jamais créer de faux positifs. Remplace la version 1 du dossier (une simulation dans chaque appli), écartée après le conseil.

## 1. Besoin

- Voir une appli fonctionner sur des cas réalistes : un contact et ses liens possibles dans carnet, une soirée Douze points avec téléphones simulés, notes et commentaires, etc.
- Choix du grill et des deux tours suivants (19/11/2026) :
  - **Une seule appli commune** (conteneur unique), et **toutes les applis couvertes d'un coup**.
  - **Vraies applis lancées à la demande** dans ce conteneur, sur une **fausse maison** (faux iCloud, Immich, Home Assistant, Paperless, Grimmory, Ollama, Mistral, carnet…).
  - **Aucune appli en service n'est modifiée.** Seule exception : un lien « Ouvrir le bac à sable » dans les **Réglages de l'Anneau**.
  - **Un port par appli simulée**.
  - Personnes réelles = **copie lue dans carnet** ; vraie fiche jamais modifiée. Copies **effacées pour de bon au « Vider »** (VACUUM) et dossier du Bac à sable **exclu des sauvegardes**.
  - Scénarios **gardés jusqu'à « Vider »** ; scénarios par appli d'abord.
  - **Étanchéité totale** : invisible de À traiter, `/health` des vraies applis, tuile de l'Anneau (hors sa propre tuile), Home Assistant, Gazette.
  - **Douze points** : votes automatiques, mur de téléphones, et vrais iPhone mêlés aux téléphones simulés.
- Applis couvertes : carnet, Douze points, Sillage, Gazette, Comptoir, Scriptorium, Millésime, Transhumance, Chambre noire, Éphéméride, Kit d'urgence, l'Anneau. Hors : Atlas (réduit à carte.json), Scan Immich (retirée), Diaporama des invités (intégration HACS), socle (modèle).

## 2. Technique

- Dépôt `baloodusudouest/bac-a-sable`, image `ghcr.io/baloodusudouest/bac-a-sable`, Watchtower désactivé. Partie du socle (FastAPI + Svelte 5 + Tailwind 4, cookie `maison_session`, `/health`).
- **Construction** (Dockerfile multi-étages) : une étape par appli `FROM ghcr.io/baloodusudouest/<appli>:<version>` dont on copie `/app` et le frontend bâti dans `/applis/<appli>/`. Versions figées dans `applis.yaml` (une ligne par appli, port, variables à donner). Mettre à jour une appli simulée = changer sa version et republier l'image.
- **Lancement à la demande** : le Bac à sable démarre `uvicorn` pour une appli quand on l'ouvre (son propre dossier de données `/data/applis/<appli>/`, ses propres variables), l'arrête après 30 min sans requête. Chaque appli reste dans son processus (toutes s'appellent `app` en Python). Bouton « Tout arrêter ».
- **Fausse maison** : un serveur interne (`/faux/immich`, `/faux/icloud`, `/faux/ha`, `/faux/paperless`, `/faux/carnet`, `/faux/ollama`, `/faux/mistral`…) qui répond comme les vrais, d'après les faux déjà écrits dans les tests des applis (à recenser appli par appli). Chaque appli simulée reçoit les adresses de la fausse maison à la place des vraies, des clés factices, et `*_LECTURE_SEULE=0` pour qu'on voie ses écritures (elles atterrissent dans la fausse maison).
- **Réseau (tranché par le conseil)** : ports publiés, réseau Docker à part de la stack (les noms `immich`, `carnet`… ne s'y résolvent pas). Chaque appli simulée est lancée avec un environnement vide, seulement les variables du scénario ; fausse maison sur `127.0.0.1`. Le jeton de lecture de carnet reste dans le Bac à sable, jamais transmis aux applis. **Autotest** au démarrage (tentative vers le NAS, Immich, HA, l'Anneau, Internet) → voyant dans Réglages ; voyant rouge = applis simulées bloquées.
- **Relais devant chaque appli simulée** (choix « Anneau simulé sans connexion ») : chaque port 8110-8121 est servi par le Bac à sable, qui relaie vers l'appli sur un port interne. Le relais retire le vrai cookie `maison_session` des requêtes, présente à l'appli un cookie signé avec la clé propre au bac à sable, et supprime tout `Set-Cookie: maison_session` des réponses : aucune appli simulée (dont l'Anneau) ne peut toucher la vraie connexion. Il injecte aussi le bandeau « Bac à sable — rien ne sort » dans les pages HTML.
- **Environnements Python** : un par appli (`/applis/<appli>/venv`, créé à son chemin final), même image Python de base ; paquets système de toutes les applis dans l'étage final (image de plusieurs Go). Frontends bâtis copiés tels quels.
- **Tâches de fond** des applis (planificateurs, sondes) : branchées sur la fausse maison ou coupées par variable. Aucun vrai secret dans le conteneur. Les dossiers de fichiers (bookdrop, Pellicule, dossier des photos) sont des dossiers factices dans `/data`, jamais montés depuis le NAS.
- **Journal** : chaque écriture reçue par la fausse maison est notée (« carnet aurait écrit dans iCloud : … »).
- **Personnes** : `inventer(n)` (prénoms, noms, dates, lieux, liens familiaux, avatars dessinés) ; `copier_depuis_carnet(ids)`. Identifiant stable par personne simulée, partagé entre applis (prépare les scénarios communs).
- **Mémoire** : ~100 Mo par appli ouverte, à mesurer ; plafond de processus simultanés. **Millésime avec modèles factices** (âges inventés, pas de modèle chargé) : on teste les écrans et le parcours, pas la datation.
- **Personnes pièges** dans `inventer` : homonymes, accents, dates incomplètes, doublons, noms très longs, personne sans lien.
- **Copies de vraies fiches** effacées après 30 jours sauf scénario épinglé ; VACUUM à chaque effacement ; dossier exclu des sauvegardes.

## 3. Parcours des clics et des écrans

- Navigation du socle. Entrées : **Applis** (écran de travail), **Personnes**, **Scénarios**, **Journal**, **Réglages**.
- **Applis** : une tuile par appli (état arrêtée / démarrée, version embarquée, bouton « Ouvrir » qui démarre puis ouvre l'appli sur son port dans un nouvel onglet ou dans le cadre).
- **Personnes** : réelles (recherche dans carnet, copie) et inventées (nombre, variété) ; « Vider ».
- **Scénarios** : créer pour une appli (personnes, réglages propres), rejouer, dupliquer, vider. Remplir la fausse maison et la base de l'appli simulée selon le scénario.
- **Douze points** : scénario « Soirée » (concours, N téléphones simulés, profils de vote), **mur de téléphones** (2 à 12 cadres iPhone avec l'écran invité réel), QR code pour rejoindre la soirée simulée avec un vrai iPhone, « Avance rapide » jusqu'au dévoilement.
- **Journal** : ce qui aurait été écrit, par appli et par service.
- **Réglages** : version, versions embarquées, mémoire utilisée, Tout vider, déconnexion.
- **Anneau** : lien « Ouvrir le bac à sable » dans ses Réglages.

## 4. Design

- Charte du socle, toujours sombre. Couleur proposée : **cyan lagon `#5cc6d6`** (absente du tableau de `format.md`).
- Bandeau discret cyan « Bac à sable — rien ne sort » injecté par le relais en haut de chaque appli simulée.

## 5. Schéma de données

- `personnes(id, origine 'reelle'|'inventee'|'piege', carnet_id, donnees_json, cree_le, epinglee)`
- `scenarios(id, applis_json, nom, personnes_ids, reglages_json, cree_le)`
- État des processus en mémoire (pas de table).
- `ecritures(id, appli, service, action, contenu_json, quand)`
- Données de chaque appli simulée dans `/data/applis/<appli>/` (sa base à elle, au schéma de sa version embarquée : pas de double schéma à tenir).

## 6. Plan

1. Tableau de recensement, une ligne par appli : lancement, frontend bâti, variables d'adresse et de clé, paquets système, faux services existants, cookie, tâches de fond, taille.
2. Bac à sable 0.1.0 (une seule version publiée, toutes les applis) construit dans l'ordre : gestionnaire de processus + relais → fausse maison service par service → applis par lots de 3 avec test de fumée en CI → Millésime → personnes, scénarios, journal.
3. Douze points : soirée, mur, vrais iPhone.
4. Anneau : lien dans ses Réglages (version mineure).
5. Stack : service `bac-a-sable`, port **8104** (écran) + **8110-8121** (applis), réseau interne, variables ; tuile ; coffre (note, décision, ports, homelab yml complet).
6. Jamais essayé sur la vraie installation tant que l'utilisateur n'a pas testé.
