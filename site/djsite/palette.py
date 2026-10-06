"""Chart colours. On-page charts are always dark and use ``DARK``, which mirrors
``static/css/00-tokens.css`` (a test keeps them in step). Downloaded SVG and PNG files
come in both themes; ``LIGHT`` is the light download palette from the Components board.
"""
from __future__ import annotations

DARK = {
    'paper': '#0E1A15',
    'ink': '#EEF3EC',
    'ink2': '#B4C2B9',
    'ink3': '#879890',
    'line': 'rgba(238,243,236,.08)',
    'line2': 'rgba(238,243,236,.14)',
    'grid': 'rgba(238,243,236,.07)',
    'axis': 'rgba(238,243,236,.16)',
    'tick': 'rgba(238,243,236,.3)',
    'algeria': '#3DBE84',
    'algeria_fill': 'rgba(61,190,132,.10)',
    'highlight': '#E8A75A',
    'median': '#A9B8AF',
    'peer': '#62736A',
    'peer_dim': '#3F4D46',
    'bar': 'rgba(238,243,236,.16)',
    'negative': '#F08A74',
    'cell_old': '#2C7255',
    'map_line': 'rgba(238,243,236,.22)',
    'map_fill': 'rgba(61,190,132,.035)',
}

LIGHT = {
    'paper': '#FFFFFF',
    'ink': '#0E1A15',
    'ink2': '#3E4D45',
    'ink3': '#5B6B63',
    'line': 'rgba(14,26,21,.10)',
    'line2': 'rgba(14,26,21,.18)',
    'grid': 'rgba(14,26,21,.08)',
    'axis': 'rgba(14,26,21,.22)',
    'tick': 'rgba(14,26,21,.35)',
    'algeria': '#13804F',
    'algeria_fill': 'rgba(19,128,79,.10)',
    'highlight': '#B5651D',
    'median': '#6B7D74',
    'peer': '#84938B',
    'peer_dim': '#C9D1CC',
    'bar': 'rgba(14,26,21,.13)',
    'negative': '#C9533B',
    'cell_old': '#A8D5BF',
    'map_line': 'rgba(14,26,21,.30)',
    'map_fill': 'rgba(19,128,79,.04)',
}

THEMES = {'dark': DARK, 'light': LIGHT}

# Which CSS custom property each DARK colour comes from.
CSS_SOURCE = {
    'paper': '--bg', 'ink': '--ink', 'ink2': '--ink2', 'ink3': '--ink3', 'line': '--line', 'line2': '--line2',
    'grid': '--grid-line', 'axis': '--axis-line', 'tick': '--tick-line',
    'algeria': '--mint', 'algeria_fill': '--mint-fill', 'highlight': '--amber', 'median': '--grey-hi',
    'peer': '--peer-line', 'peer_dim': '--peer-dim', 'bar': '--bar', 'negative': '--coral', 'cell_old': '--cell-old',
    'map_line': '--map-line', 'map_fill': '--map-fill',
}
