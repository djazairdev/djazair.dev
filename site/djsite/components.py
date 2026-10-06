"""Shared page components (Components board, docs/design/system-components.png).

Each returns ``Markup``. Text arguments must already be HTML: pass ``ctx.t(...)`` output,
or wrap data with ``esc()``. Colours come from CSS classes, never inline values.
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence

from .charts import rank_strip
from .fmt import has_arabic, num, rank_text
from .icons import icon
from .markup import Markup, esc, join, striptags

# Hub language dots: a few common languages get a token colour, the rest are neutral.
LANG_DOT = {'Markdown': 'slate', 'TypeScript': 'sky', 'JavaScript': 'straw', 'Python': 'straw', 'YAML': 'lilac',
            'HTML': 'amber', 'CSS': 'lilac', 'Kotlin': 'lilac', 'Dart': 'sky', 'Go': 'sky', 'PHP': 'lilac'}


# ---------------------------------------------------------------- text
def eyebrow(text, tag: str = 'p', cls: str = '') -> Markup:
    """Small label with the mint square: 'ALGERIA DEVELOPER INDEX · Q1 2026'."""
    return Markup(f'<{tag} class="eyebrow{" " + cls if cls else ""}">{text}</{tag}>')


def h2(text, id_: str = '', cls: str = 't-section') -> Markup:
    idattr = f' id="{id_}"' if id_ else ''
    return Markup(f'<h2 class="{cls}"{idattr}>{text}</h2>')


def section(id_: str, eyebrow_text, title, inner, lede=None, size: str = 'm', head_extra='') -> Markup:
    """A page section: eyebrow, h2, optional lede, then content. ``size``: m (46 px) or s (36 px)."""
    lede_html = f'<p class="lede">{lede}</p>' if lede else ''
    return Markup(f'''<section class="section section-{size}" id="{id_}" aria-labelledby="{id_}-h">
<div class="container">
<div class="section-head"><div class="section-head-text">{eyebrow(eyebrow_text)}{h2(title, f"{id_}-h")}{lede_html}</div>{head_extra}</div>
{inner}
</div>
</section>''')


# ---------------------------------------------------------------- actions
def btn(label, href: str, kind: str = 'primary', size: str = 'm', arrow: bool = True, attrs: str = '') -> Markup:
    """Link styled as a button. ``kind``: primary | secondary. ``size``: m (48 px) | s (40 px)."""
    arr = f'<span class="arr">{icon("arrow", 18, 2)}</span>' if arrow else ''
    sz = ' btn-s' if size == 's' else ''
    return Markup(f'<a class="btn btn-{kind}{sz}" href="{esc(href)}"{attrs}>{label}{arr}</a>')


def button(label, kind: str = 'secondary', size: str = 's', disabled: bool = False, attrs: str = '', icon_name: str = '') -> Markup:
    """A real <button> with button styles."""
    sz = ' btn-s' if size == 's' else ''
    ic = icon(icon_name, 17) if icon_name else ''
    dis = ' disabled' if disabled else ''
    return Markup(f'<button type="button" class="btn btn-{kind}{sz}"{dis}{attrs}>{ic}{label}</button>')


# ---------------------------------------------------------------- chips and labels
def chip(text, kind: str = 'flat') -> Markup:
    """Value chip. ``up``: mint, for Algeria's growth only. ``flat``: neutral ratios. ``down``: plain falls.

    A chip of figures only is isolated left to right. When it mixes Arabic words and a
    figure, wrap the figure in ``num()`` so its sign and per cent stay in place."""
    if has_arabic(text):
        return Markup(f'<span class="chip chip-{kind}">{text}</span>')
    return Markup(f'<span class="chip chip-{kind} num" dir="ltr">{text}</span>')


def label_chip(text) -> Markup:
    """GitHub label on a Hub issue; 'good first issue' is mint."""
    gfi = ' lbl-gfi' if str(text) == 'good first issue' else ''
    return Markup(f'<span class="lbl{gfi}" dir="auto">{esc(text)}</span>')


# ---------------------------------------------------------------- chart controls
def seg(label, options: Sequence, selected: str, name: str = '') -> Markup:
    """Segmented control. ``options``: [(value, text, mono)]. The selected button has aria-pressed=true."""
    out = []
    for value, text, mono in options:
        pressed = 'true' if value == selected else 'false'
        cls = ' class="mono" dir="ltr"' if mono else ''
        out.append(f'<button type="button"{cls} data-value="{esc(value)}" aria-pressed="{pressed}">{text}</button>')
    data = f' data-control="{esc(name)}"' if name else ''
    return Markup(f'<div class="seg" role="group" aria-label="{striptags(label)}"{data}>{join(out)}</div>')


def metric_tab(key: str, label, value: str, delta: str, selected: bool, accent: bool = False) -> Markup:
    """Metric tab for chart views: carries its own latest value and change."""
    d_cls = 'mt-d up' if accent else 'mt-d'
    return Markup(f'<button type="button" class="mt" data-value="{esc(key)}" aria-pressed="{"true" if selected else "false"}">'
                  f'<span class="mt-k">{label}</span>'
                  f'<span class="mt-v"><span class="num" dir="ltr">{esc(value)}</span><span class="{d_cls} num" dir="ltr">{esc(delta)}</span></span>'
                  f'</button>')


def peer_chip(code: str, name, selected: bool = False) -> Markup:
    """Toggle to highlight one peer in amber; pressing it again clears it."""
    return Markup(f'<button type="button" class="pk" data-value="{esc(code)}" aria-pressed="{"true" if selected else "false"}">'
                  f'<span class="sw" aria-hidden="true"></span>{name}</button>')


# ---------------------------------------------------------------- tiles
def rank_row(label, rank: int, of: int, lang: str) -> Markup:
    text = rank_text(rank, of, lang)
    aria = Markup(f'{striptags(label)}: {esc(text)}')
    return Markup(f'<div class="rank-row"><div class="rank-head"><span>{label}</span>{num(text, "num rank-n")}</div>'
                  f'{rank_strip(rank, of, aria)}</div>')


def spark_block(spark_svg, start_label: str, end_label: str) -> Markup:
    """Sparkline with its first and last quarter under it (time runs left to right)."""
    return Markup(f'<div class="spark-block">{spark_svg}<div class="spark-axis" dir="ltr">'
                  f'<span>{esc(start_label)}</span><span>{esc(end_label)}</span></div></div>')


def tile(*, n: int, title, value: str, chip_html, viz, ranks: Iterable, note, lang: str, href: Optional[str] = None) -> Markup:
    """Compact indicator tile (Home scorecard): number, title, chip, value, chart, ranks, note."""
    rank_html = ''.join(rank_row(lb, r, of, lang) for lb, r, of in ranks)
    tag, link = ('a', f' href="{esc(href)}"') if href else ('article', '')
    return Markup(f'''<{tag} class="card tile reveal"{link}>
<div class="tile-top"><div class="tile-title"><span class="tile-n num">{n:02d}</span><h3>{title}</h3></div>{chip_html}</div>
<div class="tile-value num" dir="ltr">{esc(value)}</div>
{viz}
<div class="tile-foot">{f'<div class="ranks">{rank_html}</div>' if rank_html else ''}<p class="tile-note">{note}</p></div>
</{tag}>''')


def indicator_card(*, n: int, title, quarter: str, value: str, extras: str = '', viz, ranks: Iterable,
                   medians: Iterable = (), measures_html='', lang: str, id_: str = '') -> Markup:
    """Full indicator card (Index overview): value, change, chart, ranks, medians, 'What this measures'."""
    rank_html = ''.join(rank_row(lb, r, of, lang) for lb, r, of in ranks)
    med_html = ''.join(f'<div class="med"><span>{k}</span>{num(v)}</div>' for k, v in medians)
    ident = f' id="{esc(id_)}"' if id_ else ''
    return Markup(f'''<article class="card indicator reveal"{ident}>
<div class="ind-top"><div class="tile-title"><span class="tile-n num">{n:02d}</span><h2>{title}</h2></div><span class="ind-q">{esc(quarter)}</span></div>
<div class="ind-value"><span class="ind-v num" dir="ltr">{esc(value)}</span>{extras}</div>
{viz}
<div class="ind-foot"><div class="ranks">{rank_html}</div><div class="meds">{med_html}</div></div>
{measures_html}
</article>''')


# ---------------------------------------------------------------- figures
def frame(inner, cls: str = '', labelledby: str = '') -> Markup:
    """Figure frame with engineering-drawing corner marks."""
    corners = ''.join(f'<span class="cm cm-{c}" aria-hidden="true"></span>' for c in ('tl', 'tr', 'bl', 'br'))
    label = f' aria-labelledby="{esc(labelledby)}"' if labelledby else ''
    return Markup(f'<figure class="frame {cls}"{label}>{corners}{inner}</figure>')


def fig_label(ctx, n: int, title, id_: str = '') -> Markup:
    ident = f' id="{esc(id_)}"' if id_ else ''
    return Markup(f'<div class="fig-label"{ident}><span class="fig-n">{ctx.t("fig.label")} {n:02d}</span>'
                  f'<span class="fig-t">{title}</span></div>')


def source_line(text, actions='') -> Markup:
    """Source and data quarter for a chart or table (IDX-13), with its downloads."""
    acts = f'<div class="src-actions">{actions}</div>' if actions else ''
    return Markup(f'<div class="src"><p class="src-text">{text}</p>{acts}</div>')


def action_link(label, href: str, icon_name: str = 'download', mono: bool = True, download: bool = True) -> Markup:
    cls = 'act num' if mono else 'act'
    dl = ' download' if download else ''
    return Markup(f'<a class="{cls}" href="{esc(href)}"{dl}>{icon(icon_name, 15)}{label}</a>')


def download_menu(ctx, files: dict) -> Markup:
    """'Download' disclosure listing a chart's files: {key: (url, file name)} with the keys csv,
    json, svg-dark, svg-light, png-dark and png-light. A PNG is drawn in the browser from the
    SVG at its URL, so PNG items start hidden and site.js shows them."""
    order = [('csv', 'CSV'), ('json', 'JSON'), ('svg-dark', ctx.t('dl.svg_dark')), ('svg-light', ctx.t('dl.svg_light')),
             ('png-dark', ctx.t('dl.png_dark')), ('png-light', ctx.t('dl.png_light'))]
    items = []
    for key, label in order:
        if key not in files:
            continue
        url, name = files[key]
        png = key.startswith('png')
        items.append(f'<li{" hidden data-png" if png else ""}><a href="{esc(url)}" download="{esc(name)}"'
                     f'{" data-png" if png else ""}>{label}</a></li>')
    return Markup(f'<details class="dl"><summary class="act">{icon("download", 15)}{ctx.t("dl.download")}</summary>'
                  f'<ul class="dl-menu">{join(items)}</ul></details>')


# ---------------------------------------------------------------- tables
def data_table(caption, head: Sequence, rows: Iterable, *, sortable: bool = False, cls: str = '',
               highlight: Optional[str] = None, sorted_by: Optional[tuple] = None, foot: Iterable = ()) -> Markup:
    """Data table. ``head``: [(label, align)] where align is 'start' or 'end'.
    ``rows``: [(key, [cells])]; the first cell is the row header. A cell is HTML, or
    ``(html, sort_value)`` so sorting works whatever the number format.
    ``sorted_by``: (column index, 'descending' | 'ascending') for the order the rows come in.
    ``foot``: rows in the same shape, such as group medians, which stay below when sorting.
    Sorting is added by site.js; without JavaScript the table keeps its order."""
    th = []
    for i, (label, align) in enumerate(head):
        sort = ' data-sort' if sortable else ''
        state = f' aria-sort="{sorted_by[1]}"' if sorted_by and sorted_by[0] == i else ''
        th.append(f'<th scope="col" class="{align}"{sort}{state}>{label}</th>')

    def tr(key, cells) -> str:
        tr_cls = ' class="is-dz"' if highlight and key == highlight else ''
        out = []
        for i, cell in enumerate(cells):
            html, value = (cell if isinstance(cell, tuple) else (cell, None))
            v = f' data-v="{esc(value)}"' if value is not None else ''
            if i == 0:
                out.append(f'<th scope="row"{v}>{html}</th>')
            else:
                out.append(f'<td class="{head[i][1]}"{v}>{html}</td>')
        return f'<tr{tr_cls} data-key="{esc(key)}">{"".join(out)}</tr>'

    body = ''.join(tr(key, cells) for key, cells in rows)
    tfoot = ''.join(tr(key, cells) for key, cells in foot)
    sort_attr = ' data-sortable' if sortable else ''
    return Markup(f'<div class="table-wrap {cls}" tabindex="0" role="region" aria-label="{striptags(caption)}">'
                  f'<table class="dt"{sort_attr}><caption class="sr-only">{caption}</caption>'
                  f'<thead><tr>{"".join(th)}</tr></thead><tbody>{body}</tbody>'
                  f'{f"<tfoot>{tfoot}</tfoot>" if tfoot else ""}</table></div>')


# ---------------------------------------------------------------- disclosure
def details(summary, body, open_: bool = False, cls: str = '', icon_name: str = 'info', id_: str = '') -> Markup:
    ident = f' id="{esc(id_)}"' if id_ else ''
    return Markup(f'<details class="disclosure {cls}"{ident}{" open" if open_ else ""}>'
                  f'<summary><span class="disc-s">{icon(icon_name, 16)}{summary}</span><span class="chev">{icon("chev", 18)}</span></summary>'
                  f'<div class="disc-body">{body}</div></details>')


def measures(ctx, does: Iterable, doesnt: Iterable) -> Markup:
    """'What this measures / what it doesn't' (IDX-12)."""
    col = lambda head, items, mark, cls: (
        f'<div class="ms-col"><p class="ms-h">{head}</p><ul>'
        + ''.join(f'<li><span class="ms-mark {cls}" aria-hidden="true">{mark}</span><span>{x}</span></li>' for x in items)
        + '</ul></div>')
    return Markup(f'<div class="ms">{col(ctx.t("measures.does"), does, "+", "yes")}'
                  f'{col(ctx.t("measures.doesnt"), doesnt, "−", "no")}</div>')


