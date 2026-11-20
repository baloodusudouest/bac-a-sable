<script>
  // Soirée Douze points simulée : téléphones automatiques, mur de téléphones (l'écran invité réel de chacun),
  // QR code pour rejoindre avec un vrai iPhone sur un prénom resté libre. La soirée se monte depuis Scénarios.
  // 0.4.0 : « Clôturer la soirée » la joue jusqu'au bout (dévoilement, fin, clôture) : carnet simulé la reçoit et la
  // Gazette simulée peut en faire son numéro.
  import { onMount, onDestroy } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Play from '@lucide/svelte/icons/play'
  import FastForward from '@lucide/svelte/icons/fast-forward'
  import Square from '@lucide/svelte/icons/square'
  import ExternalLink from '@lucide/svelte/icons/external-link'
  import Smartphone from '@lucide/svelte/icons/smartphone'
  import Flag from '@lucide/svelte/icons/flag'
  import LoaderCircle from '@lucide/svelte/icons/loader-circle'

  let s = $state(null)
  let erreur = $state('')
  let tempo = $state(4)
  let envoyer = $state(true)
  let mur = $state(true)
  let echelle = $state(0.5)
  let cloture = $state('')         // « en cours » pendant la clôture
  let minuteur

  async function lire() {
    try {
      s = await api.get('/api/douze')
      erreur = ''
    } catch (err) {
      erreur = err.message
    }
  }

  async function jouer(avance) {
    try {
      s = { ...s, ...(await api.post('/api/douze/jouer', { tempo, envoyer, avance_rapide: avance })) }
    } catch (err) {
      erreur = err.message
    }
  }

  async function arreter() {
    await api.post('/api/douze/arreter')
    lire()
  }

  async function cloturer() {
    cloture = 'en cours'
    erreur = ''
    try {
      s = { ...s, ...(await api.post('/api/douze/cloturer')) }
    } catch (err) {
      erreur = err.message
    }
    cloture = ''
  }

  const ecranInvite = (t) => `${s.adresse}/invite/${s.jeton_invite}#saisie=${t.jeton}`
  const pret = $derived(s && s.lancee && s.jeton_invite)

  onMount(() => {
    lire()
    minuteur = setInterval(lire, 2000)
  })
  onDestroy(() => clearInterval(minuteur))
</script>

<header class="mb-6">
  <h1 class="titre">Soirée</h1>
  <p class="mt-1 max-w-prose text-sm text-muted-foreground">
    Une soirée Douze points jouée par des téléphones simulés. Les prénoms qui restent libres attendent de vrais iPhone.
  </p>
</header>

