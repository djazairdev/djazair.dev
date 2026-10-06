"""Chart colours for downloaded SVG and PNG files, where the page's CSS variables don't exist.

``DARK`` mirrors ``static/css/00-tokens.css`` (a test keeps them in step). ``LIGHT`` is the
light download palette from the Foundations board: on-screen charts are always dark.
"""
from __future__ import annotations

DARK = {
    'paper': '#0E1A15',
    'ink': '#EEF3EC',
    'ink2': '#B4C2B9',
    'ink3': '#879890',
    'line': 'rgba(238,243,236,.08)',
    'line2': 'rgba(238,243,236,.14)',
    'algeria': '#3DBE84',
    'algeria_fill': 'rgba(61,190,132,.10)',
    'highlight': '#E8A75A',
    'median': '#A9B8AF',
    'peer': '#6B7D74',
    'negative': '#F08A74',
    'cell_old': '#2C7255',
}

LIGHT = {
    'paper': '#FFFFFF',
    'ink': '#0E1A15',
    'ink2': '#3E4D45',
    'ink3': '#5B6B63',
    'line': 'rgba(14,26,21,.10)',
    'line2': 'rgba(14,26,21,.18)',
    'algeria': '#13804F',
    'algeria_fill': 'rgba(19,128,79,.10)',
    'highlight': '#B5651D',
    'median': '#6B7D74',
    'peer': '#84938B',
    'negative': '#C9533B',
    'cell_old': '#A8D5BF',
}

THEMES = {'dark': DARK, 'light': LIGHT}

# Which CSS custom property each DARK colour comes from.
CSS_SOURCE = {
    'paper': '--bg', 'ink': '--ink', 'ink2': '--ink2', 'ink3': '--ink3', 'line': '--line', 'line2': '--line2',
    'algeria': '--mint', 'highlight': '--amber', 'median': '--grey-hi', 'peer': '--grey',
    'negative': '--coral', 'cell_old': '--cell-old',
}
