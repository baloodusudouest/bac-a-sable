# Bac à sable 0.4.0 — « la maison branchée » — dossier (20/11/2026)

Demande de Julien du 20/11/2026 (22 h 47), après deux captures : la Gazette du Bac à sable affichait « Pays 6, Pays 12 » alors que Douze points simulé avait une soirée Portugal, Pologne… Cadrage par questions à choix le même soir.

## 1. Besoin

Les applis simulées doivent se parler comme dans la vraie maison, pour qu'un scénario se joue de bout en bout. Exemple : soirée Douze points → clôture → carnet reçoit la soirée → la Gazette fait le magazine avec les vrais pays, les invités du scénario, leurs commentaires et les photos des duos.

Choix de Julien :
1. **Portée :** tous les flux de la vraie maison entre applis maison (le coffre en compte 32), refaits entre les applis simulées.
   - **Anneau :** seulement l'annuaire (les applis se trouvent entre elles). Pas de tuiles, de voyants ni de sauvegarde simulés.
   - **Services extérieurs :** Home Assistant, Ollama, iCloud, Wikipédia… restent des faux.
2. **Démarrage :** ouvrir une appli démarre aussi celles qu'elle lit. Un lien vers une appli arrêtée s'affiche comme coupé, sans erreur.
3. **Mémoire :** au-delà de la limite (3 Go), l'appli simulée inutilisée depuis le plus longtemps s'arrête seule ; son lien paraît coupé.
4. **Remise à zéro :** une seule pour toute la maison simulée, pour que les applis restent cohérentes.
5. **Un faux Immich commun :** une photo envoyée par Douze points simulé se retrouve dans la Gazette simulée (et de même Chambre noire → Millésime, Sillage…).
6. **Données :** seulement celles du scénario (personnes du scénario, éventuellement copies de vraies fiches de carnet) et ce que les applis simulées s'envoient. Plus de données de démo.

## 2. Flux concernés (coffre, 20/11/2026)

Entre applis (20) :
- carnet → Douze points, Gazette, Kit d'urgence, Sillage
- Douze points → carnet, Gazette
- Gazette → carnet
- Sillage → carnet, Gazette, Millésime
- Millésime → carnet, Transhumance
- Chambre noire → Millésime, Sillage
- Scriptorium → Comptoir

