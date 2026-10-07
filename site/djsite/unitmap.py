"""Unit map layout: Algeria's outline filled with one square per 1,000 developer accounts.

Squares show quantity, never location: the grid fills the outline evenly, and the
squares added in the last year are scattered with a fixed hash, so the same numbers
always give the same picture. For a replay of the years, the squares each earlier year
added follow in the same hashed order. The outline comes from ``site/geo/algeria.json``
(see ``tools/make_outline.py``).
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from functools import lru_cache

from .config import SITE_DIR

GEO = SITE_DIR / 'geo' / 'algeria.json'


@lru_cache(maxsize=1)
def outline() -> dict:
    return json.loads(GEO.read_text('utf-8'))


def inside(px: float, py: float, poly) -> bool:
    """Even-odd point-in-polygon test."""
    hit = False
    j = len(poly) - 1
    for i in range(len(poly)):
        (xi, yi), (xj, yj) = poly[i], poly[j]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def _seg_dist(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy or 1e-12
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _simplify(pts, eps):
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (ax, ay), (bx, by) = pts[a], pts[b]
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy) or 1e-12
        far, dmax = -1, 0.0
        for i in range(a + 1, b):
            d = abs(dy * pts[i][0] - dx * pts[i][1] + bx * ay - by * ax) / length
            if d > dmax:
                far, dmax = i, d
        if dmax > eps:
            keep[far] = True
            stack += [(a, far), (far, b)]
    return [p for p, k in zip(pts, keep) if k]


def outline_path(poly, eps: float) -> str:
    """SVG path data for the closed outline, simplified to ``eps``."""
    k = max(range(len(poly)), key=lambda i: math.hypot(poly[i][0] - poly[0][0], poly[i][1] - poly[0][1]))
    pts = _simplify(poly[:k + 1], eps)[:-1] + _simplify(poly[k:] + [poly[0]], eps)[:-1]
    return 'M' + ' '.join(f'{x:.1f} {y:.1f}' for x, y in pts) + 'Z'


@dataclass(frozen=True)
class Cell:
    x: float
    y: float
    new: bool
    t: float          # distance from Algiers, 0 to 1 (the order cells appear in)
    step: int = 0     # with a history, the first step the square is in


@dataclass(frozen=True)
class Layout:
    width: float
    height: float
    pitch: float
    cells: tuple
    outline: str

    @property
    def total(self) -> int:
        return len(self.cells)

    @property
    def added(self) -> int:
        return sum(c.new for c in self.cells)


def _rank(seed: str, i: int) -> str:
    return hashlib.sha256(f'{seed}:{i}'.encode()).hexdigest()


@lru_cache(maxsize=32)
def layout(total: int, new: int, box: float = 600.0, seed: str = 'djazair.dev', history: tuple = ()) -> Layout:
    """``total`` squares inside the outline, ``new`` of them marked as added in the last year.

    The grid pitch is the largest that still fits ``total`` squares; extra squares nearest
    the coast and borders are dropped so the count is exact.

    ``history``: the number of squares at each step of a replay, oldest first, ending with
    ``total`` after ``total - new``. Each square gets the first step it is in: the ``new``
    squares make the last step, and each earlier step takes the next squares in the same
    hashed order, so every step holds the one before it."""
    if not 0 <= new <= total:
        raise ValueError(f'new ({new}) must be between 0 and total ({total})')
    if history and (history[-1] != total or list(history) != sorted(history)
                    or (len(history) > 1 and history[-2] != total - new)):
        raise ValueError(f'history {history} must rise to {total}, from {total - new} the step before')
    geo = outline()
    s = box / 1000
    poly = [(x * s, y * s) for x, y in geo['outline']]
    w, h = geo['width'] * s, geo['height'] * s

    def grid(p):
        cols, rows = math.ceil(w / p), math.ceil(h / p)
        ox, oy = -(cols * p - w) / 2, -(rows * p - h) / 2
        return [(ox + c * p, oy + r * p) for r in range(rows) for c in range(cols)
                if inside(ox + c * p + p / 2, oy + r * p + p / 2, poly)]

    area = abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]))) / 2
    lo, hi = 0.5 * math.sqrt(area / max(total, 1)), 1.5 * math.sqrt(area / max(total, 1))
    if len(grid(lo)) < total:
        raise ValueError(f'{total} squares do not fit in the outline')
    for _ in range(24):                      # largest pitch with at least ``total`` cells
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if len(grid(mid)) >= total else (lo, mid)
    p = lo
    cells = grid(p)
    if len(cells) > total:
        def edge(c):
            cx, cy = c[0] + p / 2, c[1] + p / 2
            return min(_seg_dist(cx, cy, *poly[i], *poly[(i + 1) % len(poly)]) for i in range(len(poly)))
        drop = set(sorted(range(len(cells)), key=lambda i: (edge(cells[i]), cells[i][1], cells[i][0]))[:len(cells) - total])
        cells = [c for i, c in enumerate(cells) if i not in drop]

    order = sorted(range(total), key=lambda i: _rank(seed, i))
    fresh = set(order[:new])
    step = [0] * total
    for k in range(len(history) - 1, 0, -1):
        for i in order[total - history[k]:total - history[k - 1]]:
            step[i] = k
    ax, ay = geo['algiers'][0] * s, geo['algiers'][1] * s
    dist = [math.hypot(c[0] + p / 2 - ax, c[1] + p / 2 - ay) for c in cells]
    far = max(dist) or 1
    out = tuple(Cell(round(c[0], 2), round(c[1], 2), i in fresh, round(dist[i] / far, 4), step[i]) for i, c in enumerate(cells))
    return Layout(width=round(w, 2), height=round(h, 2), pitch=round(p, 4), cells=out, outline=outline_path(poly, box / 1000))