{#if erreur}<p class="mb-4 text-sm text-destructive" role="alert">{erreur}</p>{/if}

{#if s && !pret}
  <section class="rounded-2xl border bg-card p-5">
    <h2 class="text-base font-medium">Pas de soirée en cours</h2>
    <p class="mt-1 max-w-prose text-sm text-muted-foreground">
      Crée un scénario avec Douze points et des personnes, puis « Jouer sur Douze points » : la soirée est montée
      comme le ferait l'hôte (invités, chansons inventées, ouverture), et les téléphones t'attendent ici.
    </p>
    <Button class="mt-4" href="#/scenarios">Aller aux scénarios</Button>
  </section>
{:else if s}
  <div class="grid gap-3 lg:grid-cols-[2fr_1fr]">
    <section class="flex flex-col gap-4 rounded-2xl border bg-card p-5">
      <div class="flex flex-wrap items-baseline justify-between gap-2">
        <h2 class="text-base font-medium">{s.telephones.length} téléphones simulés, {s.chansons} chansons</h2>
        <a class="inline-flex items-center gap-1 text-sm text-primary underline-offset-4 hover:underline" href={s.adresse} target="_blank" rel="noopener">
          Régie de l'hôte<ExternalLink class="size-3.5" aria-hidden="true" />
        </a>
      </div>
      <div class="flex flex-wrap items-end gap-4">
        <label class="flex flex-col gap-1 text-sm">
          Une note toutes les {tempo} s environ
          <input type="range" min="1" max="30" step="1" bind:value={tempo} class="w-48 accent-[var(--app)]" />
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" bind:checked={envoyer} class="size-4 accent-[var(--app)]" />Envoyer à la fin
        </label>
      </div>
      <div class="flex flex-wrap gap-1.5">
        {#if s.en_cours}
          <Button onclick={arreter}><Square class="size-3.5" aria-hidden="true" />Arrêter les téléphones</Button>
        {:else}
          <Button onclick={() => jouer(false)}><Play class="size-3.5" aria-hidden="true" />Faire noter</Button>
          <Button variant="outline" onclick={() => jouer(true)}><FastForward class="size-3.5" aria-hidden="true" />Avance rapide</Button>
        {/if}
        {#if !s.cloturee}
          <Button variant="outline" onclick={cloturer} disabled={!!cloture}>
            {#if cloture}<LoaderCircle class="size-3.5 animate-spin" aria-hidden="true" />{:else}<Flag class="size-3.5" aria-hidden="true" />{/if}
            Clôturer la soirée
          </Button>
        {/if}
      </div>
      {#if s.message}<p class="text-sm" role="status">{s.message}</p>{/if}
      {#if s.cloturee}
        <p class="text-sm text-muted-foreground">
          Clôturée : carnet simulé l'a reçue ; la Gazette simulée en fait son numéro (« À traiter », ou « Relire Douze points »).
        </p>
      {/if}
      <ul class="divide-y text-sm">
        {#each s.telephones as t (t.participation_id)}
          <li class="flex flex-wrap items-center gap-x-3 gap-y-1 py-2">
            <span class={['size-2 rounded-full', t.etat === 'note' ? 'rayures' : t.etat === 'envoyé' ? 'bg-valide' : t.etat === 'erreur' ? 'bg-destructive' : 'bg-muted-foreground/40']}
                  aria-hidden="true"></span>
            <span class="min-w-24 font-medium">{t.prenom}</span>
            <span class="text-muted-foreground">{t.profil_nom}{t.prefere ? ` (${t.prefere})` : ''}</span>
            <span class="ml-auto tabular-nums text-muted-foreground">{t.notees}/{s.chansons}, {t.etat}</span>
            {#if t.erreur}<span class="w-full text-xs text-destructive">{t.erreur}</span>{/if}
          </li>
        {/each}
      </ul>
    </section>

    <section class="flex flex-col gap-3 rounded-2xl border bg-card p-5">
      <h2 class="flex items-center gap-2 text-base font-medium"><Smartphone class="size-4" aria-hidden="true" />Avec un vrai iPhone</h2>
      {#if s.libres.length}
        <img src={`/api/douze/qr.svg?j=${s.jeton_invite}`} alt="QR code de la soirée simulée" class="w-44 self-center rounded-lg" />
        <p class="text-sm text-muted-foreground">Prénoms libres : {s.libres.map((l) => l.prenom).join(', ')}.</p>
        <p class="break-all text-xs text-muted-foreground">{s.lien_invites}</p>
      {:else}
        <p class="text-sm text-muted-foreground">
          Tous les prénoms ont un téléphone simulé. Pour en garder pour de vrais iPhone, baisse le nombre de téléphones
          dans le scénario (réglage Douze points).
        </p>
      {/if}
      <p class="text-xs text-muted-foreground">L'iPhone doit être sur le même réseau que le NAS.</p>
    </section>
  </div>

  <section class="mt-6">
    <div class="mb-3 flex flex-wrap items-center gap-4">
      <h2 class="text-lg font-light tracking-tight">Mur de téléphones</h2>
      <label class="flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={mur} class="size-4 accent-[var(--app)]" />Afficher</label>
      {#if mur}
        <label class="flex items-center gap-2 text-sm">Taille
          <select bind:value={echelle} class="h-8 rounded-md border border-input bg-transparent px-2">
            {#each [[0.35, 'Petite'], [0.5, 'Moyenne'], [0.7, 'Grande']] as [v, n]}<option value={v}>{n}</option>{/each}
          </select>
        </label>
      {/if}
    </div>
    {#if mur}
      <p class="mb-3 max-w-prose text-xs text-muted-foreground">
        Chaque cadre est le vrai écran invité, ouvert au nom du téléphone simulé (lien de saisie de l'hôte) : tu peux
        aussi y noter à sa place.
      </p>
      <!-- Chaque écran est rendu à la vraie taille d'un iPhone (390 × 844) puis réduit : la mise en page est celle
           du téléphone, pas celle d'une fenêtre étroite. -->
      <ul class="flex flex-wrap gap-4">
        {#each s.telephones.filter((t) => t.jeton) as t (t.participation_id)}
          <li class="flex flex-col items-center gap-2">
            <div class="relative overflow-hidden rounded-[1.6rem] border-[6px] border-[#2a2521] bg-background shadow-xl"
                 style={`width:${390 * echelle + 12}px;height:${844 * echelle + 12}px`}>
              <iframe title={`Téléphone de ${t.prenom}`} src={ecranInvite(t)} width="390" height="844"
                      class="absolute top-0 left-0 origin-top-left border-0" style={`transform:scale(${echelle})`}></iframe>
            </div>
            <span class="text-sm">{t.prenom}</span>
          </li>
        {:else}
          <li class="col-span-full text-sm text-muted-foreground">Les cadres apparaissent dès qu'un téléphone a choisi son prénom (« Faire noter »).</li>
        {/each}
      </ul>
    {/if}
  </section>
{:else if !erreur}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}
