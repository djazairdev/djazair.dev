"""Build-time SVG charts. On-page charts take their colours from CSS classes (so the tokens
apply); downloadable files get explicit colours from ``palette``.

Time always runs left to right, in Arabic too, and maps are never mirrored.
"""
from __future__ import annotations

from typing import Callable, Iterable, Optional

from .markup import Markup, esc


def _path(points) -> str:
    return 'M' + ' L'.join(f'{x:.2f} {y:.2f}' for x, y in points)


# ---------------------------------------------------------------- sparkline
def spark(values: list, median: Optional[list] = None, w: int = 100, h: int = 34) -> Markup:
    """A sparkline that stretches to its box while strokes keep their width (decorative:
    the tile around it states the value, and the page's tables hold the series)."""
    vals = [v for v in values if v is not None] + [v for v in (median or []) if v is not None]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.12 or 1
    lo, hi = lo - pad, hi + pad
    n = len(values)
    X = lambda i: i * w / (n - 1)
    Y = lambda v: h - (v - lo) / (hi - lo) * h
    pts = lambda vs: [(X(i), Y(v)) for i, v in enumerate(vs) if v is not None]
    out = []
    if median:
        out.append(f'<path class="sp-md" d="{_path(pts(median))}" vector-effect="non-scaling-stroke"/>')
    line = pts(values)
    out.append(f'<path class="sp-area" d="{_path(line)} L{w} {h} L0 {h} Z"/>')
    out.append(f'<path class="sp-ln" d="{_path(line)}" vector-effect="non-scaling-stroke"/>')
    lx, ly = line[-1]
    out.append(f'<path class="sp-end" d="M{lx:.2f} {ly:.2f} l0 0" vector-effect="non-scaling-stroke"/>')
    return Markup(f'<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true" '
                  f'focusable="false">{"".join(out)}</svg>')


# ---------------------------------------------------------------- rank strip
def rank_strip(rank: int, of: int, label: str, full: int = 29) -> Markup:
    """One cell per economy, Algeria's rank lit. Every strip uses the same 29-cell scale,
    so a rank of 7 and a rank of 29 compare at a glance. Mirrored in Arabic (rank 1 first)."""
    s, g = 8, 3
    width = full * (s + g) - g
    lit = ' class="on"'
    cells = ''.join(f'<rect x="{i * (s + g)}" width="{s}" height="{s}" rx="1.8"{lit if i + 1 == rank else ""}/>'
                    for i in range(of))
    return Markup(f'<svg class="rank-strip" viewBox="0 0 {width} {s}" role="img" aria-label="{esc(label)}">{cells}</svg>')


# ---------------------------------------------------------------- tiny horizontal bars
def hbars(items: Iterable, fmt: Callable, names: dict, highlight: str = 'DZ') -> Markup:
    """Peer comparison inside a tile, as HTML so labels stay crisp. ``items``: [(code, value)]."""
    items = list(items)
    top = max(v for _, v in items) or 1
    rows = []
    for code, v in items:
        on = ' class="on"' if code == highlight else ''
        rows.append(f'<div{on}><span class="hb-name">{esc(names.get(code, code))}</span>'
                    f'<span class="hb-track"><span class="hb-bar" style="inline-size: {v / top * 100:.1f}%"></span></span>'
                    f'<span class="hb-val num" dir="ltr">{esc(fmt(v))}</span></div>')
    return Markup(f'<div class="hbars">{"".join(rows)}</div>')
