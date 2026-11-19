<script>
  // Scénarios : des personnes + des applis (+ réglages propres à Douze points). « Jouer » remet l'appli à zéro,
  // y verse le scénario (carnet, Douze points) et l'ouvre. Les autres applis s'ouvrent sur leurs données de
  // démonstration.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Play from '@lucide/svelte/icons/play'
  import Copy from '@lucide/svelte/icons/copy'
  import Pin from '@lucide/svelte/icons/pin'
  import Trash2 from '@lucide/svelte/icons/trash-2'
  import LoaderCircle from '@lucide/svelte/icons/loader-circle'

  let scenarios = $state([])
  let applis = $state([])
  let personnes = $state([])
  let message = $state('')
  let joue = $state('')             // « sid:appli » en cours
  let reglages = $state({ douze_telephones: 6, douze_chansons: 12 })

  const vide = () => ({ nom: '', applis: [], personnes: [], telephones: 6, chansons: 12 })
  let nouveau = $state(vide())

  const nomAppli = (id) => applis.find((a) => a.id === id)?.nom ?? id
  const versees = (id) => applis.find((a) => a.id === id)?.personnes
  const nomDe = (p) => [p.prenom, p.nom].filter(Boolean).join(' ') || 'Sans nom'

  async function lire() {
    const [s, a, p, r] = await Promise.all([api.get('/api/scenarios'), api.get('/api/applis'), api.get('/api/personnes'),
                                            api.get('/api/reglages')])
    scenarios = s.scenarios
    applis = a.applis
    personnes = p.personnes
    reglages = r.reglages
  }

  function basculer(liste, valeur) {
    return liste.includes(valeur) ? liste.filter((x) => x !== valeur) : [...liste, valeur]
  }

  async function creer(e) {
    e.preventDefault()
    message = ''
    const corps = { nom: nouveau.nom, applis: nouveau.applis, personnes: nouveau.personnes, reglages: {} }
    if (nouveau.applis.includes('douze-points'))
      corps.reglages['douze-points'] = { telephones: Number(nouveau.telephones), chansons: Number(nouveau.chansons) }
    try {
      await api.post('/api/scenarios', corps)
      nouveau = { ...vide(), telephones: reglages.douze_telephones, chansons: reglages.douze_chansons }
      message = 'Scénario créé.'
      lire()
    } catch (err) {
      message = err.message
    }
  }

  async function jouer(s, appli) {
    const onglet = appli === 'douze-points' ? null : window.open('', '_blank')
    joue = `${s.id}:${appli}`
    message = ''
    try {
      const r = await api.post(`/api/scenarios/${s.id}/jouer`, { appli })
      if (appli === 'douze-points') location.hash = '#/soiree'
      else if (onglet) onglet.location = r.adresse
      message = r.versees ? `${nomAppli(appli)} relancée avec ${r.personnes} personnes.`
                          : `${nomAppli(appli)} relancée sur ses données de démonstration (elle ne reçoit pas encore les personnes).`
    } catch (err) {
      onglet?.close()
      message = err.message
    }
    joue = ''
    lire()
  }

  async function geste(promesse) {
    try { await promesse } catch (err) { message = err.message }
    lire()
  }

  onMount(lire)
</script>

<header class="mb-6">
  <h1 class="titre">Scénarios</h1>
  <p class="mt-1 max-w-prose text-sm text-muted-foreground">
    Jouer un scénario remet l'appli à zéro et la relance avec ses personnes. Rejouer, c'est repartir du même point.
  </p>
</header>