def measures_disclosure(ctx, does, doesnt) -> Markup:
    return details(ctx.t('measures.summary'), measures(ctx, does, doesnt))


# ---------------------------------------------------------------- Hub
def issue_icon() -> Markup:
    return Markup('<svg class="icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                  'stroke-width="1.8" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="8.5"/>'
                  '<circle cx="12" cy="12" r="1.8" fill="currentColor" stroke="none"/></svg>')


def ago(days: int, lang: str) -> str:
    """'5 days ago', '3 weeks ago' / 'منذ 5 أيام', 'منذ 3 أسابيع'."""
    if lang == 'en':
        if days < 1:
            return 'today'
        if days < 14:
            return '1 day ago' if days == 1 else f'{days} days ago'
        w = days // 7
        return f'{w} weeks ago'
    if days < 1:
        return 'اليوم'
    if days < 14:
        if days == 1:
            return 'منذ يوم'
        if days == 2:
            return 'منذ يومين'
        return f'منذ {days} أيام' if days <= 10 else f'منذ {days} يومًا'
    w = days // 7
    if w == 2:
        return 'منذ أسبوعين'
    return f'منذ {w} أسابيع' if w <= 10 else f'منذ {w} أسبوعًا'


def issue_card(ctx, issue: dict) -> Markup:
    """A beginner issue from a listed project. Links to GitHub; shows what you'll need, never who opened it.
    ``issue``: url, title, labels, repo, language, days, need (optional). Every field is escaped."""
    labels = ''.join(label_chip(l) for l in issue.get('labels', []))
    lang_name = issue.get('language') or ''
    dot = LANG_DOT.get(lang_name, 'neutral')
    lang_html = f'<span class="ic-lang"><span class="dot dot-{dot}" aria-hidden="true"></span>{esc(lang_name)}</span>' if lang_name else ''
    need = issue.get('need')
    need_html = f'<span class="ic-need">{ctx.t("hub.need")} <span dir="auto">{esc(need)}</span></span>' if need else ''
    attrs = ''.join(f' data-{k}="{esc(v)}"' for k, v in (issue.get('data') or {}).items())
    return Markup(f'''<a class="issue" href="{esc(issue["url"])}"{attrs}>
<span class="ic-icon">{issue_icon()}</span>
<span class="ic-main"><span class="ic-head"><span class="ic-title" dir="auto">{esc(issue["title"])}</span><span class="ic-labels">{labels}</span></span>
<span class="ic-meta"><span class="ic-repo num" dir="ltr">{esc(issue["repo"])}</span>{lang_html}{need_html}</span></span>
<span class="ic-age">{esc(ago(issue["days"], ctx.lang))}</span>
</a>''')


