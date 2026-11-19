"""Filigrane du Bac à sable (0.1.2) : « BAC À SABLE » en diagonale, répété sur tout l'écran, avec le nom et la version
de l'appli. Une capture d'écran d'une appli simulée se reconnaît ainsi au premier coup d'œil (et par Claude).

Le même dessin est fait côté interface du Bac à sable (frontend/src/lib/Filigrane.svelte) : garder les deux pareils.
Il ne bloque aucun clic (pointer-events: none) et reste discret (cyan du Bac à sable, peu opaque).
"""
from __future__ import annotations

from html import escape
from urllib.parse import quote


def motif(sous_titre: str) -> str:
    """Le carreau SVG du filigrane, en adresse data: (répété par le navigateur)."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="340" height="210" viewBox="0 0 340 210">'
        '<g transform="rotate(-24 170 105)" font-family="Inter,system-ui,sans-serif" text-anchor="middle" '
        'fill="#5cc6d6" fill-opacity="0.13">'
        '<text x="170" y="104" font-size="26" font-weight="700" letter-spacing="3">BAC À SABLE</text>'
        f'<text x="170" y="128" font-size="13" font-weight="500">{escape(sous_titre)}</text>'
        '</g></svg>')
    return "data:image/svg+xml;charset=utf-8," + quote(svg)


def html(nom: str, version: str) -> str:
    """Le calque du filigrane, à placer en fin de <body>."""
    return ('<div id="bac-a-sable-filigrane" aria-hidden="true" style="position:fixed;inset:0;z-index:2147483646;'
            'pointer-events:none;background-repeat:repeat;'
            f"background-image:url(&quot;{motif(f'{nom} {version} — simulation')}&quot;)\"></div>")
