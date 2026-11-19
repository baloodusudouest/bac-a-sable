<script>
  // Écran de travail : une tuile par appli embarquée. « Ouvrir » démarre l'appli (si elle dort) puis l'ouvre sur son
  // port, dans un nouvel onglet. En tête : la coupure (autotest) ; rouge, rien ne démarre.
  import { onMount, onDestroy } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import ShieldCheck from '@lucide/svelte/icons/shield-check'
  import ShieldAlert from '@lucide/svelte/icons/shield-alert'
  import ExternalLink from '@lucide/svelte/icons/external-link'
  import Square from '@lucide/svelte/icons/square'
  import Trash2 from '@lucide/svelte/icons/trash-2'
  import LoaderCircle from '@lucide/svelte/icons/loader-circle'

  let donnees = $state(null)
  let autotest = $state(null)
  let enCours = $state({})            // appli → « démarrage » | « arrêt » | « vidage »
  let messages = $state({})
  let erreur = $state('')
  let minuteur

  async function lire() {
    try {
      donnees = await api.get('/api/applis')
      erreur = ''
    } catch (err) {
      erreur = err.message
    }
  }

  async function ouvrir(a) {
    // L'onglet est ouvert tout de suite (sinon le navigateur le bloque après une attente), puis rempli.
    const onglet = window.open('', '_blank')
    enCours[a.id] = 'démarrage'
    messages[a.id] = ''
    try {
      const r = await api.post(`/api/applis/${a.id}/demarrer`)
      if (onglet) onglet.location = r.adresse
      else location.href = r.adresse
    } catch (err) {
      onglet?.close()
      messages[a.id] = err.message
    }
    delete enCours[a.id]
    lire()
  }

  async function geste(a, quoi, libelle) {
    enCours[a.id] = libelle
    try {
      await api.post(`/api/applis/${a.id}/${quoi}`)
      messages[a.id] = quoi === 'vider' ? 'Données simulées jetées : la prochaine ouverture repart de zéro.' : ''
    } catch (err) {
      messages[a.id] = err.message
    }
    delete enCours[a.id]
    lire()
  }

  async function toutArreter() {
    await api.post('/api/applis/tout-arreter')
    lire()
  }

  const duree = (s) => (s < 60 ? `${s} s` : s < 3600 ? `${Math.round(s / 60)} min` : `${Math.round(s / 3600)} h`)
  const lancees = $derived(donnees ? donnees.applis.filter((a) => a.etat === 'demarree') : [])

  onMount(async () => {
    lire()
    try { autotest = await api.get('/api/autotest') } catch { /* lu plus tard */ }
    minuteur = setInterval(lire, 5000)
  })
  onDestroy(() => clearInterval(minuteur))
</script>

<header class="mb-6 flex flex-wrap items-end justify-between gap-3">
  <div>
    <h1 class="titre">Applis</h1>
    <p class="mt-1 max-w-prose text-sm text-muted-foreground">
      Les vraies applis, sur une fausse maison. Ce que tu y fais ne sort pas d'ici.
    </p>
  </div>
  {#if lancees.length}
    <Button variant="outline" onclick={toutArreter}><Square class="size-3.5" aria-hidden="true" />Tout arrêter ({lancees.length})</Button>
  {/if}
</header>

{#if autotest}
  <a href="#/reglages"
     class={['mb-5 flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm',
             autotest.ok ? 'rayures-douces' : 'border-destructive/60 bg-destructive/10 text-destructive']}>
    {#if autotest.ok}
      <ShieldCheck class="size-5 shrink-0 text-primary" aria-hidden="true" />
      <span>{autotest.message}</span>
    {:else}
      <ShieldAlert class="size-5 shrink-0" aria-hidden="true" />
      <span><strong>Coupure non prouvée.</strong> {autotest.message}</span>
    {/if}
  </a>
{/if}

{#if erreur}<p class="mb-4 text-sm text-destructive" role="alert">{erreur}</p>{/if}

{#if donnees}
  <ul class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
    {#each donnees.applis as a (a.id)}
      {@const vivante = a.etat === 'demarree'}
      <li class="flex min-w-0 flex-col gap-3 rounded-2xl border bg-card p-4">
        <div class="flex items-start gap-3">
          <span class={['mt-1 size-2.5 shrink-0 rounded-full', vivante ? 'rayures' : a.etat === 'erreur' ? 'bg-destructive' : 'bg-muted-foreground/40']}
                aria-hidden="true"></span>
          <div class="min-w-0 flex-1">
            <h2 class="truncate text-base font-medium">{a.nom}</h2>
            <p class="text-xs text-muted-foreground">
              Version {a.version}, port {a.port}{#if a.personnes}. Reçoit les personnes du scénario{/if}
            </p>
          </div>
        </div>

        <p class="text-sm text-muted-foreground" aria-live="polite">
          {#if enCours[a.id]}
            <LoaderCircle class="mr-1 inline size-3.5 animate-spin" aria-hidden="true" />{enCours[a.id]}…
          {:else if !a.installee}
            Absente de cette image.
          {:else if vivante}
            Lancée depuis {duree(a.depuis)}, {a.memoire_mo} Mo sur {a.memoire_max}.
            {#if a.inactive_depuis > 60}Inactive depuis {duree(a.inactive_depuis)} (arrêt à {donnees.arret_minutes} min).{/if}
          {:else if a.etat === 'erreur'}
            <span class="text-destructive">{a.erreur}</span>
          {:else}
            Arrêtée. Elle démarre à l'ouverture.
          {/if}
        </p>
        {#if messages[a.id]}<p class="text-sm" role="status">{messages[a.id]}</p>{/if}

        <div class="mt-auto flex flex-wrap items-center gap-1.5">
          <Button onclick={() => ouvrir(a)} disabled={!!enCours[a.id] || !!donnees.bloque || !a.installee}>
            <ExternalLink class="size-3.5" aria-hidden="true" />Ouvrir
          </Button>
          {#if vivante}
            <Button variant="ghost" onclick={() => geste(a, 'arreter', 'arrêt')} disabled={!!enCours[a.id]}>
              <Square class="size-3.5" aria-hidden="true" />Arrêter
            </Button>
          {/if}
          <Button variant="ghost" class="ml-auto text-muted-foreground" onclick={() => geste(a, 'vider', 'vidage')}
                  disabled={!!enCours[a.id]} aria-label={`Vider les données simulées de ${a.nom}`}>
            <Trash2 class="size-3.5" aria-hidden="true" />Vider
          </Button>
        </div>
      </li>
    {/each}
  </ul>
  <p class="mt-6 max-w-prose text-xs text-muted-foreground">
    Au plus {donnees.max_simultanees} applis lancées en même temps : la plus ancienne s'arrête pour laisser la place.
    Sans scénario, une appli s'ouvre sur les données de démonstration de son dépôt.
  </p>
{:else if !erreur}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
