<script>
  // Navigation commune aux applis : rail à gauche sur PC, pilule d'icônes en bas sur iPhone.
  // Entrées : Applis (écran de travail), Soirée (Douze points simulé), Personnes, Scénarios, Journal, Connexion
  // (0.2.0 : écran commun des services, contrat 3), Réglages.
  import { onMount } from 'svelte'
  import { fly } from 'svelte/transition'
  import Boxes from '@lucide/svelte/icons/boxes'
  import MicVocal from '@lucide/svelte/icons/mic-vocal'
  import Users from '@lucide/svelte/icons/users'
  import Clapperboard from '@lucide/svelte/icons/clapperboard'
  import ScrollText from '@lucide/svelte/icons/scroll-text'
  import SlidersHorizontal from '@lucide/svelte/icons/sliders-horizontal'
  import Plug from '@lucide/svelte/icons/plug'
  import { api } from '$lib/api.js'
  import Filigrane from '$lib/Filigrane.svelte'
  import Connexion from './pages/Connexion.svelte'
  import Applis from './pages/Applis.svelte'
  import Soiree from './pages/Soiree.svelte'
  import Personnes from './pages/Personnes.svelte'
  import Scenarios from './pages/Scenarios.svelte'
  import Journal from './pages/Journal.svelte'
  import Reglages from './pages/Reglages.svelte'
  import Services from '$lib/services/Services.svelte'   // 0.2.0 : écran commun (contrat 3, socle 0.11.0)

  const onglets = [
    { page: 'applis', nom: 'Applis', icone: Boxes },
    { page: 'soiree', nom: 'Soirée', icone: MicVocal },
    { page: 'personnes', nom: 'Personnes', icone: Users },
    { page: 'scenarios', nom: 'Scénarios', icone: Clapperboard },
    { page: 'journal', nom: 'Journal', icone: ScrollText },
    { page: 'connexion', nom: 'Connexion', icone: Plug },
    { page: 'reglages', nom: 'Réglages', icone: SlidersHorizontal },
  ]

  let connecte = $state(null)
  let session = $state({ version: '' })
  let page = $state(lirePage())

  function lirePage() {
    const p = location.hash.replace('#/', '')
    return onglets.some((o) => o.page === p) ? p : 'applis'
  }

  async function verifier() {
    try {
      const s = await api.get('/api/session')
      session = s
      connecte = s.connecte
    } catch {
      connecte = false
    }
  }

  async function deconnecter() {
    try { await api.post('/api/deconnexion') } catch { /* déjà déconnecté */ }
    connecte = false
  }

  onMount(verifier)
</script>

<svelte:window onhashchange={() => (page = lirePage())} onbac-deconnecte={() => (connecte = false)} />

<!-- 0.1.2 : filigrane sur tous les écrans, connexion comprise (reconnaître une capture du Bac à sable) -->
<Filigrane sousTitre={`Bac à sable ${session.version || ''} — écran de pilotage`.replace('  ', ' ')} />

{#if connecte === false}
  <Connexion onconnecte={verifier} />
{:else if connecte}
  <div class="md:pl-52">
    <nav
      aria-label="Sections"
      class="fixed bottom-[calc(0.75rem+env(safe-area-inset-bottom))] left-1/2 z-20 flex -translate-x-1/2 items-center gap-0.5 rounded-full border bg-card/85 p-1.5 shadow-lg backdrop-blur-md
             md:inset-y-0 md:left-0 md:w-52 md:translate-x-0 md:flex-col md:items-stretch md:gap-1 md:rounded-none md:border-0 md:border-r md:bg-transparent md:p-4 md:shadow-none md:backdrop-blur-none"
    >
      <span class="mb-4 hidden items-center gap-2 px-2 text-xl font-light tracking-tight md:flex">
        <span class="rayures inline-block size-3 rounded-sm" aria-hidden="true"></span>Bac à sable
      </span>
      {#each onglets as o}
        {@const Icone = o.icone}
        <a
          href={'#/' + o.page}
          aria-label={o.nom}
          aria-current={page === o.page ? 'page' : undefined}
          class="flex h-11 items-center gap-2 rounded-full px-3.5 text-sm font-medium text-muted-foreground transition-colors
                 hover:text-foreground aria-[current=page]:bg-foreground aria-[current=page]:text-background
                 md:h-10 md:rounded-lg md:px-3 md:aria-[current=page]:bg-secondary md:aria-[current=page]:text-foreground"
        >
          <Icone class="size-[1.15rem]" aria-hidden="true" />
          <span class="sr-only md:not-sr-only">{o.nom}</span>
        </a>
      {/each}
    </nav>

    <main
      class="mx-auto max-w-6xl px-[max(1rem,env(safe-area-inset-left))] pt-[calc(1.25rem+env(safe-area-inset-top))] pb-[calc(6rem+env(safe-area-inset-bottom))] md:px-8 md:pt-8 md:pb-10"
    >
      {#key page}
        <div in:fly={{ y: 6, duration: 180 }}>
          {#if page === 'soiree'}
            <Soiree />
          {:else if page === 'personnes'}
            <Personnes />
          {:else if page === 'scenarios'}
            <Scenarios />
          {:else if page === 'journal'}
            <Journal />
          {:else if page === 'connexion'}
            <!-- vrais liens du Bac à sable, en lecture seule (aucun geste qui écrit) -->
            <Services lectureSeule={true} ondeconnecte={() => (connecte = false)} />
          {:else if page === 'reglages'}
            <Reglages {session} {deconnecter} />
          {:else}
            <Applis />
          {/if}
        </div>
      {/key}
    </main>
  </div>
{/if}
