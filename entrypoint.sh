#!/bin/sh
# Démarre en root, adopte le propriétaire du dossier /data (ton compte du NAS), puis lance le Bac à sable avec ses
# droits. Les applis simulées sont lancées par lui, avec les mêmes droits, chacune dans /data/applis/<appli>.
set -eu

DATA="${BAC_DATA:-/data}"
mkdir -p "$DATA"

PUID="$(stat -c %u "$DATA")"
PGID="$(stat -c %g "$DATA")"
if [ "$PUID" = "0" ] && [ "${MAISON_ROOT_ACCEPTE:-}" != "oui" ]; then
  echo "ERREUR : $DATA appartient à root ; le Bac à sable ne tourne pas en root." >&2
  echo "Remède : donner le dossier à ton compte du NAS (File Station › Propriétés › Propriétaire, ou chown -R <UID>:<GID>)," >&2
  echo "puis redémarrer le conteneur. Dépannage seulement : MAISON_ROOT_ACCEPTE=oui dans la stack." >&2
  exit 1
fi
echo "bac-a-sable : exécution avec UID=$PUID GID=$PGID (propriétaire de $DATA)"

export HOME="$DATA"
cd /app
exec gosu "$PUID:$PGID" uvicorn app.main:app --app-dir /app --host 0.0.0.0 --port "${BAC_PORT:-8104}" --proxy-headers --no-access-log
