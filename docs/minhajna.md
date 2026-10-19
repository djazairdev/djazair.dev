# Minhajna's teacher download page

The new routes are `/ar/minhajna/` and `/en/minhajna/`. The page explains the
published Android preview in everyday language. The installer stays on the
Minhajna GitHub release; the site does not mirror or rebuild it.

## Review locally

```sh
python3 site/build.py --all-languages
python3 -m http.server 4328 --bind 127.0.0.1 --directory site/dist
```

Open `http://localhost:4328/ar/minhajna/` and its English counterpart. This is a
local review build, **never a deployment build**. Check the phone layout, keyboard
navigation, text spacing, 200% zoom and the optional technical-details disclosure.
Test the exercise against the actual tagged app, not a newer development build.

The normal production build honours `PUBLISHED = ('en',)` and the
[Arabic review gate](arabic-review.md). Amine Yagoub approved this Arabic page on
19 October 2026. Its scoped review in `content/page-reviews.json` enables only
`/ar/minhajna/`, not the rest of the Arabic site. Changing reviewed copy requires
fresh approval. Never deploy an all-languages build or mark the whole site reviewed.
Submit the tested changes through a pull request; after maintainer review and merge
to `main`, CI builds and deploys them as described in [deploy.md](deploy.md).
Check both live routes before inviting teachers. The repository guides remain a fallback.

On the download page, the top banner explains that Minhajna is an independent
project, not an official app adopted by the Algerian state or the Ministry of
National Education. This replaces the generic draft-language notice on this
page only, in both languages. It does not mark Arabic reviewed or bypass the
publication gate; unreviewed pages keep their existing invitation to translate.

## Release updates

`content/minhajna-release.json` is a manually checked snapshot of
[app-v0.1.0](https://github.com/djazairdev/minhajna/releases/tag/app-v0.1.0).
It contains the version, publication date, minimum Android version, universal APK
byte count, file SHA-256 and signing-certificate SHA-256. The renderer validates
them and constructs download URLs on the fixed project repository. Nothing is
fetched at build time or when a teacher reads the page.

Before changing it, check the signed release assets, checksum list and supported
devices. Review **all** capability, limitation, installation, privacy and exercise
copy against that release. A metadata update alone must not advertise unreleased
features. Update `tests/test_minhajna.py`'s independent release expectations too.

The teacher-facing update section explains manual installation over the existing
app, never uninstalling or clearing storage, and asking for help if Android refuses
the update. It does not promise backups, recovery or automatic update checks.
Keep that guidance aligned with the app project's release and upgrade checks.

All interface copy lives under `minhajna` and `pages.minhajna` in both catalogues.
Keep the meaning aligned, with natural Arabic rather than a word-for-word copy.
The introduction describes an integrated digital education system being built in
stages: daily journals, lesson logs and attendance registers first, then wider
educational and administrative work. This is the project's vision, not a claim
that the preview already covers the education system or has Ministry approval.
Keep the available and not-ready lists tied to the published release.

Use familiar Algerian school terms and concrete tasks: entering a weekly timetable,
recording lessons taught, roll call and following completed lessons by class.
Distinguish a class from its subgroups, a school stage from a grade, and the
academic year from either. Explain plans without software terms such as “packs”.
When quoting a control in a published release, keep its exact label and explain
the task alongside it; do not invent a new label that teachers cannot find.

Keep one download card with requirements, buttons and “Free download”. The same
card sits beside the introduction on wide screens and below it on phones.
Do not add file-format, processor or account explanations there. Teacher instructions stay
short; technical verification and legal credits are closed disclosures. Retain
the demo-data restriction, official-record warning, safe installation guidance,
no-uninstall update warning and lack of backup/recovery. Provider and architecture
details belong in the linked policy or maintainer documentation, not the pitch.
The header and download card reuse Minhajna's original icon and outlined Arabic
wordmark. The three gallery images come from the signed 0.1.0 installer, not the
design mockups or a newer development build. They show only the built-in demo
class. Images have dimensions and alternative text, load lazily and link to the
full-size capture without JavaScript. Nothing cycles or moves automatically.
On phones, the gallery scrolls sideways; keyboard focus brings each image into view.
Keep screenshots tied to the pinned release when updating the installer.

Asset sources, capture details and separate licences are in
`site/static/minhajna/README.md`. The page's newly written text is CC BY 4.0;
Minhajna's imported artwork remains CC BY-SA 4.0, its app UI AGPL-3.0-or-later,
and its name and logo subject to its trademark policy. No app code is imported.

The Android buttons inline the official robot SVG with its original colours and
geometry. Its separate CC BY 3.0 attribution and source are recorded in
`site/static/brand/README.md`, and the page footer carries the credit. Check Google's
brand-review requirements before publication. No asset is loaded from Google at
runtime. The iOS coming-soon controls are native disabled buttons with a generic
phone icon, not a standalone Apple logo or App Store badge; they have no URL,
click handler, release date or signup form. No iPhone build is available yet.

## Feedback and privacy

The maintainer selected these channels, in this order:

1. [Facebook page messages](https://www.facebook.com/djazairdev).
2. Email: `contact@djazair.dev`.
3. [GitHub reports](https://github.com/djazairdev/minhajna/issues/new?template=bug.yml), optional and public.

They are plain external links, not integrations. There is no form, embedded social
widget, tracking script, action counter, or automatic app report on this route,
even if those site options are enabled elsewhere. The static language switch and
technical details work without JavaScript. The host and external providers still
handle their own connection data; do not promise an absence of server logs.

Use invented data only, even in private messages. Security reports go privately by
email or through the app project's security policy, not Facebook comments or
public issues. Do not collect reports during automated checks. Mail hosting,
support access and retention must satisfy the app project's existing privacy
requirements before the maintainer invites teachers; this page adds no backend
or claim that those operational checks have been completed.

## Search and sharing

Search titles name the Android download and teachers in Algeria. Each language
uses its own 1200×630 Minhajna sharing card, generated with
`python3 site/tools/share.py --minhajna`. Keep the card and its text aligned with
the approved page. Canonical links, reciprocal language alternates and the sitemap
include only reviewed versions; other Arabic pages remain out of search.

Run `python3 -m unittest discover -s tests` and a normal production build before
submitting. Page approval does not authorise teacher outreach or a change to
either project's governance or privacy commitments. Use the repository's CI
deployment after merge, not a manual upload of this uncommitted checkout.
