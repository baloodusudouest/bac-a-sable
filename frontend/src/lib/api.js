// Appels à l'API du Bac à sable. Une réponse 401 renvoie à l'écran de connexion.
export class ErreurApi extends Error {
  constructor(message, statut) {
    super(message)
    this.statut = statut
  }
}

async function appel(methode, chemin, corps) {
  const r = await fetch(chemin, {
    method: methode,
    headers: corps ? { 'Content-Type': 'application/json' } : undefined,
    body: corps ? JSON.stringify(corps) : undefined,
    credentials: 'same-origin',
  })
  let donnees = null
  try { donnees = await r.json() } catch { /* réponse sans contenu */ }
  if (r.status === 401 && chemin !== '/api/connexion') window.dispatchEvent(new Event('bac-deconnecte'))
  if (!r.ok) throw new ErreurApi(donnees?.detail || `Le serveur a répondu ${r.status}.`, r.status)
  return donnees
}

export const api = {
  get: (chemin) => appel('GET', chemin),
  post: (chemin, corps) => appel('POST', chemin, corps ?? {}),
  put: (chemin, corps) => appel('PUT', chemin, corps ?? {}),
  del: (chemin) => appel('DELETE', chemin),
}

// Noms affichés des origines de personnes
export const ORIGINES = { inventee: 'Inventée', piege: 'Piège', reelle: 'Copie de carnet' }
