# Reprise — Bac à sable

Fichier à lire en premier dans une nouvelle session, et à mettre à jour à chaque fin de session, dans le même commit
que le code.

## État (19/11/2026)

- **0.1.0** : première version (voir `CHANGELOG.md`, `docs/dossier.md`). Port 8104 (écran), 8110-8121 (applis).
- Testé ici : API, garde, personnes (20 essais sans réseau) ; bout en bout avec de vrais processus pour carnet,
  Douze points, Sillage, Comptoir (soirée complète : 4 téléphones notent et envoient ; carnet reçoit les personnes
  du scénario ; relais : cookies protégés, reconnexion après « Se déconnecter »). Écrans vérifiés sur PC et
  iPhone (aucune erreur de page, aucun débordement).
- **Jamais essayé** : l'image complète (les 12 applis construites ensemble), les 8 autres applis embarquées
  (la CI les essaie dans l'image), la copie depuis le vrai carnet, l'installation sur le NAS, un vrai iPhone sur la
  soirée simulée, Chromium de Gazette derrière le proxy inexistant.

## Prochaine étape

1. Vérifier que la CI (Tests, Image Docker) est verte ; corriger l'appli embarquée qui ne démarre pas (test de fumée
   `test_chaque_appli_demarre_et_s_ouvre_par_le_relais`).
2. Installer sur le NAS (stack), lancer l'autotest avec `BAC_AUTOTEST` (adresses réelles de la maison).
3. Verser les personnes du scénario dans d'autres applis (Gazette, Sillage, Kit d'urgence) : un lanceur par appli
   dans `lanceurs/`, sur le modèle de `lanceurs/carnet.py`.

## Décisions tranchées

- Une seule appli commune, aucune appli en service modifiée (seule exception : lien dans les Réglages de l'Anneau).
- Applis lancées depuis les lanceurs de démonstration de leurs dépôts (ils coupent les tâches de fond et branchent
  les faux services) ; lanceurs écrits ici pour carnet (personnes du scénario) et Douze points (pas de démo).
- Un environnement Python par appli (`/applis/<appli>/site`) : leurs versions épinglées se contredisent.
- Anneau simulé sans connexion : le relais tient les sessions, jamais le navigateur.
- Millésime sur ses faux services (âges inventés) : on teste les écrans, pas la datation.

## Pièges

- Le mot de passe de démonstration de chaque appli est dans `applis.yaml` : s'il change dans le dépôt, le relais ne se
  connecte plus (le test de fumée le voit).
- Les cookies ne sont pas séparés par port : ne jamais laisser une réponse d'appli simulée poser un cookie.
- `tools/dockerfile.py --verifier` échoue si le Dockerfile n'a pas été refait après un changement d'`applis.yaml`.
- Mur de téléphones : les écrans s'ouvrent par le lien de saisie de l'hôte (« #saisie=<jeton> ») ; ils partagent le
  stockage de l'onglet, ce qui suffit au premier affichage mais pas à un rechargement de chaque cadre.
- Caméra de Chambre noire : il lui faut du https ; dans le Bac à sable (http), la prise de vue ne marche pas.