def check_panel(ctx, checks: Sequence, note=None, title: str = 'listing-check', summary=None) -> Markup:
    """Inclusion-check results: ``checks`` is [(key, description, passed)] (HUB-03)."""
    passed = sum(1 for _, _, ok in checks if ok)
    rows = ''.join(
        f'<li class="{"ok" if ok else "fail"}"><span class="ck-mark">{icon("check" if ok else "x", 13, 2.4)}'
        f'<span class="sr-only">{ctx.t("checks.pass" if ok else "checks.fail")}</span></span>'
        f'<span class="ck-key num" dir="ltr">{esc(key)}</span><span class="ck-desc">{desc}</span></li>'
        for key, desc, ok in checks)
    status = ctx.t('checks.passed', n=passed, total=len(checks))
    all_ok = passed == len(checks)
    return Markup(f'''<div class="checks{" all-ok" if all_ok else ""}">
<div class="ck-head"><span class="ck-title">{icon("check" if all_ok else "x", 18, 2.2)}<span class="num" dir="ltr">{esc(title)}</span><span class="ck-status num">{status}</span></span>
<span class="ck-sub">{summary or ctx.t("checks.when")}</span></div>
<ol>{rows}</ol>
{f'<div class="ck-note">{note}</div>' if note else ''}
</div>''')


