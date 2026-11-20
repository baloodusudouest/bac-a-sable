# Bac à sable 0.4.0 — avis du conseil (20/11/2026)

Dossier : `bac-a-sable-0.4.0-dossier.md`. Cinq conseillers, deux relectures croisées, synthèse. Les choix de Julien ne changent pas. Voici ce que le conseil fait changer au plan, et l'arbitrage de Julien sur le seul point qui lui revenait.

## Arbitrage de Julien (20/11/2026)

- **Copies de vraies fiches : seulement les personnes inventées dans la Gazette.** La Gazette simulée ne voit que les personnes inventées du scénario. Les copies de vraies fiches restent dans carnet et Douze points simulés, et le lanceur de la Gazette les écarte.

## Ce que le conseil fait changer

1. **La cause de la capture :** la Gazette du Bac à sable prend ses pays dans `DS.exemple()`, dans `tools/demo.py` de son dépôt. Le lanceur de la Gazette écrit ici supprime cette démo.
2. **Une 0.4.0 resserrée sur la capture**, avec un test de livraison : une soirée simulée (Portugal, Pologne…) est clôturée, puis la Gazette affiche ces pays, les invités inventés et leurs commentaires. Le faux Immich commun passe en 0.4.1.
3. **La table `liens:`** est écrite ici, mais un test la compare à une copie figée des flux de la carte du coffre (`docs/flux-maison.json`, tirée de la carte). Le Bac à sable ne lit jamais le coffre privé quand il tourne. Un flux sans lanceur est signalé.
4. **Garde resserrée, pas élargie :**
   - aujourd'hui, elle laisse passer tout `127.0.0.1` ;
   - désormais, chaque appli ne joint que les ports de ses liens, plus le faux annuaire, plus le faux Immich ;
   - un autotest refuse de démarrer si une variable `*_URL` vise autre chose que `127.0.0.1` ;
   - une variable de lien manquante fait échouer le lanceur, sans repli sur l'adresse de la vraie stack (`http://carnet:8096`).
5. **Jeton simulé** tiré par `secrets` à chaque démarrage, jamais lu dans l'environnement du conteneur. Un autotest vérifie qu'aucune variable d'une appli simulée ne vaut le vrai `MAISON_JETON`.
6. **Annuaire :** `MAISON_ANNEAU_URL` pointe vers le faux annuaire du Bac à sable (sinon `maison.Annuaire` chercherait l'Anneau de la vraie stack).
7. **Démarrage en cascade, lectures et écritures comprises :**
   - les applis qu'on lit et celles à qui on écrit démarrent ensemble ;
   - exemple : la clôture de Douze points écrit à carnet, donc carnet démarre ;
   - on garde la liste des applis déjà vues, car les liens vont dans les deux sens ;
   - les envois ratés sont repris par les files des applis (Douze points et la Gazette réessaient toutes les 10 min).
8. **Activité et mémoire :**
   - toucher une appli touche aussi celles qu'elle lit et celles à qui elle écrit (sinon carnet, lu par la Gazette, s'arrêtait au bout de 30 min) ;
   - la limite de 4 applis à la fois est remplacée par une limite de mémoire de 2,4 Go, mesurée sur tout l'arbre des processus, Chromium compris (le conteneur est coupé net à 3 Go) ;
   - l'appli arrêtée pour la mémoire le dit : « arrêtée pour libérer la mémoire ; ses données sont gardées ; la rouvrir ».
9. **Remettre la maison à zéro :**
   - un verrou commun empêche tout démarrage en cascade pendant la remise à zéro ;
   - toutes les bases sont vidées, celle de la Gazette comprise ;
   - le bouton dit ce qui sera perdu (soirées jouées, journaux, photos envoyées) et ce qui sera reversé (le scénario) ;
   - le scénario dit si la soirée Douze points est déjà clôturée.
10. **Badge « encore en démo »** sur les applis pas encore branchées (Sillage, Millésime…) ; leurs liens avec les applis branchées restent coupés, pour ne pas mélanger démo et scénario.
11. **Chromium de la Gazette** contourne la garde Python (`no_proxy=127.0.0.1`). On restreint ses adresses locales (règles de proxy de Chromium) ou on l'accepte en le disant ; à trancher en codant, et à dire.

## Pour plus tard (souhaits)

- **0.4.1 :** faux Immich commun, écrit ici comme un service à part sous la garde, avec son propre journal et des tests de contrat qui rejouent les appels des faux Immich de chaque dépôt. Il pourra rejoindre le `socle` ensuite.
- **0.4.x :** un lanceur par appli restante.
- **0.5.0 :**
  - page « Liens » ;
  - voyants verts des fiches « Connexion » entre applis simulées ;
  - instantanés nommés (« avant la clôture ») ;
  - répétition générale : un scénario scripté joué de bout en bout avant chaque changement de version dans `applis.yaml`.
- **Accès aux ports 8110 à 8121** (copies de vraies fiches) : rappeler qu'ils sont derrière le relais, avec sa connexion ; à vérifier dans la 0.4.0.
