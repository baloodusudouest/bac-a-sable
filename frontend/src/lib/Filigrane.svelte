<script>
  // Filigrane du Bac à sable (0.1.2) : « BAC À SABLE » en diagonale sur tout l'écran, pour reconnaître une capture
  // d'écran. Même dessin que app/filigrane.py (filigrane des applis simulées) : garder les deux pareils.
  let { sousTitre = 'Bac à sable — simulation' } = $props()
  const echapper = (t) => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const svg = $derived(
    '<svg xmlns="http://www.w3.org/2000/svg" width="340" height="210" viewBox="0 0 340 210">' +
      '<g transform="rotate(-24 170 105)" font-family="Inter,system-ui,sans-serif" text-anchor="middle" ' +
      'fill="#5cc6d6" fill-opacity="0.13">' +
      '<text x="170" y="104" font-size="26" font-weight="700" letter-spacing="3">BAC À SABLE</text>' +
      `<text x="170" y="128" font-size="13" font-weight="500">${echapper(sousTitre)}</text>` +
      '</g></svg>'
  )
  const url = $derived('data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg))
</script>

<div id="bac-a-sable-filigrane" aria-hidden="true"
     class="pointer-events-none fixed inset-0 z-[60] bg-repeat"
     style={`background-image:url("${url}")`}></div>
