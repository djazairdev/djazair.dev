"""Every page of the site, in both languages: /<lang>/<path>."""
from __future__ import annotations

from .context import Route
from .pages import (about, collaboration, datapage, home, hub, languages, localisation, meetups, notfound, overview, peers,
                    rankings, topics, trends)

ROUTES = [
    Route('home', '', home.render, ticket=18),
    Route('overview', 'index/', overview.render, section='index', sub='overview', ticket=19),
    Route('peers', 'index/peers/', peers.render, section='index', sub='peers', ticket=21),
    Route('trends', 'index/trends/', trends.render, section='index', sub='trends', ticket=20),
    Route('languages', 'index/languages/', languages.render, section='index', sub='languages', ticket=22),
    Route('topics', 'index/topics/', topics.render, section='index', sub='topics', ticket=36),
    Route('collaboration', 'index/collaboration/', collaboration.render, section='index', sub='collaboration', ticket=37),
    Route('rankings', 'index/rankings/', rankings.render, section='index', sub='rankings', ticket=38),
    Route('hub', 'hub/', hub.render, section='hub'),
    Route('localisation', 'hub/localisation/', localisation.render, section='hub', ticket=40),
    Route('meetups', 'meetups/', meetups.render, ticket=43),
    Route('data', 'data/', datapage.render, section='data', ticket=24, last=True),
    Route('about', 'about/', about.render, ticket=23),
    Route('notfound', '404.html', notfound.render, switchable=False, indexed=False),
]
