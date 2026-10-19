"""Minhajna's teacher preview, pinned to a verified public release, without page scripts."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from ..components import btn, eyebrow
from ..config import CONTENT_DIR
from ..context import Ctx, Page
from ..icons import android_mark, icon
from ..markup import Markup, esc, join

REPO = 'https://github.com/djazairdev/minhajna'
FACEBOOK = 'https://www.facebook.com/djazairdev'
EMAIL = 'mailto:contact@djazair.dev?subject=Minhajna%20feedback'
PRIVATE_EMAIL = 'mailto:contact@djazair.dev?subject=Minhajna%20private%20report'


def load_release(path: Path = CONTENT_DIR / 'minhajna-release.json') -> dict:
    """Validate the pinned release before constructing links on the fixed GitHub origin."""
    data = json.loads(path.read_text('utf-8'))
    if not isinstance(data, dict) or not re.fullmatch(r'\d+\.\d+\.\d+', str(data.get('version', ''))):
        raise ValueError('Minhajna release version must be numeric semver')
    for key in ('apk_bytes', 'minimum_android'):
        if type(data.get(key)) is not int or data[key] <= 0:
            raise ValueError(f'Minhajna {key} must be a positive integer')
    for key in ('apk_sha256', 'certificate_sha256'):
        if not re.fullmatch(r'[0-9a-f]{64}', str(data.get(key, ''))):
            raise ValueError(f'Minhajna {key} must be a SHA-256 digest')
    if not isinstance(data.get('published'), str):
        raise ValueError('Minhajna publication date must be an ISO date')
    date.fromisoformat(data['published'])
    return data


def header(ctx: Ctx, switch: Markup) -> Markup:
    """A teacher-focused header, without the developer contribution menu."""
    return Markup(f'''<header class="mh-header"><div class="container mh-header-row">
<a class="mh-brand" href="{ctx.url('minhajna')}" aria-label="{ctx.ta('minhajna.brand')}">{_brand(ctx)}</a>
<div class="mh-header-end"><a href="#feedback">{ctx.t('minhajna.feedback.link')}</a>{switch}</div>
</div></header>''')


def footer(ctx: Ctx) -> Markup:
    """Small source and policy links; no embeds or third-party widgets."""
    links = [('minhajna.footer.project', REPO), ('minhajna.footer.privacy', REPO + '/blob/main/PRIVACY.md'),
             ('minhajna.footer.site', ctx.url('home', lang=ctx.lang if ctx.lang in ctx.site.languages('home') else 'en'))]
    items = join(f'<a href="{esc(href)}">{ctx.t(label)}</a>' for label, href in links)
    licence = Markup(f'<a href="https://creativecommons.org/licenses/by/3.0/">{ctx.t("minhajna.footer.robot_licence")}</a>')
    art_credit = ctx.t('minhajna.footer.art_credit',
                       source=Markup(f'<a href="{REPO}">Minhajna</a>'),
                       licence=Markup('<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>'))
    return Markup(f'<footer class="mh-footer"><div class="container"><p>{ctx.t("minhajna.footer.note")}</p>'
                  f'<nav aria-label="{ctx.ta("minhajna.footer.links")}">{items}</nav>'
                  f'<details class="mh-credits"><summary>{ctx.t("minhajna.footer.credits")}</summary>'
                  f'<a href="https://github.com/djazairdev/djazair.dev/blob/main/LICENSE-content">'
                  f'{ctx.t("minhajna.footer.licence")}</a>'
                  f'<p class="mh-small">{art_credit}</p>'
                  f'<p class="mh-small">{ctx.t("minhajna.footer.android_credit", licence=licence)} '
                  f'{ctx.t("minhajna.footer.android_trademark")}</p></details></div></footer>')


def _brand(ctx: Ctx) -> Markup:
    """Keep the original Arabic artwork and lockup order in either page language."""
    assets = ctx.site.assets.minhajna
    return Markup(f'<span class="mh-lockup" dir="rtl">'
                  f'<img class="mh-app-icon" src="{assets["minhajna-icon.svg"]}" width="512" height="512" alt="">'
                  f'<img class="mh-wordmark" src="{assets["minhajna-wordmark-chalk.svg"]}" '
                  f'width="1979" height="971" alt=""></span>')


def _screenshots(ctx: Ctx, version: str) -> Markup:
    assets = ctx.site.assets.minhajna
    cards = join(f'<figure><a class="mh-screen-link" href="{assets[f"{name}-{version}.png"]}" '
                 f'aria-label="{ctx.ta("minhajna.screenshots.enlarge", screen=ctx.s(f"minhajna.screenshots.{name}.caption"))}">'
                 f'<img src="{assets[f"{name}-{version}-thumb.jpg"]}" width="270" height="600" '
                 f'loading="lazy" decoding="async" alt="{ctx.ta(f"minhajna.screenshots.{name}.alt")}"></a>'
                 f'<figcaption>{ctx.t(f"minhajna.screenshots.{name}.caption")}</figcaption></figure>'
                 for name in ('today', 'week', 'roll'))
    return _section(ctx, 'screenshots', f'<p class="mh-small">{ctx.t("minhajna.screenshots.note", version=version)}</p>'
                    f'<div class="mh-gallery">{cards}</div>')


def _download_actions(ctx: Ctx, href: str) -> Markup:
    label = Markup(f'{android_mark("download")}<span>{ctx.t("minhajna.download")}</span>')
    android = btn(label, href, arrow=False)
    ios = (f'<button class="btn btn-secondary mh-ios" type="button" disabled aria-disabled="true">'
           f'{icon("phone", 24, cls="icon ios-phone")}<span>{ctx.t("minhajna.ios_soon")}</span></button>')
    return Markup(f'<div class="mh-download-actions">{android}{ios}</div>')


def _list(ctx: Ctx, key: str, ordered: bool = False) -> Markup:
    tag = 'ol' if ordered else 'ul'
    return Markup(f'<{tag} class="mh-list">' + ''.join(f'<li>{item}</li>' for item in ctx.tl(key)) + f'</{tag}>')


def _section(ctx: Ctx, id_: str, inner: str) -> Markup:
    return Markup(f'<section class="mh-section" id="{id_}" aria-labelledby="{id_}-h">'
                  f'<h2 id="{id_}-h">{ctx.t(f"minhajna.{id_}.title")}</h2>{inner}</section>')


def render(ctx: Ctx) -> Page:
    data = load_release()
    version = data['version']
    release = f'{REPO}/releases/tag/app-v{version}'
    asset = f'{REPO}/releases/download/app-v{version}/'
    download = asset + f'minhajna-{version}.apk'
    facts = ctx.t('minhajna.release', version=Markup(f'<bdi>{version}</bdi>'),
                  date=Markup(f'<time datetime="{data["published"]}">{data["published"]}</time>'))
    hero = f'''<section class="mh-hero" aria-labelledby="mh-title"><div>
{eyebrow(ctx.t('minhajna.eyebrow'))}<h1 id="mh-title">{ctx.t('minhajna.title')}</h1>
<p class="mh-lede">{ctx.t('minhajna.lede')}</p>
<p class="mh-mission">{ctx.t('minhajna.mission')}</p>
<p class="mh-release">{facts}</p>
<p class="mh-caution">{ctx.t('minhajna.demo_only')}</p>
<a class="mh-text-link" href="#try">{ctx.t('minhajna.try.link')}{icon('arrow', 18)}</a></div>
<div class="mh-download"><div class="mh-download-name" role="img" aria-label="{ctx.ta('minhajna.brand')}">{_brand(ctx)}</div>
<p>{ctx.t('minhajna.compatibility', android=data['minimum_android'])}</p>
{_download_actions(ctx, download)}
<p class="mh-small">{ctx.t('minhajna.download_note')}</p>
<a href="#install">{ctx.t('minhajna.install.link')}</a>
<a href="#update">{ctx.t('minhajna.update.link')}</a>
</div></section>'''
    features = _section(ctx, 'features', _list(ctx, 'minhajna.features.items'))
    limits = _section(ctx, 'limits', _list(ctx, 'minhajna.limits.items'))
    install = _section(ctx, 'install', str(_list(ctx, 'minhajna.install.steps', True)) +
                       f'<p class="mh-caution">{ctx.t("minhajna.install.safety")}</p>')
    update = _section(ctx, 'update', f'<p>{ctx.t("minhajna.update.lede")}</p>' +
                      str(_list(ctx, 'minhajna.update.steps', True)) +
                      f'<p class="mh-caution">{ctx.t("minhajna.update.warning")}</p>'
                      f'<p>{ctx.t("minhajna.update.help")} '
                      f'<a href="#feedback">{ctx.t("minhajna.update.contact")}</a></p>')
    exercise = _section(ctx, 'try', str(_list(ctx, 'minhajna.try.steps', True)) +
                        f'<p class="mh-small">{ctx.t("minhajna.try.plan_note")}</p>')
    privacy = _section(ctx, 'privacy', f'<p>{ctx.t("minhajna.privacy.local")}</p>'
                       f'<p class="mh-caution">{ctx.t("minhajna.privacy.loss")}</p>')
    channels = [('facebook', FACEBOOK), ('email', EMAIL), ('github', REPO + '/issues/new?template=bug.yml')]
    contact = join(f'<li><a href="{esc(href)}">{ctx.t(f"minhajna.feedback.{key}")}'
                   f'{icon("arrow-ur", 18)}</a>' +
                   (f'<p>{ctx.t("minhajna.feedback.github_note")}</p>' if key == 'github' else '') + '</li>'
                   for key, href in channels)
    feedback = _section(ctx, 'feedback', f'<ol class="mh-channels">{contact}</ol>'
                        f'<p>{ctx.t("minhajna.feedback.details")}</p>'
                        f'<p class="mh-caution">{ctx.t("minhajna.feedback.safe")}</p>'
                        f'<p>{ctx.t("minhajna.feedback.security")} '
                        f'<a href="{PRIVATE_EMAIL}">{ctx.t("minhajna.feedback.private")}</a></p>')
    verification = f'''<section class="mh-section" id="verify" aria-label="{ctx.ta('minhajna.verify.title')}">
<details><summary>{ctx.t('minhajna.verify.title')}</summary><p>{ctx.t('minhajna.verify.devices')}</p>
<dl class="mh-hashes">
<dt>{ctx.t('minhajna.verify.file')}</dt><dd><bdi>minhajna-{version}.apk</bdi></dd>
<dt>{ctx.t('minhajna.verify.size')}</dt><dd><bdi>{data['apk_bytes']}</bdi></dd>
<dt>{ctx.t('minhajna.verify.sha')}</dt><dd><code dir="ltr">{data['apk_sha256']}</code></dd>
<dt>{ctx.t('minhajna.verify.certificate')}</dt><dd><code dir="ltr">{data['certificate_sha256']}</code></dd></dl>
<a href="{asset}SHA256SUMS.txt">{ctx.t('minhajna.verify.checksums')}</a>
<p><a href="{release}">{ctx.t('minhajna.verify.release')}</a></p>
</details></section>'''
    body = Markup(f'<div class="container mh-page">{hero}{_screenshots(ctx, version)}<div class="mh-scope">{features}{limits}</div>'
                  f'{install}{update}{exercise}{privacy}{feedback}{verification}</div>')
    return Page(title=ctx.s('pages.minhajna.title'), description=ctx.s('pages.minhajna.description'),
                body=body, style='minhajna', share_image=ctx.site.assets.minhajna[f'share-{ctx.lang}.png'],
                share_alt=ctx.s('pages.minhajna.title'))