<form class="flex flex-col gap-4 rounded-2xl border bg-card p-5" onsubmit={creer}>
  <h2 class="text-base font-medium">Nouveau scénario</h2>
  <label class="flex flex-col gap-1 text-sm">Nom
    <input bind:value={nouveau.nom} required maxlength="80" placeholder="Soirée à huit, famille Garnier…"
           class="h-9 max-w-md rounded-lg border border-input bg-transparent px-3" />
  </label>
  <fieldset class="flex flex-col gap-2">
    <legend class="mb-1 text-sm">Applis</legend>
    <div class="flex flex-wrap gap-1.5">
      {#each applis as a (a.id)}
        <button type="button" aria-pressed={nouveau.applis.includes(a.id)} onclick={() => (nouveau.applis = basculer(nouveau.applis, a.id))}
                class="h-8 rounded-full border px-3 text-sm text-muted-foreground aria-pressed:border-transparent aria-pressed:bg-primary aria-pressed:text-primary-foreground">
          {a.nom}
        </button>
      {/each}
    </div>
  </fieldset>
  <fieldset class="flex flex-col gap-2">
    <legend class="mb-1 flex items-center gap-3 text-sm">
      Personnes ({nouveau.personnes.length} sur {personnes.length})
      <button type="button" class="text-primary underline-offset-4 hover:underline" onclick={() => (nouveau.personnes = personnes.map((p) => p.id))}>toutes</button>
      <button type="button" class="text-primary underline-offset-4 hover:underline" onclick={() => (nouveau.personnes = [])}>aucune</button>
    </legend>
    {#if personnes.length}
      <div class="flex max-h-48 flex-wrap gap-1.5 overflow-y-auto">
        {#each personnes as p (p.id)}
          <button type="button" aria-pressed={nouveau.personnes.includes(p.id)} onclick={() => (nouveau.personnes = basculer(nouveau.personnes, p.id))}
                  class="h-8 max-w-60 truncate rounded-full border px-3 text-sm text-muted-foreground aria-pressed:border-transparent aria-pressed:bg-secondary aria-pressed:text-foreground">
            {nomDe(p)}
          </button>
        {/each}
      </div>
    {:else}
      <p class="text-sm text-muted-foreground">Aucune personne : <a href="#/personnes" class="text-primary underline">en inventer</a> d'abord.</p>
    {/if}
  </fieldset>
  {#if nouveau.applis.includes('douze-points')}
    <fieldset class="flex flex-wrap gap-4">
      <legend class="mb-1 text-sm">Douze points</legend>
      <label class="flex flex-col gap-1 text-sm">Téléphones simulés
        <input type="number" min="0" max="60" bind:value={nouveau.telephones} class="h-9 w-24 rounded-lg border border-input bg-transparent px-3" />
      </label>
      <label class="flex flex-col gap-1 text-sm">Chansons
        <input type="number" min="1" max="26" bind:value={nouveau.chansons} class="h-9 w-24 rounded-lg border border-input bg-transparent px-3" />
      </label>
      <p class="basis-full text-xs text-muted-foreground">Les invités sans téléphone simulé restent libres pour de vrais iPhone.</p>
    </fieldset>
  {/if}
  <Button type="submit" class="self-start" disabled={!nouveau.nom || !nouveau.applis.length}>Créer le scénario</Button>
</form>

{#if message}<p class="mt-4 text-sm" role="status">{message}</p>{/if}

<ul class="mt-6 grid gap-3 md:grid-cols-2">
  {#each scenarios as s (s.id)}
    <li class="flex min-w-0 flex-col gap-3 rounded-2xl border bg-card p-4">
      <div class="flex items-start gap-2">
        <div class="min-w-0 flex-1">
          <h2 class="truncate text-base font-medium">{s.nom}</h2>
          <p class="text-xs text-muted-foreground">
            {s.personnes.length} personnes{s.joue_le ? `, joué le ${new Date(s.joue_le).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}` : ', jamais joué'}
          </p>
        </div>
        <button type="button" aria-pressed={s.epingle} aria-label={s.epingle ? 'Désépingler' : 'Épingler (ses copies de vraies fiches ne sont pas effacées)'}
                onclick={() => geste(api.put(`/api/scenarios/${s.id}`, { epingle: !s.epingle }))}
                class="-m-1 grid size-8 place-items-center rounded-md text-muted-foreground aria-pressed:text-primary">
          <Pin class="size-4" aria-hidden="true" />
        </button>
      </div>
      <div class="flex flex-wrap gap-1.5">
        {#each s.applis as a, i}
          <Button variant={i === 0 ? 'default' : 'outline'} onclick={() => jouer(s, a)} disabled={!!joue}>
            {#if joue === `${s.id}:${a}`}<LoaderCircle class="size-3.5 animate-spin" aria-hidden="true" />{:else}<Play class="size-3.5" aria-hidden="true" />{/if}
            Jouer sur {nomAppli(a)}{versees(a) ? '' : ' (démo)'}
          </Button>
        {/each}
      </div>
      <div class="mt-auto flex gap-1.5">
        <Button variant="ghost" class="text-muted-foreground" onclick={() => geste(api.post(`/api/scenarios/${s.id}/dupliquer`))}>
          <Copy class="size-3.5" aria-hidden="true" />Dupliquer
        </Button>
        <Button variant="ghost" class="ml-auto text-muted-foreground" onclick={() => geste(api.del(`/api/scenarios/${s.id}`))}>
          <Trash2 class="size-3.5" aria-hidden="true" />Effacer
        </Button>
      </div>
    </li>
  {:else}
    <li class="text-sm text-muted-foreground md:col-span-2">Aucun scénario pour l'instant.</li>
  {/each}
</ul>
