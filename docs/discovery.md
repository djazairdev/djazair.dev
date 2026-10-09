# Search, AI readers and security discovery

`python3 site/build.py` generates these files from the public route catalogue and current release:

- `sitemap.xml` and `sitemap.txt`: the same canonical, indexed English and Arabic pages. Embeds, removed routes and error pages are excluded.
- `robots.txt`: allows crawling and points to the XML sitemap. Cloudflare preview URLs retain their `X-Robots-Tag: noindex`; launch checks must use the production custom domain.
- `llms.txt`: project purpose, canonical links, source files, participation paths and data limitations. `/en/data/index.md` and `/ar/data/index.md` provide the existing definitions and download descriptions in native Markdown. This follows the [llms.txt proposal](https://llmstxt.org/); it does not guarantee AI indexing or ranking.
- `/.well-known/security.txt`, with a root copy for older clients: the private disclosure channels already documented in `SECURITY.md`, following [RFC 9116](https://www.rfc-editor.org/rfc/rfc9116.html). **Verify the contacts and renew `SECURITY_EXPIRES` in `site/djsite/discovery.py` before 1 October 2027.** The regression test fails once it expires.

Indexed HTML pages include Organization, WebSite and WebPage JSON-LD. The Data page adds a DataCatalog and fourteen Dataset entries, with actual CSV/JSON DataDownload URLs, byte sizes, descriptions and provenance. Dataset IDs stay the same across languages. Quarterly measurements retain CC0, population sources retain their own CC BY 4.0 licence, and the separately published Octoverse forecast is not labelled CC0. Metadata comes from the manifest and visible Data-page descriptions, in accordance with [Google's Dataset guidance](https://developers.google.com/search/docs/appearance/structured-data/dataset).

Cloudflare headers revalidate HTML and discovery documents, preserve immutable asset caching, enable HTTPS transport security, restrict framing of ordinary pages, and prohibit object embeds and external base URLs. Public chart embeds retain their explicit framing exception. See the [Cloudflare static-assets header rules](https://developers.cloudflare.com/workers/static-assets/headers/).

Founders.coffee links are ordinary editorial HTML anchors. They carry no `nofollow`, `ugc` or `sponsored` qualifier, so no nonstandard `rel="dofollow"` value is necessary. Tests check both languages on Home and Meetups.

Page styles include shared components and only the route's own rules. CSS compaction preserves strings, descendant selectors and arithmetic spacing. The map caches its bounds until scrolling or resizing, reads replay counters only for the cube shader, reuses its ripple buffer, and initializes the renderer when first visible on mobile. It renders at up to 30 frames per second, with a smaller pixel buffer on touch devices, and adapts resolution and cadence when rendering takes too long. Its particle entrance still runs once, and the numbers and cubes keep looping until paused.

PageSpeed is a variable lab measurement, not a production-readiness certificate. Recheck mobile and desktop after changes and on the final production domain; do not remove preview indexing protection to raise its SEO score.