def code_block(ctx, name: str, lines: Sequence[str]) -> Markup:
    """A small YAML-style code sample with line numbers and a Copy button (shown when JavaScript runs)."""
    def colour(line: str) -> str:
        if line.strip().startswith('#'):
            return f'<span class="c-comment">{esc(line)}</span>'
        if ':' in line:
            k, v = line.split(':', 1)
            return f'<span class="c-key">{esc(k)}</span><span class="c-punct">:</span><span class="c-val">{esc(v)}</span>'
        return str(esc(line))
    body = '\n'.join(colour(l) for l in lines)
    nums = '\n'.join(str(i + 1) for i in range(len(lines)))
    return Markup(f'''<figure class="code" dir="ltr">
<figcaption><span class="code-name">{icon("code", 16)}{esc(name)}</span><button type="button" class="act" data-copy data-copied="{ctx.ta('code.copied')}" hidden>{ctx.t("code.copy")}</button></figcaption>
<div class="code-body"><pre class="code-nums" aria-hidden="true">{nums}</pre><pre class="code-src"><code>{body}</code></pre></div>
</figure>''')


# ---------------------------------------------------------------- page head
def page_head(*, eyebrow_text, title, lede=None, meta: Optional[Iterable] = None, actions=None) -> Markup:
    """The top of an inner page: eyebrow, h1, lede, optional meta row and actions."""
    meta_html = ''
    if meta:
        meta_html = ('<dl class="page-meta">'
                     + ''.join(f'<div><dt>{k}</dt><dd>{num(v) if not isinstance(v, Markup) else v}</dd></div>' for k, v in meta)
                     + '</dl>')
    lede_html = f'<p class="lede">{lede}</p>' if lede else ''
    actions_html = f'<div class="page-actions">{join(actions)}</div>' if actions else ''
    return Markup(f'''<section class="page-head">
<div class="container page-head-row">
<div class="page-head-text">{eyebrow(eyebrow_text)}
<h1>{title}</h1>
{lede_html}{meta_html}</div>
{actions_html}
</div>
</section>''')
