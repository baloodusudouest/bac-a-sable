<script>
  // Personnes : inventées (avec liens de famille), pièges (cas limites), copies de vraies fiches de carnet
  // (prénom, nom, naissance, genre seulement ; effacées après 30 jours sauf épinglées).
  import { onMount } from 'svelte'
  import { api, ORIGINES } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import WandSparkles from '@lucide/svelte/icons/wand-sparkles'
  import UserPlus from '@lucide/svelte/icons/user-plus'
  import Search from '@lucide/svelte/icons/search'
  import Pin from '@lucide/svelte/icons/pin'
  import Trash2 from '@lucide/svelte/icons/trash-2'

  let donnees = $state(null)
  let filtre = $state('')
  let message = $state('')
  let nombre = $state(8)
  let variete = $state(50)
  let recherche = $state('')
  let fiches = $state(null)
  let choisies = $state(new Set())
  let attente = $state(false)

  const parId = $derived(Object.fromEntries((donnees?.personnes ?? []).map((p) => [p.id, p])))
  const affichees = $derived((donnees?.personnes ?? []).filter((p) => !filtre || p.origine === filtre))
  const compte = (o) => (donnees?.personnes ?? []).filter((p) => p.origine === o).length
  const nomDe = (p) => [p.prenom, p.nom].filter(Boolean).join(' ') || 'Sans nom'
  const RELATIONS = { frere: 'frère de', soeur: 'sœur de', conjoint: 'conjoint de', parent: 'parent de', enfant: 'enfant de', ami: 'ami de' }

  async function lire() {
    donnees = await api.get('/api/personnes')
  }

  async function faire(promesse, texte) {
    attente = true
    message = ''
    try {
      const r = await promesse
      message = typeof texte === 'function' ? texte(r) : texte
      await lire()
    } catch (err) {
      message = err.message
    }
    attente = false
  }

  const inventer = () => faire(api.post('/api/personnes/inventer', { nombre: Number(nombre), variete: Number(variete) }),
                                (r) => `${r.ajoutees.length} personnes inventées.`)
  const pieges = () => faire(api.post('/api/personnes/pieges'), (r) => `${r.ajoutees.length} pièges ajoutés.`)
  const epingler = (p) => faire(api.put(`/api/personnes/${p.id}`, { epinglee: !p.epinglee }), '')
  const effacer = (corps, texte) => faire(api.post('/api/personnes/effacer', corps), (r) => `${r.effacees} ${texte}.`)

  async function chercher(e) {
    e?.preventDefault()
    message = ''
    try {
      const r = await api.get('/api/carnet/personnes?q=' + encodeURIComponent(recherche))
      fiches = r.fiches
      choisies = new Set()
    } catch (err) {
      fiches = null
      message = err.message
    }
  }

  async function copier() {
    await faire(api.post('/api/personnes/copier', { carnet_ids: [...choisies] }), (r) => `${r.ajoutees.length} fiches copiées.`)
    chercher()
  }

  function basculer(id) {
    const n = new Set(choisies)
    n.has(id) ? n.delete(id) : n.add(id)
    choisies = n
  }

  onMount(lire)
</script>

<header class="mb-6">
  <h1 class="titre">Personnes</h1>
  <p class="mt-1 max-w-prose text-sm text-muted-foreground">
    Les gens des scénarios. Les numéros inventés sont dans la tranche réservée à la fiction et les adresses en
    example.org : personne ne peut être joint.
  </p>
</header>

