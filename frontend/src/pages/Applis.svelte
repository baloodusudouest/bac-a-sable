<script>
  // Écran de travail : une tuile par appli embarquée. « Ouvrir » démarre l'appli (et, 0.4.0, celles qu'elle lit ou à
  // qui elle écrit) puis l'ouvre sur son port, dans un nouvel onglet. En tête : la coupure (autotest) ; rouge, rien
  // ne démarre. 0.4.0 : badge « encore en démo », « lancée pour … », mémoire de toute la maison, message « arrêtée
  // pour libérer la mémoire », et une seule remise à zéro pour toute la maison simulée (au lieu de « Vider » par appli).
  import { onMount, onDestroy } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import { Badge } from '$lib/components/ui/badge/index.js'
  import ShieldCheck from '@lucide/svelte/icons/shield-check'
  import ShieldAlert from '@lucide/svelte/icons/shield-alert'
  import ExternalLink from '@lucide/svelte/icons/external-link'
  import Square from '@lucide/svelte/icons/square'
  import RotateCcw from '@lucide/svelte/icons/rotate-ccw'
  import LoaderCircle from '@lucide/svelte/icons/loader-circle'

  let donnees = $state(null)
  let autotest = $state(null)
  let enCours = $state({})            // appli → « démarrage » | « arrêt »
  let messages = $state({})
  let erreur = $state('')
  let minuteur

  // remise à zéro de la maison
  let remise = $state(null)           // aperçu : ce qui sera perdu, ce qui sera reversé
  let scenarios = $state([])
  let choix = $state('')              // identifiant du scénario à reverser ('' : aucun)
  let remiseEnCours = $state(false)
  let remiseMessage = $state('')

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
      if (r.cascade?.length) messages[a.id] = `Lancées avec elle : ${r.cascade.join(', ')}.`
    } catch (err) {
      onglet?.close()
      messages[a.id] = err.message
    }
    delete enCours[a.id]
    lire()
  }

  async function arreter(a) {
    enCours[a.id] = 'arrêt'
    try { await api.post(`/api/applis/${a.id}/arreter`) } catch (err) { messages[a.id] = err.message }
    delete enCours[a.id]
    lire()
  }

  async function toutArreter() {
    await api.post('/api/applis/tout-arreter')
    lire()
  }

  async function preparerRemise() {
    remiseMessage = ''
    const [s, apercu] = await Promise.all([api.get('/api/scenarios'), api.get('/api/maison/remise-a-zero')])
    scenarios = s.scenarios
    choix = apercu.scenario_maison ? String(apercu.scenario_maison) : (scenarios[0] ? String(scenarios[0].id) : '')
    remise = choix ? await api.get(`/api/maison/remise-a-zero?scenario=${choix}`) : apercu
  }

  async function changerChoix() {
    remise = await api.get(choix ? `/api/maison/remise-a-zero?scenario=${choix}` : '/api/maison/remise-a-zero')
  }

  async function remettre() {
    remiseEnCours = true
    remiseMessage = ''
    try {
      const r = await api.post('/api/maison/remise-a-zero', { confirmer: true, scenario: choix ? Number(choix) : null })
      remiseMessage = r.scenario ? `Maison remise à zéro, scénario reversé (${r.personnes} personnes). Lancées : ${r.ouvertes.join(', ') || 'aucune'}.`
                                 : 'Maison remise à zéro : toutes les applis simulées sont vides.'
      remise = null
    } catch (err) {
      remiseMessage = err.message
    }
    remiseEnCours = false
    lire()
  }

  const duree = (s) => (s < 60 ? `${s} s` : s < 3600 ? `${Math.round(s / 60)} min` : `${Math.round(s / 3600)} h`)
  const lancees = $derived(donnees ? donnees.applis.filter((a) => a.etat === 'demarree') : [])
  const pourcent = $derived(donnees ? Math.min(100, Math.round((100 * donnees.memoire_mo) / donnees.memoire_limite_mo)) : 0)

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
      Les vraies applis, sur une fausse maison. Elles se parlent comme dans la vraie ; rien ne sort d'ici.
    </p>
  </div>
  <div class="flex flex-wrap gap-1.5">
    {#if lancees.length}
      <Button variant="outline" onclick={toutArreter}><Square class="size-3.5" aria-hidden="true" />Tout arrêter ({lancees.length})</Button>
    {/if}
    <Button variant="outline" onclick={preparerRemise} disabled={remiseEnCours}>
      <RotateCcw class="size-3.5" aria-hidden="true" />Remettre la maison à zéro
    </Button>
  </div>
</header>

{#if autotest}
  <a href="#/reglages"
     class={['mb-5 flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm',
             autotest.ok ? 'rayures-douces' : 'border-destructive/60 bg-destructive/10 text-destructive']}>
    {#if autotest.ok}
      <ShieldCheck class="size-5 shrink-0 text-primary" aria-hidden="true" />
      <span>{autotest.message}{autotest.liens ? ` ${autotest.liens.message}` : ''}</span>
    {:else}
      <ShieldAlert class="size-5 shrink-0" aria-hidden="true" />
      <span><strong>Coupure non prouvée.</strong> {autotest.message}</span>
    {/if}
  </a>
{/if}

{#if remise}
  <section class="mb-5 flex flex-col gap-3 rounded-2xl border border-destructive/50 bg-card p-5" aria-labelledby="titre-remise">
    <h2 id="titre-remise" class="text-base font-medium">Remettre toute la maison simulée à zéro ?</h2>
    <div class="grid gap-4 text-sm sm:grid-cols-2">
      <div class="min-w-0">
        <h3 class="mb-1 font-medium text-destructive">Sera perdu</h3>
        <ul class="list-disc pl-5 text-muted-foreground">
          <li>{remise.perdu.applis.length
            ? `les données de ${remise.perdu.applis.length} appli${remise.perdu.applis.length > 1 ? 's' : ''} (${remise.perdu.applis.map((a) => a.nom).join(', ')}) ;`
            : 'les données des applis (aucune pour l’instant, Gazette comprise) ;'}</li>
          <li>{remise.perdu.soiree ? `la soirée jouée${remise.perdu.soiree_cloturee ? ' (clôturée)' : ''}` : 'les soirées jouées (aucune en cours)'} ;</li>
          <li>les journaux des applis ({remise.perdu.ecritures} écriture{remise.perdu.ecritures > 1 ? 's' : ''} notée{remise.perdu.ecritures > 1 ? 's' : ''}) ;</li>
          <li>les photos envoyées ({remise.perdu.photos}).</li>
        </ul>
        <p class="mt-1 text-xs text-muted-foreground">Les personnes et les scénarios du Bac à sable restent.</p>
      </div>
      <div class="min-w-0">
        <h3 class="mb-1 font-medium">Sera reversé</h3>
        <label class="flex flex-col gap-1">
          <span class="sr-only">Scénario à reverser</span>
          <select bind:value={choix} onchange={changerChoix} class="h-9 max-w-full rounded-lg border border-input bg-transparent px-2">
            <option value="">Aucun (maison vide)</option>
            {#each scenarios as s (s.id)}<option value={String(s.id)}>{s.nom}</option>{/each}
          </select>
        </label>
        {#if remise.reverse}
          <p class="mt-2 text-muted-foreground">
            {remise.reverse.personnes} personne{remise.reverse.personnes > 1 ? 's' : ''}{remise.reverse.copies ? ` (dont ${remise.reverse.copies} copie${remise.reverse.copies > 1 ? 's' : ''} de vraies fiches, jamais montrée${remise.reverse.copies > 1 ? 's' : ''} à la Gazette)` : ''},
            versées dans les applis branchées ; lancées : {remise.reverse.applis.join(', ')}, avec celles qu'elles lisent.
            {#if remise.reverse.soiree}La soirée Douze points est {remise.reverse.soiree_cloturee ? 'remontée et déjà clôturée' : 'remontée, à jouer'}.{/if}
          </p>
        {/if}
      </div>
    </div>
    <div class="flex flex-wrap gap-1.5">
      <Button variant="destructive" onclick={remettre} disabled={remiseEnCours}>
        {#if remiseEnCours}<LoaderCircle class="size-3.5 animate-spin" aria-hidden="true" />{:else}<RotateCcw class="size-3.5" aria-hidden="true" />{/if}
        Remettre à zéro
      </Button>
      <Button variant="ghost" onclick={() => (remise = null)} disabled={remiseEnCours}>Annuler</Button>
    </div>
  </section>
{/if}
{#if remiseMessage}<p class="mb-4 text-sm" role="status">{remiseMessage}</p>{/if}

{#if erreur}<p class="mb-4 text-sm text-destructive" role="alert">{erreur}</p>{/if}

{#if donnees}
  <div class="mb-4 flex max-w-md flex-col gap-1 text-xs text-muted-foreground">
    <span>Mémoire de toute la maison : {donnees.memoire_mo} Mo sur {donnees.memoire_limite_mo}</span>
    <span class="h-1.5 overflow-hidden rounded-full bg-muted" aria-hidden="true">
      <span class={['block h-full rounded-full', pourcent > 90 ? 'bg-destructive' : 'rayures']} style={`width:${pourcent}%`}></span>
    </span>
  </div>
  <ul class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
    {#each donnees.applis as a (a.id)}
      {@const vivante = a.etat === 'demarree'}
      <li class="flex min-w-0 flex-col gap-3 rounded-2xl border bg-card p-4">
        <div class="flex items-start gap-3">
          <span class={['mt-1 size-2.5 shrink-0 rounded-full', vivante ? 'rayures' : a.etat === 'erreur' ? 'bg-destructive' : 'bg-muted-foreground/40']}
                aria-hidden="true"></span>
          <div class="min-w-0 flex-1">
            <h2 class="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-base font-medium">
              <span class="truncate">{a.nom}</span>
              {#if a.demo}<Badge variant="outline" title="Données de démonstration de son dépôt ; ses liens avec les applis branchées restent coupés">encore en démo</Badge>{/if}
            </h2>
            <p class="text-xs text-muted-foreground">
              Version {a.version}, port {a.port}{#if a.personnes}. Reçoit les personnes du scénario{/if}{#if a.appelle?.length}. Lit ou écrit : {a.appelle.join(', ')}{/if}
            </p>
          </div>
        </div>

        <p class="text-sm text-muted-foreground" aria-live="polite">
          {#if enCours[a.id]}
            <LoaderCircle class="mr-1 inline size-3.5 animate-spin" aria-hidden="true" />{enCours[a.id]}…
          {:else if !a.installee}
            Absente de cette image.
          {:else if vivante}
            {#if a.lancee_pour}Lancée pour {a.lancee_pour}, depuis{:else}Lancée depuis{/if} {duree(a.depuis)} ; {a.memoire_mo} Mo.
            {#if a.inactive_depuis > 60}Inactive depuis {duree(a.inactive_depuis)} (arrêt à {donnees.arret_minutes} min).{/if}
          {:else if a.arret_memoire}
            <span>{a.nom} a été arrêtée pour libérer la mémoire ; ses données sont gardées.</span>
          {:else if a.etat === 'erreur'}
            <span class="text-destructive">{a.erreur}</span>
          {:else}
            Arrêtée. Elle démarre à l'ouverture.
          {/if}
        </p>
        {#if messages[a.id]}<p class="text-sm" role="status">{messages[a.id]}</p>{/if}

        <div class="mt-auto flex flex-wrap items-center gap-1.5">
          <Button onclick={() => ouvrir(a)} disabled={!!enCours[a.id] || !!donnees.bloque || donnees.remise || !a.installee}>
            <ExternalLink class="size-3.5" aria-hidden="true" />{a.arret_memoire ? 'La rouvrir' : 'Ouvrir'}
          </Button>
          {#if vivante}
            <Button variant="ghost" onclick={() => arreter(a)} disabled={!!enCours[a.id]}>
              <Square class="size-3.5" aria-hidden="true" />Arrêter
            </Button>
          {/if}
        </div>
      </li>
    {/each}
  </ul>
  <p class="mt-6 max-w-prose text-xs text-muted-foreground">
    Ouvrir une appli démarre aussi celles qu'elle lit ou à qui elle écrit. Au-delà de {donnees.memoire_limite_mo} Mo
    pour toute la maison, l'appli utilisée il y a le plus longtemps s'arrête (ses données sont gardées). Les applis
    « encore en démo » s'ouvrent sur les données de démonstration de leur dépôt.
  </p>
{:else if !erreur}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
