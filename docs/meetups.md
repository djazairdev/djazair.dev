# Meetups

The meetups section, [`/en/meetups/`](https://djazair.dev/en/meetups/) and [`/ar/meetups/`](https://djazair.dev/ar/meetups/) (ticket [#43](https://github.com/djazairdev/djazair.dev/issues/43), PRD D11).

## What the page does

- It says what a meetup is: a small group in a real café, around a subject the host described, with no slides and no pitches, and free. It also says how to host one.
- It sends readers to founders.coffee, where the meetups are organised, to find a meetup in Algeria or host one. Links open founders.coffee in the page's language.
- It copies no meetups, dates, places or names from founders.coffee, so it can't go out of date. founders.coffee keeps the accounts, the RSVPs and the hosts.
- It says founders.coffee is a separate site, with its own accounts, terms and privacy policy, and that djazair.dev shares nothing with it.

Home also invites developers to find local teammates through founders.coffee, after Project Hub. Its four-piece skill illustration assembles with scroll; reduced motion and no JavaScript show the completed illustration. The meetup and hosting buttons reuse the configured platform paths below, in the page's language. No live events, member profiles or city availability claims are copied into Home.

The meetups page is linked from the footer (Hub column) and listed in the sitemap, but it isn't in the main navigation yet.

Where it links lives in [`content/meetups/meetups.json`](../content/meetups/meetups.json): the founders.coffee address and four paths, each with `{lang}`. The weekly *Link check* ([deploy.md](deploy.md#link-check)) opens every one of them in both languages. It opens an issue if one stops answering or no longer looks like a Founders Coffee page.

## The move from founders.coffee: a decision for the founder

The PRD (D11) plans that founders.coffee becomes this section and its domain redirects to `djazair.dev/{lang}/meetups`.

founders.coffee has since grown into an app of its own. As of October 2026 it has:

- accounts (email codes, Google and GitHub sign-in);
- RSVPs, live attendance and city waitlists;
- an installable app;
- three active markets: Algeria, Egypt and Saudi Arabia.

Redirecting the whole domain would switch all of that off, Egypt and Saudi Arabia included. djazair.dev is static, with no accounts and no database, so it has nowhere to keep any of it.

So the redirect isn't set up, and #43 stays open until you choose:

1. **Link, and keep both** (what is built). founders.coffee stays the meetups app, and djazair.dev has this page and links there. founders.coffee could link back to djazair.dev from its Algeria pages; that change belongs in its own repository.
2. **The full move, as the PRD says.** First decide what happens to members' accounts and RSVPs and to the Egypt and Saudi Arabia markets. Then tell members, as founders.coffee's terms and privacy policy require. Only then add the redirect below.

### The redirect, for option 2

In Cloudflare, open the founders.coffee zone, then *Rules → Redirect Rules*. Add two single redirects, in this order, both 301, without the query string:

| Order | When incoming requests match | Then redirect to |
| --- | --- | --- |
| 1 | Hostname equals `founders.coffee` and URI Path starts with `/en` | `https://djazair.dev/en/meetups/` |
| 2 | Hostname equals `founders.coffee` | `https://djazair.dev/ar/meetups/` |

The second rule catches the rest: founders.coffee's default is Arabic. It also takes the French pages, since djazair.dev has no French (D20). Add the same rules for `www.founders.coffee` if that name is in use.

After the change:

1. Open `https://founders.coffee/`, `https://founders.coffee/en/algeria` and `https://founders.coffee/ar/algeria`. They should land on the matching meetups page.
2. Change this page and `content/meetups/meetups.json`, which still link to founders.coffee.
