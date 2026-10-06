"""Write ``site/geo/algeria.json``: Algeria's outline, projected and simplified, for the unit map.

Source: Natural Earth 1:10m admin-0 countries (public domain), as the TopoJSON
``countries-10m.json`` from the world-atlas package (Algeria is id ``012``). Only needed
if the outline should change:

    python3 site/tools/make_outline.py path/to/countries-10m.json

The projection is Lambert conformal conic (standard parallels 24° and 34° N, origin
28° N 1.7° E), which keeps Algeria's familiar shape. Coordinates are scaled so the
longer side is 1,000 units, with y pointing down as in SVG.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'geo' / 'algeria.json'
ALGIERS = (3.06, 36.75)        # lon, lat
TOLERANCE = 0.5                # Douglas-Peucker tolerance, in output units

PHI1, PHI2, PHI0, LAM0 = map(math.radians, (24, 34, 28, 1.7))
N = math.log(math.cos(PHI1) / math.cos(PHI2)) / math.log(math.tan(math.pi / 4 + PHI2 / 2) / math.tan(math.pi / 4 + PHI1 / 2))
F = math.cos(PHI1) * math.tan(math.pi / 4 + PHI1 / 2) ** N / N
RHO0 = F / math.tan(math.pi / 4 + PHI0 / 2) ** N


def project(lon: float, lat: float) -> tuple:
    rho = F / math.tan(math.pi / 4 + math.radians(lat) / 2) ** N
    theta = N * (math.radians(lon) - LAM0)
    return rho * math.sin(theta), RHO0 - rho * math.cos(theta)


def ring(topo: dict, code: str = '012') -> list:
    """The country's outer ring in lon/lat, decoded from quantised TopoJSON arcs."""
    (sx, sy), (tx, ty) = topo['transform']['scale'], topo['transform']['translate']
    geom = next(g for g in topo['objects']['countries']['geometries'] if g.get('id') == code)
    arcs = geom['arcs'][0] if geom['type'] == 'Polygon' else max(geom['arcs'], key=lambda p: len(p[0]))[0]

    def arc(i):
        x = y = 0
        pts = []
        for dx, dy in topo['arcs'][i if i >= 0 else ~i]:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        return pts[::-1] if i < 0 else pts

    out = []
    for i in arcs:
        a = arc(i)
        out += a if not out else a[1:]
    return out


def simplify(pts: list, eps: float) -> list:
    """Douglas-Peucker on an open polyline (iterative)."""
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
            px, py = pts[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / length
            if d > dmax:
                far, dmax = i, d
        if dmax > eps:
            keep[far] = True
            stack += [(a, far), (far, b)]
    return [p for p, k in zip(pts, keep) if k]


def closed_simplify(pts: list, eps: float) -> list:
    """Simplify a closed ring by splitting it at the point farthest from the start."""
    if pts[0] == pts[-1]:
        pts = pts[:-1]
    k = max(range(len(pts)), key=lambda i: math.hypot(pts[i][0] - pts[0][0], pts[i][1] - pts[0][1]))
    return simplify(pts[:k + 1], eps)[:-1] + simplify(pts[k:] + [pts[0]], eps)[:-1]


def main(argv: list) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    topo = json.loads(Path(argv[1]).read_text('utf-8'))
    projected = [project(lon, lat) for lon, lat in ring(topo)]
    x0 = min(p[0] for p in projected)
    x1 = max(p[0] for p in projected)
    y0 = min(p[1] for p in projected)
    y1 = max(p[1] for p in projected)
    scale = 1000 / max(x1 - x0, y1 - y0)

    def fit(x, y):
        return (x - x0) * scale, (y1 - y) * scale     # y down

    outline = closed_simplify([fit(x, y) for x, y in projected], TOLERANCE)
    data = {
        'source': 'Natural Earth 1:10m admin-0 countries (public domain), via world-atlas countries-10m.json',
        'projection': 'Lambert conformal conic, standard parallels 24 and 34 N, origin 28 N 1.7 E',
        'width': round((x1 - x0) * scale, 2),
        'height': round((y1 - y0) * scale, 2),
        'algiers': [round(v, 2) for v in fit(*project(*ALGIERS))],
        'outline': [[round(x, 2), round(y, 2)] for x, y in outline],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(',', ':')) + '\n', 'utf-8')
    print(f'{OUT}: {len(outline)} points from {len(projected)}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