<div class="grid gap-3 lg:grid-cols-3">
  <section class="flex flex-col gap-3 rounded-2xl border bg-card p-5">
    <h2 class="text-base font-medium">Inventer</h2>
    <label class="flex flex-col gap-1 text-sm">Combien
      <input type="number" min="1" max="200" bind:value={nombre} class="h-9 w-24 rounded-lg border border-input bg-transparent px-3" />
    </label>
    <label class="flex flex-col gap-1 text-sm">Fiches incomplètes et liens : {variete} %
      <input type="range" min="0" max="100" step="10" bind:value={variete} class="accent-[var(--app)]" />
    </label>
    <div class="mt-auto flex flex-wrap gap-1.5">
      <Button onclick={inventer} disabled={attente}><WandSparkles class="size-3.5" aria-hidden="true" />Inventer</Button>
      <Button variant="outline" onclick={pieges} disabled={attente}>Ajouter les pièges</Button>
    </div>
  </section>

  <section class="flex flex-col gap-3 rounded-2xl border bg-card p-5 lg:col-span-2">
    <h2 class="text-base font-medium">Copier depuis carnet</h2>
    {#if donnees && !donnees.copie_carnet}
      <p class="text-sm text-muted-foreground">
        Pas réglé : il faut BAC_CARNET_URL et MAISON_JETON dans la stack. La copie lit carnet sans jamais y écrire.
      </p>
    {:else}
      <form class="flex gap-1.5" onsubmit={chercher}>
        <input type="search" bind:value={recherche} placeholder="Prénom ou nom" aria-label="Chercher dans carnet"
               class="h-9 min-w-0 flex-1 rounded-lg border border-input bg-transparent px-3" />
        <Button type="submit" variant="outline"><Search class="size-3.5" aria-hidden="true" />Chercher</Button>
      </form>
      {#if fiches}
        <ul class="max-h-64 divide-y overflow-y-auto text-sm">
          {#each fiches as f (f.carnet_id)}
            <li>
              <label class="flex items-center gap-3 py-2">
                <input type="checkbox" class="size-4 accent-[var(--app)]" disabled={f.copiee}
                       checked={choisies.has(f.carnet_id)} onchange={() => basculer(f.carnet_id)} />
                <span class="flex-1">{f.prenom} {f.nom}</span>
                <span class="text-xs text-muted-foreground">{f.copiee ? 'déjà copiée' : f.naissance || 'sans date'}</span>
              </label>
            </li>
          {:else}
            <li class="py-2 text-muted-foreground">Aucune fiche ne correspond.</li>
          {/each}
        </ul>
        <Button class="self-start" onclick={copier} disabled={!choisies.size || attente}>
          <UserPlus class="size-3.5" aria-hidden="true" />Copier {choisies.size || ''} fiche{choisies.size > 1 ? 's' : ''}
        </Button>
      {/if}
      <p class="text-xs text-muted-foreground">
        Gardé : prénom, nom, naissance, genre. Effacé après {donnees?.duree_copies_jours ?? 30} jours, sauf épinglé.
      </p>
    {/if}
  </section>
</div>

{#if message}<p class="mt-4 text-sm" role="status">{message}</p>{/if}

{#if donnees}
  <section class="mt-6">
    <div class="mb-3 flex flex-wrap items-center gap-2">
      <h2 class="mr-2 text-lg font-light tracking-tight">{donnees.personnes.length} personnes</h2>
      {#each [['', 'Toutes'], ['inventee', 'Inventées'], ['piege', 'Pièges'], ['reelle', 'Copies']] as [o, nom]}
        <button type="button" onclick={() => (filtre = o)} aria-pressed={filtre === o}
                class="h-8 rounded-full border px-3 text-sm text-muted-foreground aria-pressed:border-transparent aria-pressed:bg-secondary aria-pressed:text-foreground">
          {nom}{o ? ` (${compte(o)})` : ''}
        </button>
      {/each}
      {#if affichees.length}
        <Button variant="ghost" class="ml-auto text-muted-foreground"
                onclick={() => effacer(filtre ? { origine: filtre } : { tout: true }, 'personnes effacées pour de bon')}>
          <Trash2 class="size-3.5" aria-hidden="true" />Effacer {filtre ? 'celles-ci' : 'tout'}
        </Button>
      {/if}
    </div>
    {#if affichees.length}
      <ul class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {#each affichees as p (p.id)}
          <li class={['flex min-w-0 flex-col gap-1 rounded-xl border p-3 text-sm', p.origine === 'reelle' ? 'border-primary/40' : 'bg-card']}>
            <div class="flex items-start gap-2">
              <span class="min-w-0 flex-1 truncate font-medium" title={nomDe(p)}>{nomDe(p)}</span>
              <span class="shrink-0 text-xs text-muted-foreground">{ORIGINES[p.origine]}</span>
              <button type="button" aria-pressed={p.epinglee} aria-label={p.epinglee ? 'Désépingler' : 'Épingler'}
                      onclick={() => epingler(p)} class="-m-1 grid size-8 place-items-center rounded-md text-muted-foreground aria-pressed:text-primary">
                <Pin class="size-3.5" aria-hidden="true" />
              </button>
            </div>
            <span class="text-muted-foreground">
              {p.naissance || 'Naissance inconnue'}{p.ville ? `, ${p.ville}` : ''}
            </span>
            {#if p.liens?.length}
              <span class="text-xs text-muted-foreground">
                {p.liens.filter((l) => parId[l.vers]).map((l) => `${RELATIONS[l.relation] ?? l.relation} ${nomDe(parId[l.vers])}`).join(' ; ')}
              </span>
            {/if}
            {#if p.note}<span class="text-xs text-primary">{p.note}</span>{/if}
          </li>
        {/each}
      </ul>
    {:else}
      <p class="text-sm text-muted-foreground">Personne ici pour l'instant : invente-en quelques-unes ou ajoute les pièges.</p>
    {/if}
  </section>
{/if}
