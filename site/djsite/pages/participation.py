"""Participation-first Home content, drawn from the existing public Hub snapshot."""
from .. import components as C, config, contributions, public_projects as project_discovery
from ..fmt import date_label, fint, num, quarter_label
from ..icons import icon
from ..markup import Markup, esc, join
from . import hub


def save_control(ctx) -> Markup:
    return C.button(ctx.t('participation.save'), attrs=f' hidden data-save-view data-saved="{ctx.ta("participation.saved")}" data-error="{ctx.ta("participation.save_failed")}"')


def opportunities(ctx) -> Markup:
    data = ctx.site.hub
    # A small, diverse preview; the full issue inventory remains in the Hub.
    issues, seen_types = [], set()
    for issue in data.issues:
        kind = contributions.kind(issue)
        if kind not in seen_types:
            issues.append(issue)
            seen_types.add(kind)
        if len(issues) == 3:
            break
    if len(issues) < 3:
        issues += [i for i in data.issues if i not in issues][:3 - len(issues)]
    projects = {p['repository']: p for p in data.projects}
    types = {contributions.kind(i) for i in issues}
    options = join(f'<option value="{key}">{ctx.t(f"participation.types.{key}")}</option>'
                   for key in contributions.TYPES if key in types)
    languages = sorted({i.get('language') for i in issues if i.get('language')})
    languages_html = join(f'<option value="{esc(k)}">{esc(k)}</option>' for k in languages)
    tools = Markup(f'<form class="opportunity-tools" action="{ctx.url("hub")}#issues" method="get">'
                   f'<label>{ctx.t("participation.type")}<select name="type"><option value="">{ctx.t("participation.all_types")}</option>{options}</select></label>'
                   f'<label>{ctx.t("participation.project_language")}<select name="lang"><option value="">{ctx.t("hub.all_languages")}</option>{languages_html}</select></label>'
                   f'<label class="opportunity-search">{ctx.t("participation.skills")}<input type="search" name="q" placeholder="{ctx.ta("participation.search")}"></label>'
                   f'<button class="btn btn-secondary" type="submit">{ctx.t("participation.browse")}{icon("arrow", 18)}</button></form>')
    cards = []
    for issue in issues:
        kind = contributions.kind(issue)
        project = projects.get(issue['repo'], {})
        beginner = 'good first issue' in [l.lower() for l in issue.get('labels', [])]
        badge = C.chip(ctx.t('participation.beginner' if beginner else 'participation.help'))
        pledge = (f'<p class="opportunity-pledge">{icon("reply", 15)}{ctx.t("participation.pledge")}</p>'
                  if project.get('pledge') else '')
        cards.append(f'<article class="card opportunity" data-type="{kind}" data-lang="{esc(issue.get("language") or "")}">'
                     f'<div class="opportunity-top"><span class="opportunity-type">{ctx.t(f"participation.types.{kind}")}</span>{badge}</div>'
                     f'<h3><a href="{esc(issue["url"])}" dir="auto">{esc(issue["title"])}</a></h3>'
                     f'<p class="opportunity-project"><bdi>{esc(issue["repo"])}</bdi></p>'
                     f'<p class="opportunity-date">{ctx.t("hub.opened")} <time datetime="{esc(issue["created_at"])}">{esc(date_label(issue["created_at"], ctx.lang))}</time></p>'
                     f'<p class="opportunity-purpose" dir="auto">{esc(project.get("description") or "")}</p>'
                     f'<p class="opportunity-needs">{ctx.t("hub.need")} <span dir="auto">{esc(issue.get("needs") or issue.get("language") or ctx.s("participation.read_issue"))}</span></p>'
                     f'{pledge}<a class="opportunity-action" href="{esc(issue["url"])}">{ctx.t("participation.view_issue")}{icon("arrow-ur", 16)}</a></article>')
    stamp = ''
    if data.synced:
        stamp = ctx.t('participation.updated', date=Markup(f'<time datetime="{data.synced.isoformat()}">{esc(date_label(data.synced.date(), ctx.lang))}</time>'))
    if not issues:
        body = Markup(f'<div class="empty-state"><div><h3>{ctx.t("home.hub_empty_title")}</h3><p>{ctx.t("home.hub_empty")}</p></div>'
                      f'{C.btn(ctx.t("home.hub_list"), ctx.url("hub", hash="list"))}</div>')
    else:
        body = tools + Markup(f'<p class="opportunity-count" role="status" data-count="{ctx.ta("participation.match_count", n="{n}")}">'
                              f'{ctx.t("participation.match_count", n=len(issues))}</p><div class="opportunity-grid">{join(cards)}</div>'
                              f'<div class="opportunity-empty" hidden><p>{ctx.t("participation.no_match")}</p>'
                              f'{C.btn(ctx.t("participation.all_issues"), ctx.url("hub", hash="issues"), "secondary")}</div>'
                              f'<div class="opportunity-foot"><a class="lnk" data-matching-hub href="{ctx.url("hub", hash="issues")}">{ctx.t("participation.all_issues")}{icon("arrow", 16)}</a>'
                              f'{save_control(ctx)}</div>')
    note = Markup(f'<p class="participation-note">{stamp} {ctx.t("participation.feed_note")}</p>')
    steps = join(f'<li><h3>{ctx.t(f"hub.step{i}_t")}</h3><p>{ctx.t(f"hub.step{i}")}</p></li>' for i in (1, 2, 3))
    starter = Markup(f'<details class="first-contribution"><summary>{ctx.t("participation.first_time")}{icon("chev", 18)}</summary>'
                     f'<ol>{steps}</ol>'
                     f'<a class="lnk" href="{ctx.url("hub", hash="contribute")}">{ctx.t("participation.guide")}{icon("arrow", 16)}</a></details>')
    return C.section('contributions', ctx.t('participation.opportunities_eyebrow'), ctx.t('participation.opportunities_title'),
                     body + note + starter + public_projects(ctx), lede=ctx.t('participation.opportunities_lede'))


