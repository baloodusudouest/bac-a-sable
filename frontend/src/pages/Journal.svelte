<script>
  // Journal : ce que les applis simulées ont tenté. « A écrit » : une écriture reçue par un faux service (elle
  // serait partie chez le vrai). « Sortie refusée » : la garde a bloqué une connexion vers l'extérieur.
  import { onMount, onDestroy } from 'svelte'
  import { api } from '$lib/api.js'
  import RefreshCw from '@lucide/svelte/icons/refresh-cw'
  import { Button } from '$lib/components/ui/button/index.js'

  const SORTES = { ecriture: 'A écrit', sortie_refusee: 'Sortie refusée', nom_refuse: 'Nom non résolu' }
  let applis = $state([])
  let appli = $state('')
  let sorte = $state('')
  let j = $state(null)
  let minuteur

  async function lire() {
    const params = new URLSearchParams({ appli, sorte, limite: '400' })
    j = await api.get('/api/journal?' + params)
  }

  const heure = (q) => (q ? q.slice(11, 19) : '')
  const jour = (q) => (q ? q.slice(0, 10) : '')
  const detail = (x) => x.sorte === 'ecriture' ? `${x.action} chez ${x.service}` : x.vers || x.nom || ''

  onMount(async () => {
    applis = (await api.get('/api/applis')).applis
    lire()
    minuteur = setInterval(lire, 5000)
  })
  onDestroy(() => clearInterval(minuteur))
</script>

<header class="mb-6">
  <h1 class="titre">Journal</h1>
  <p class="mt-1 max-w-prose text-sm text-muted-foreground">
    Ce qui serait parti chez les vrais services. Rien n'est sorti : tout s'est arrêté dans la fausse maison ou à la garde.
  </p>
</header>

<div class="mb-4 flex flex-wrap items-center gap-2">
  <select bind:value={appli} onchange={lire} aria-label="Appli" class="h-9 rounded-lg border border-input bg-transparent px-2 text-sm">
    <option value="">Toutes les applis</option>
    {#each applis as a (a.id)}<option value={a.id}>{a.nom}</option>{/each}
  </select>
  <select bind:value={sorte} onchange={lire} aria-label="Sorte" class="h-9 rounded-lg border border-input bg-transparent px-2 text-sm">
    <option value="">Tout</option>
    {#each Object.entries(SORTES) as [k, v]}<option value={k}>{v}</option>{/each}
  </select>
  <Button variant="ghost" onclick={lire}><RefreshCw class="size-3.5" aria-hidden="true" />Relire</Button>
  {#if j}
    <span class="ml-auto text-sm text-muted-foreground">
      {j.compte.ecriture} écritures, {j.compte.sortie_refusee + j.compte.nom_refuse} sorties refusées
    </span>
  {/if}
</div>

{#if j}
  {#if j.lignes.length}
    <div class="overflow-x-auto rounded-2xl border bg-card">
      <table class="w-full text-left text-sm">
        <thead class="text-xs text-muted-foreground">
          <tr><th class="px-4 py-2 font-normal">Quand</th><th class="px-4 py-2 font-normal">Appli</th><th class="px-4 py-2 font-normal">Quoi</th><th class="px-4 py-2 font-normal">Détail</th></tr>
        </thead>
        <tbody class="divide-y">
          {#each j.lignes as x, i (i)}
            <tr>
              <td class="whitespace-nowrap px-4 py-2 tabular-nums text-muted-foreground" title={jour(x.quand)}>{heure(x.quand)}</td>
              <td class="whitespace-nowrap px-4 py-2">{applis.find((a) => a.id === x.appli)?.nom ?? x.appli}</td>
              <td class={['whitespace-nowrap px-4 py-2', x.sorte === 'ecriture' ? 'text-primary' : 'text-muted-foreground']}>{SORTES[x.sorte] ?? x.sorte}</td>
              <td class="break-all px-4 py-2 text-muted-foreground">{detail(x)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <p class="text-sm text-muted-foreground">Rien pour l'instant. Ouvre une appli et fais-y quelque chose qui écrit.</p>
  {/if}
{/if}
