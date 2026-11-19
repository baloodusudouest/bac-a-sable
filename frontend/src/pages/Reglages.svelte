<script>
  // Réglages : la coupure (autotest), les réglages de Douze points, les applis embarquées et leurs versions,
  // la version et la déconnexion.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import ShieldCheck from '@lucide/svelte/icons/shield-check'
  import ShieldAlert from '@lucide/svelte/icons/shield-alert'

  let { session, deconnecter } = $props()
  let autotest = $state(null)
  let synthese = $state(null)
  let reglages = $state(null)
  let brouillon = $state({})
  let message = $state('')
  let essai = $state(false)
  const modifie = $derived(reglages && JSON.stringify(brouillon) !== JSON.stringify(reglages))

  async function lire() {
    ;[autotest, synthese, reglages] = await Promise.all([api.get('/api/autotest'), api.get('/api/synthese'),
                                                         api.get('/api/reglages').then((r) => r.reglages)])
    brouillon = { ...reglages }
  }

  async function relancer() {
    essai = true
    try { autotest = await api.post('/api/autotest') } catch (err) { message = err.message }
    essai = false
  }

  async function enregistrer(e) {
    e.preventDefault()
    try {
      const corps = { douze_tempo: Number(brouillon.douze_tempo), douze_telephones: Number(brouillon.douze_telephones),
                      douze_chansons: Number(brouillon.douze_chansons) }
      reglages = (await api.put('/api/reglages', corps)).reglages
      brouillon = { ...reglages }
      message = 'Réglages enregistrés.'
    } catch (err) {
      message = err.message
    }
  }

  onMount(lire)
</script>

<header class="mb-6"><h1 class="titre">Réglages</h1></header>

<div class="grid gap-3 lg:grid-cols-2">
  {#if autotest}
    <section class={['flex flex-col gap-3 rounded-2xl border p-5 lg:col-span-2', autotest.ok ? 'rayures-douces bg-card' : 'border-destructive/60 bg-destructive/10']}>
      <h2 class="flex items-center gap-2 text-base font-medium">
        {#if autotest.ok}<ShieldCheck class="size-5 text-primary" aria-hidden="true" />Rien ne sort{:else}<ShieldAlert class="size-5 text-destructive" aria-hidden="true" />Coupure non prouvée{/if}
      </h2>
      <p class="text-sm">{autotest.message}</p>
      {#if autotest.essais?.length}
        <ul class="grid gap-x-6 gap-y-1 text-sm sm:grid-cols-2">
          {#each autotest.essais as e}
            <li class="flex justify-between gap-3">
              <span class="truncate">{e.cible}</span>
              <span class={e.passe ? 'text-destructive' : 'text-muted-foreground'}>{e.passe ? 'joignable' : e.motif}</span>
            </li>
          {/each}
        </ul>
      {/if}
      <p class="text-xs text-muted-foreground">
        Chaque essai part d'un processus monté comme une appli simulée. Le Bac à sable lui-même peut joindre carnet,
        pour copier de vraies fiches, sans jamais transmettre cet accès aux applis.
      </p>
      <Button variant="outline" class="self-start" onclick={relancer} disabled={essai}>{essai ? 'Essai…' : "Refaire l'essai"}</Button>
    </section>
  {/if}

  {#if reglages}
    <form class="flex flex-col gap-3 rounded-2xl border bg-card p-5" onsubmit={enregistrer}>
      <h2 class="text-base font-medium">Douze points, par défaut</h2>
      <label class="flex items-center justify-between gap-3 text-sm">Secondes entre deux notes d'un téléphone
        <input type="number" min="0" max="120" step="0.5" bind:value={brouillon.douze_tempo} class="h-9 w-24 rounded-lg border border-input bg-transparent px-3" />
      </label>
      <label class="flex items-center justify-between gap-3 text-sm">Téléphones simulés
        <input type="number" min="0" max="60" bind:value={brouillon.douze_telephones} class="h-9 w-24 rounded-lg border border-input bg-transparent px-3" />
      </label>
      <label class="flex items-center justify-between gap-3 text-sm">Chansons
        <input type="number" min="1" max="26" bind:value={brouillon.douze_chansons} class="h-9 w-24 rounded-lg border border-input bg-transparent px-3" />
      </label>
      <Button type="submit" class="self-start" disabled={!modifie}>Enregistrer</Button>
      {#if message}<p class="text-sm" role="status">{message}</p>{/if}
    </form>
  {/if}

  {#if synthese}
    <section class="flex flex-col gap-3 rounded-2xl border bg-card p-5">
      <h2 class="text-base font-medium">Applis embarquées</h2>
      <ul class="divide-y text-sm">
        {#each synthese.embarquees as a (a.id)}
          <li class="flex justify-between gap-3 py-1.5">
            <span>{a.nom}</span>
            <span class="tabular-nums text-muted-foreground">{a.installee ? `${a.version} (${a.sha})` : 'absente'}</span>
          </li>
        {/each}
      </ul>
      <p class="text-xs text-muted-foreground">
        Mémoire : Bac à sable {synthese.memoire_bac_mo} Mo, applis lancées {synthese.memoire_applis_mo} Mo.
        Copie depuis carnet : {synthese.carnet_relie ? 'réglée' : 'pas réglée'}.
      </p>
    </section>
  {/if}

  <section class="flex flex-col gap-3 rounded-2xl border bg-card p-5 lg:col-span-2">
    <p class="text-sm text-muted-foreground">Bac à sable {session.version}</p>
    <Button variant="outline" class="self-start" onclick={deconnecter}>Se déconnecter</Button>
  </section>
</div>
