"""Every page of the site, in both languages: /<lang>/<path>."""
from __future__ import annotations

from .context import Route
from .pages import about, datapage, home, hub, languages, methodology, notfound, overview, peers, report, topics, trends
from .reports import all_reports

ROUTES = [
    Route('home', '', home.render, ticket=18),
    Route('overview', 'index/', overview.render, section='index', sub='overview', ticket=19),
    Route('peers', 'index/peers/', peers.render, section='index', sub='peers', ticket=21),
    Route('trends', 'index/trends/', trends.render, section='index', sub='trends', ticket=20),
    Route('languages', 'index/languages/', languages.render, section='index', sub='languages', ticket=22),
    Route('topics', 'index/topics/', topics.render, section='index', sub='topics', ticket=36),
    Route('hub', 'hub/', hub.render, section='hub'),
    Route('reports', 'reports/', report.render_index, section='reports', ticket=34),
    *(Route(r.key, r.path, report.render, section='reports', ticket=34) for r in all_reports()),
    Route('methodology', 'methodology/', methodology.render, section='methodology', ticket=23),
    Route('data', 'data/', datapage.render, section='data', ticket=24, last=True),
    Route('about', 'about/', about.render, ticket=23),
    Route('notfound', '404.html', notfound.render, switchable=False, indexed=False),
]
