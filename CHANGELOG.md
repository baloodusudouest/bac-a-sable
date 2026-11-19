# Journal des versions

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