def public_projects(ctx) -> Markup:
    data = project_discovery.load()
    cards = []
    for project in data['projects']:
        repo = project['repository']
        stamp = Markup(f'<time datetime="{esc(project["last_commit"])}">{esc(date_label(project["last_commit"], ctx.lang))}</time>')
        cards.append(f'<article class="card public-project"><h4><a href="https://github.com/{esc(repo)}"><bdi>{esc(project["name"])}</bdi></a></h4>'
                     f'<p class="public-project-stack"><bdi>{esc(project["language"])} · {esc(project["licence"])}</bdi></p>'
                     f'<p>{esc(project[ctx.lang])}</p><p class="participation-note">{ctx.t("participation.project_updated", date=stamp)}</p>'
                     f'<a class="lnk" href="{esc(project["contribute"])}">{ctx.t("participation.public_action")}{icon("arrow-ur", 16)}</a></article>')
    stamp = Markup(f'<time datetime="{data["checked"]}">{esc(date_label(data["checked"], ctx.lang))}</time>')
    return Markup(f'<div class="public-discovery" role="group" aria-labelledby="public-projects-h">'
                  f'<h3 id="public-projects-h">{ctx.t("participation.public_title")}</h3>'
                  f'<p class="participation-note">{ctx.t("participation.public_note", date=stamp)}</p>'
                  f'<div class="public-projects">{join(cards)}</div></div>')


def follow_work(ctx) -> Markup:
    """Public activity and saved searches share one compact follow-up section."""
    projects = []
    for project in ctx.site.hub.projects[:3]:
        repo = project['repository']
        commit = project.get('last_commit')
        stamp = Markup(f'<time datetime="{esc(commit)}">{esc(date_label(commit, ctx.lang))}</time>') if commit else ''
        updated = f'<p class="participation-note">{ctx.t("participation.project_updated", date=stamp)}</p>' if commit else ''
        projects.append(f'<li><a class="lnk" href="https://github.com/{esc(repo)}/pulls?q=is%3Apr+is%3Amerged"><bdi>{esc(repo)}</bdi>{icon("arrow-ur", 16)}</a>{updated}</li>')
    work = (Markup(f'<ul class="follow-projects" role="list">{join(projects)}</ul>') if projects else
            Markup(f'<p class="participation-note">{ctx.t("participation.projects_empty")}</p>'))
    metrics = getattr(ctx.site.hub, 'metrics', None)
    measured = ''
    if metrics and metrics.get('quarters'):
        row = metrics['quarters'][-1]
        measured = (f'<div class="community-measured"><p>{ctx.t("participation.contributors", n=num(fint(row["new_contributors"], ctx.lang)), quarter=quarter_label(row["quarter"], ctx.lang))}</p>'
                    f'<p class="participation-note">{ctx.t("participation.metrics_note")}</p>'
                    f'<a class="lnk" href="{ctx.url("hub", hash="numbers")}">{ctx.t("participation.metrics_more")}</a></div>')
    saved = (f'<h3>{ctx.t("participation.return_saved_title")}</h3><p>{ctx.t("participation.return_saved_text")}</p>'
             f'<a class="lnk" data-saved-hub href="{ctx.url("hub", hash="issues")}">{ctx.t("participation.return_saved_action")}{icon("arrow", 16)}</a>')
    watch = (f'<details class="first-contribution"><summary>{ctx.t("participation.watch_help")}{icon("chev", 18)}</summary>'
             f'<p>{ctx.t("participation.watch_steps")}</p><a class="lnk" href="{config.REPO_URL}">{ctx.t("participation.return_watch_action")}{icon("arrow-ur", 16)}</a>'
             f'<p><a class="lnk" href="https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications">{ctx.t("participation.watch_docs")}{icon("arrow-ur", 16)}</a></p></details>')
    body = Markup(f'<div class="follow-grid"><div class="card follow-panel" id="community-progress">'
                  f'<h3>{ctx.t("participation.reviewed_work")}</h3><p>{ctx.t("participation.progress_lede")}</p>{work}{measured}</div>'
                  f'<div class="card follow-panel">{saved}{watch}</div></div>')
    return C.section('stay-connected', ctx.t('participation.progress_eyebrow'), ctx.t('participation.return_title'),
                     body, lede=ctx.t('participation.return_lede'))


def index_teaser(ctx) -> Markup:
    """Keep a sourced gateway to the Index instead of repeating its six charts."""
    folder = ctx.site.data.folder.name
    source = ctx.t('home.source', quarter=quarter_label(ctx.site.data.quarter, ctx.lang), date=date_label(ctx.site.data.release_date, ctx.lang))
    actions = (C.btn(ctx.t('home.cta_index'), ctx.url('overview')) +
               C.btn(ctx.t('participation.index_trends'), ctx.url('trends'), 'secondary'))
    files = C.action_link('CSV', f'/data/{folder}/overview.csv') + C.action_link('JSON', f'/data/{folder}/overview.json')
    body = Markup(f'<div class="index-teaser" id="scorecard"><div id="fig-home-yoy">'
                  f'<div class="page-actions">{actions}</div>{C.source_line(source, files)}</div></div>')
    return C.section('trend', ctx.t('participation.index_eyebrow', quarter=quarter_label(ctx.site.data.quarter, ctx.lang)),
                     ctx.t('participation.index_title'), body, lede=ctx.t('participation.index_lede'))