Vers ou depuis l'Anneau (12) : seul l'**annuaire** (`GET /externe/services`, adresses des tuiles) est simulé. Les autres (tuiles, `/health` lu par l'Anneau, sauvegarde de nuit) sont hors portée.

Par le faux Immich commun : Douze points (photos, albums, tags), Gazette (photos de l'invité, « scandale », duos, apéro), Chambre noire (envoi), Millésime (lecture, tags), Sillage (personnes, photos), carnet (personnes liées), Transhumance, Éphéméride.

## 3. Technique

**Aujourd'hui (0.3.3) :**
- Chaque appli tourne dans un processus à part, en `127.0.0.1:(port + 1000)`, derrière le relais (ports 8110 à 8121).
- Son environnement est construit de zéro : aucune adresse, aucun jeton.
- Une garde (`garde/sitecustomize.py`) refuse toute sortie réseau ; le proxy est mis sur un port mort.
- Les faux services sont ceux des tests de chaque dépôt, chargés dans le processus (MockTransport).
- carnet et Douze points ont un lanceur écrit ici (`lanceurs/`) ; les autres lancent la démo de leur dépôt.

**Ce qui change :**

1. **Adresses entre applis**
   - Chaque appli reçoit les adresses des autres, prises dans ses variables de la vraie stack (`GAZETTE_CARNET_URL`, `GAZETTE_DOUZE_POINTS_URL`, `DOUZE_POINTS_CARNET_URL`, `SILLAGE_CARNET_URL`, `KIT_URL`…), pointées vers `http://127.0.0.1:<port local de l'autre>`.
   - Un jeton commun simulé `MAISON_JETON`, tiré au hasard à chaque démarrage du Bac à sable et jamais le vrai.
   - Les variables viennent d'une table `liens:` dans `applis.yaml` (de, vers, variable), recopiée des flux du coffre.
2. **Annuaire**
   - Un faux annuaire de l'Anneau (`/externe/services`) servi par le Bac à sable lui-même.
   - Les applis qui le lisent (adresse publique d'une appli, liens entre applis) y trouvent les adresses du relais (vues par le navigateur).
3. **Garde**
   - Elle laisse passer `127.0.0.1` vers les seuls ports locaux des applis simulées, l'annuaire et le faux Immich commun.
   - Tout le reste reste refusé. L'autotest « coupure » vérifie toujours qu'aucune sortie n'est possible.
4. **Faux Immich commun**
   - Un petit service du Bac à sable (FastAPI, port local fixe) avec le sous-ensemble de l'API Immich que les applis utilisent : serveur et version, envoi et lecture d'assets, vignettes, albums, tags, personnes, recherche par personne et par date, et les droits de clé simulés.
   - Ses photos sont des images fabriquées (couleur et légende), plus celles que les applis envoient.
   - Il est rempli depuis le scénario : une personne Immich par personne du scénario, avec quelques photos par personne et par année.
   - Point délicat : chaque appli a son propre faux Immich de tests, écrit d'après le vrai. Le commun doit couvrir l'union de ce qu'ils servent. À recenser dépôt par dépôt avant de l'écrire.
5. **Démarrage en cascade**
   - `ouvrir(appli)` démarre d'abord les applis qu'elle lit, d'après `liens:`, sans boucle.
   - L'écran du Bac à sable montre ce qui tourne et pourquoi.
6. **Mémoire**
   - On mesure la mémoire totale (déjà fait : `memoire_mo`).
   - Au-delà de 3 Go : on arrête l'appli touchée il y a le plus longtemps (`toucher()` existe), jamais celle qu'on ouvre ni celles qu'elle lit.
7. **Remise à zéro de la maison**
   - Tout arrêter, vider les dossiers de données des applis et le faux Immich, puis reverser le scénario.
   - Le scénario porte l'état voulu : personnes, et soirée Douze points s'il y en a une.
8. **Plus de démo : un lanceur par appli dans `lanceurs/`**, sur le modèle de carnet et Douze points.
   - Les applis prennent leurs données dans le scénario, carnet ou le faux Immich commun, et branchent les faux services extérieurs restants (Home Assistant, Ollama, Wikipédia, iCloud, Mistral…).
   - Gros morceau : 10 lanceurs, chacun d'après l'appli et ses faux de tests.
   - L'Anneau simulé reste le relais. Éphéméride et Transhumance lisent le faux Immich commun.
9. **Versions des applis embarquées**
   - Celles du jour, qui ont toutes l'écran « Connexion » commun.
   - Avec les liens, leurs fiches « Connexion » simulées doivent montrer des voyants verts entre applis.

## 4. Écrans

- Écran du Bac à sable, liste des applis : pour chacune, « tourne / arrêtée », la mémoire, et « lancée pour Gazette » quand elle a démarré en cascade.
- Un bouton « Remettre la maison à zéro » (avec confirmation) remplace les remises à zéro par appli.
- Une page « Liens » montre les flux simulés (de → vers, branché ou coupé) et la dernière fois qu'ils ont servi, d'après le journal du relais.
- Dans chaque appli, rien ne change, à part le filigrane « BAC À SABLE » déjà là.

## 5. Ordre proposé (versions successives)

1. **0.4.0 :**
   - liens et adresses entre applis, jeton simulé, garde élargie, annuaire, démarrage en cascade, mémoire, remise à zéro de la maison ;
   - faux Immich commun branché sur Douze points et la Gazette ;
   - lanceur de la Gazette (fiches depuis carnet, soirées depuis Douze points).

   C'est ce qui répare la capture de Julien.
2. **0.4.x :** un lanceur par appli restante (Sillage, Millésime, Chambre noire, Kit, Comptoir, Scriptorium, Transhumance, Éphéméride), avec le faux Immich commun.
3. **0.5.0 :** page « Liens » et voyants verts des fiches « Connexion » entre applis simulées.

## 6. Questions pour le conseil

1. **Faux Immich commun :** un service à part écrit ici, ou réutiliser le faux des tests d'une appli et le compléter ?
2. **Jeton simulé et garde élargie :** l'étanchéité tient-elle, sachant que le Bac à sable contient des copies de vraies fiches ?
3. **Variables des adresses :** une table `liens:` à entretenir à la main dans `applis.yaml`, ou la lire depuis la carte de la maison du coffre ?
4. **Remettre la maison à zéro** en un bouton : trop brutal ?
5. **Découpage :** 0.4.0 / 0.4.x / 0.5.0, est-ce le bon ?
