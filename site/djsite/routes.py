"""Every page of the site, in both languages: /<lang>/<path>."""
from __future__ import annotations

from .context import Route
from .pages import notfound, stub

ROUTES = [
    Route('home', '', stub.render, ticket=18),
    Route('overview', 'index/', stub.render, section='index', sub='overview', ticket=19),
    Route('peers', 'index/peers/', stub.render, section='index', sub='peers', ticket=21),
    Route('trends', 'index/trends/', stub.render, section='index', sub='trends', ticket=20),
    Route('languages', 'index/languages/', stub.render, section='index', sub='languages', ticket=22),
    Route('hub', 'hub/', stub.render, section='hub', ticket=27),
    Route('reports', 'reports/', stub.render, section='reports', ticket=34),
    Route('report-2026-q1', 'reports/2026-q1/', stub.render, section='reports', ticket=34),
    Route('methodology', 'methodology/', stub.render, section='methodology', ticket=23),
    Route('data', 'data/', stub.render, section='data', ticket=24),
    Route('about', 'about/', stub.render, ticket=23),
    Route('notfound', '404.html', notfound.render, switchable=False, indexed=False),
]
