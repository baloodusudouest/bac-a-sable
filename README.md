# Bac à sable

Les applis maison, lancées pour de vrai mais sur une **fausse maison** : on y essaie un contact et ses liens dans
carnet, une soirée Douze points avec des téléphones simulés, ou n'importe quel écran d'une autre appli, sans rien
écrire chez les vrais services (iCloud, Immich, Home Assistant, Paperless…) et sans créer de faux positifs.

- **Applis** : les 12 applis maison sont embarquées (code de leur dépôt, au commit noté dans `applis.yaml`) et
  démarrent à la demande, chacune sur son port (8110 à 8121). Arrêt seul après 30 minutes sans usage.
- **Personnes** : inventées (avec liens de famille), pièges (homonymes, accents, dates incomplètes, doublons…), ou
  copies de vraies fiches de carnet (prénom, nom, naissance, genre ; lecture seule ; effacées après 30 jours sauf
  épinglées).
- **Scénarios** : des personnes et des applis ; « Jouer » remet l'appli à zéro et la relance avec eux. carnet et
  Douze points reçoivent les personnes ; les autres applis s'ouvrent sur les données de démonstration de leur dépôt.
- **Soirée** : Douze points monté comme le ferait l'hôte ; téléphones simulés (profils généreux, sévère, fan d'un
  pays…) ; mur de téléphones ; QR code pour rejoindre avec un vrai iPhone.
- **Journal** : ce que les applis auraient écrit chez les vrais services, et les sorties refusées.

## Pourquoi rien ne sort

1. Chaque appli simulée tourne dans son processus, avec un environnement vide (aucune vraie adresse, aucune clé).
2. Une **garde** (`garde/sitecustomize.py`) chargée d'office dans chaque appli refuse toute connexion qui ne va pas
   vers la machine elle-même, et ne résout aucun nom ; un proxy local inexistant couvre ce qui n'est pas du Python.
3. Les faux services sont ceux des tests de chaque appli (les lanceurs de démonstration des dépôts).
4. Le conteneur n'est pas sur le réseau de la stack.
5. Un **autotest** au démarrage le prouve ; s'il échoue, aucune appli ne démarre.

Le **relais** (`app/relais.py`) sert chaque appli simulée : il retire les vrais cookies, tient lui-même la session de
l'appli simulée et retire tous les `Set-Cookie` des réponses. Une appli simulée (l'Anneau surtout) ne peut donc pas
toucher à ta vraie connexion. Il ajoute un petit bandeau « Bac à sable » en haut des pages.

## Mettre à jour une appli embarquée

Dans `applis.yaml` : changer `version` et `sha` (commit du dépôt), puis `python tools/dockerfile.py` et pousser :
l'image est reconstruite, et les essais de bout en bout tournent dans l'image avant publication.

## Développement

```
pip install -r requirements-dev.txt
python -m pytest -q                                   # API, garde, personnes (sans réseau)
BAC_ESSAI_APPLIS=/chemin/applis python -m pytest -q   # + bout en bout (applis/<appli>/src et site)
cd frontend && npm ci && npx vite build
```

Déploiement : voir `docker-compose.yml` et `.env.example`.
