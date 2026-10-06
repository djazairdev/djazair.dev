"""/_dev/components/: every shared component in both languages, built only with ``--dev``.

Its numbers come from data/derived/, like every page. Demo issue rows are examples, not
live Hub data.
"""
from __future__ import annotations

from .. import components as C
from ..charts import Bar, BarChart, Line, LineChart, Note, UnitMap, hbars, spark, tick_compact, tick_int, tick_pct
from ..context import Ctx, Page
from ..figures import figure
from ..fmt import fdec, fint, fpct, num, quarter_label
from ..markup import Markup, esc

NAMES_EN = {'DZ': 'Algeria', 'EG': 'Egypt', 'LY': 'Libya', 'MA': 'Morocco', 'MR': 'Mauritania', 'SD': 'Sudan', 'TN': 'Tunisia',
            'NG': 'Nigeria', 'KE': 'Kenya', 'ZA': 'South Africa'}
NAMES_AR = {'DZ': 'الجزائر', 'EG': 'مصر', 'LY': 'ليبيا', 'MA': 'المغرب', 'MR': 'موريتانيا', 'SD': 'السودان', 'TN': 'تونس',
            'NG': 'نيجيريا', 'KE': 'كينيا', 'ZA': 'جنوب أفريقيا'}

T = {
    'en': dict(
        title='Components', lede='Every shared component, in both directions. Built only with --dev; not part of the site.',
        buttons='Buttons', chips='Chips and labels', controls='Chart controls', tiles='Indicator tiles',
        table='Data table', disclosure='Disclosure', hub='Hub', code='Code sample',
        explore='Explore the Index', method='Methodology', disabled='Unavailable', more='Read more',
        up='▲ 49.1% in a year', flat='▼ 26% vs Q1 2025', neutral='vs peers', down='▼ fall in accounts',
        mode='Chart mode', actual='Actual', indexed='2020 Q1 = 100', peers='Highlight a peer',
        accounts='Developer accounts', pushes='Pushes per account', repos='Repositories per account', orgs='Organisations per account',
        topics='Topics above GitHub’s threshold', north='North Africa', africa='Africa', peer_group='Algeria and 6 peers',
        acc_note='Growth rank. North Africa median', topics_note='GitHub publishes a topic once 100+ developers use it',
        in_year='in a year', vs_q='vs Q1 2025', med_na='N. Africa', med_cp='Core peers', med_af='Africa (29)',
        does=['Pushes in the quarter, divided by all accounts', 'Web-interface edits, which count as pushes'],
        doesnt=['Commits: one push can hold many', 'Code quality or impact'],
        charts='Charts',
        acc_title='Developer accounts, 2020–2026', unit_acc='Accounts',
        acc_summary='Line chart of developer accounts from Q1 2020 to Q1 2026 for Algeria, the North Africa median and six peers. '
                    'Algeria reached 586,990 in Q1 2026.',
        idx_title='Developer accounts, indexed to 2020 Q1 = 100', unit_idx='Index, 2020 Q1 = 100',
        idx_summary='Each economy’s accounts as a share of its Q1 2020 count. In Q1 2026 Algeria stands at 639 and Kenya at 747.',
        median='N. Africa median', six_peers='Six peers',
        yoy_title='Year-on-year growth in developer accounts, 2021–2026', unit_yoy='Growth on the same quarter a year earlier',
        yoy_summary='Algeria’s growth fell to 25.6% in Q1 2025, then rose for four quarters to 49.1% in Q1 2026, '
                    'above the North Africa median (44.0%) and below the Africa median (56.5%).',
        yoy_note='Four quarters of acceleration\nfrom 25.6% to 49.1% a year',
        north_median='North Africa median', africa_median='Africa median',
        bar_title='Developer accounts, growth from Q1 to Q1',
        bar_summary='Growth slowed from 44.6% in 2021 to 25.6% in 2025, then jumped to 49.1% in 2026, the fastest pace in the series.',
        um_title='One square, 1,000 developer accounts',
        um_summary='Algeria’s outline filled with 587 squares, one per 1,000 developer accounts. '
                   'The 193 bright squares are accounts added since Q1 2025.',
        um_start='Q1 2025', um_added='Added since', um_total='Q1 2026', um_note='Squares show quantity, not location.',
        src_acc='Source: GitHub Innovation Graph (CC0), 2020 Q1 – 2026 Q1. N. Africa median of Algeria, Egypt, Libya, Mauritania, '
                'Morocco, Sudan and Tunisia.',
        src_yoy='Source: GitHub Innovation Graph (CC0). Growth compares each quarter with the same quarter a year earlier. '
                'Africa: economies with 20,000+ accounts a year earlier.',
        src_um='Source: GitHub Innovation Graph (CC0), Q1 2026 data released 7 July 2026. Accounts are placed by network address.',
        caption='Algeria and six peers, Q1 2026', economy='Economy', growth='Growth', per_m='Per million',
        checks=[('licence', 'An OSI-approved open-source licence'), ('activity', 'At least one commit in the last 90 days'),
                ('docs', 'A README and a CONTRIBUTING file'), ('issues', 'At least 3 open issues labelled good first issue or help wanted'),
                ('pledge', 'Maintainers pledge to reply to newcomer pull requests within 7 days'),
                ('topic', 'The repository carries the GitHub topic djazairdev'), ('relevance', 'Algerian maintainers, or clear relevance to Algeria')],
        check_note='A failing check names what to fix. A code of conduct is recommended, not required.',
    ),
    'ar': dict(
        title='المكوّنات', lede='كل المكوّنات المشتركة، في الاتجاهين. تُبنى مع --dev فقط وليست جزءًا من الموقع.',
        buttons='الأزرار', chips='الشارات والوسوم', controls='أدوات الرسوم', tiles='بطاقات المؤشرات',
        table='جدول البيانات', disclosure='قسم قابل للطي', hub='مركز المشاريع', code='مثال شيفرة',
        explore='استكشف المؤشر', method='المنهجية', disabled='غير متاح', more='اقرأ المزيد',
        up='▲ 49,1% خلال عام', flat='▼ 26% مقارنة بالربع 1 · 2025', neutral='مقابل النظراء', down='▼ تراجع في الحسابات',
        mode='نمط الرسم', actual='القيم الفعلية', indexed='2020 Q1 = 100', peers='أبرِز أحد النظراء',
        accounts='حسابات المطوّرين', pushes='عمليات الدفع لكل حساب', repos='المستودعات لكل حساب', orgs='المنظّمات لكل حساب',
        topics='المواضيع فوق عتبة GitHub', north='شمال أفريقيا', africa='أفريقيا', peer_group='الجزائر و6 نظراء',
        acc_note='ترتيب النموّ. وسيط شمال أفريقيا', topics_note='ينشر GitHub الموضوع حين يستخدمه 100 مطوّر أو أكثر',
        in_year='خلال عام', vs_q='مقارنة بالربع 1 · 2025', med_na='شمال أفريقيا', med_cp='النظراء', med_af='أفريقيا (29)',
        does=['عمليات الدفع خلال الربع مقسومة على كل الحسابات', 'التعديلات من واجهة الويب، فهي تُحتسب عمليات دفع'],
        doesnt=['الالتزامات: قد تضمّ عملية دفع واحدة عدّة التزامات', 'جودة الشيفرة أو أثرها'],
        charts='الرسوم البيانية',
        acc_title='حسابات المطوّرين، 2020–2026', unit_acc='الحسابات',
        acc_summary='رسم خطّي لحسابات المطوّرين من الربع الأول 2020 إلى الربع الأول 2026 للجزائر ووسيط شمال أفريقيا وستة نظراء. '
                    'بلغت الجزائر 586.990 حسابًا في الربع الأول 2026.',
        idx_title='حسابات المطوّرين، مؤشَّرة على أساس الربع الأول 2020 = 100', unit_idx='المؤشر، الربع الأول 2020 = 100',
        idx_summary='حسابات كل اقتصاد نسبةً إلى عددها في الربع الأول 2020. في الربع الأول 2026 تبلغ الجزائر 639 وكينيا 747.',
        median='وسيط شمال أفريقيا', six_peers='ستة نظراء',
        yoy_title='النموّ السنوي في حسابات المطوّرين، 2021–2026', unit_yoy='النموّ مقارنة بالربع نفسه قبل عام',
        yoy_summary='تراجع نموّ الجزائر إلى 25,6% في الربع الأول 2025، ثم ارتفع أربعة أرباع متتالية إلى 49,1% في الربع الأول 2026، '
                    'فوق وسيط شمال أفريقيا (44,0%) ودون الوسيط الأفريقي (56,5%).',
        yoy_note='تسارع أربعة أرباع متتالية\nمن 25,6% إلى 49,1% سنويًا',
        north_median='وسيط شمال أفريقيا', africa_median='وسيط أفريقيا',
        bar_title='حسابات المطوّرين، النموّ من الربع الأول إلى الربع الأول',
        bar_summary='تباطأ النموّ من 44,6% في 2021 إلى 25,6% في 2025، ثم قفز إلى 49,1% في 2026، وهي أسرع وتيرة في السلسلة.',
        um_title='مربّع واحد = 1.000 حساب',
        um_summary='خريطة الجزائر مملوءة بـ587 مربّعًا، كل مربّع يمثّل 1.000 حساب. المربّعات المضيئة (193) حسابات أُضيفت منذ الربع الأول 2025.',
        um_start='الربع الأول 2025', um_added='أُضيف منذ ذلك الحين', um_total='الربع الأول 2026', um_note='المربّعات تمثّل الكمّية لا الموقع.',
        src_acc='المصدر: GitHub Innovation Graph ‏(CC0)، من الربع الأول 2020 إلى الربع الأول 2026. وسيط شمال أفريقيا: الجزائر ومصر وليبيا '
                'وموريتانيا والمغرب والسودان وتونس.',
        src_yoy='المصدر: GitHub Innovation Graph ‏(CC0). يقارن النموّ كل ربع بالربع نفسه قبل عام. أفريقيا: الاقتصادات التي تجاوزت 20.000 حساب قبل عام.',
        src_um='المصدر: GitHub Innovation Graph ‏(CC0)، بيانات الربع الأول 2026 الصادرة في 7 جويلية 2026. تُحدَّد مواقع الحسابات حسب عنوان الشبكة.',
        caption='الجزائر وستة نظراء، الربع الأول 2026', economy='الاقتصاد', growth='النموّ', per_m='لكل مليون',
        checks=[('licence', 'ترخيص مفتوح المصدر معتمد من OSI'), ('activity', 'التزام واحد على الأقل خلال آخر 90 يومًا'),
                ('docs', 'ملف README وملف CONTRIBUTING'), ('issues', '3 مهام مفتوحة على الأقل بوسم good first issue أو help wanted'),
                ('pledge', 'تعهّد المشرفين بالرد على طلبات الدمج من الوافدين الجدد خلال 7 أيام'),
                ('topic', 'يحمل المستودع موضوع GitHub ‏djazairdev'), ('relevance', 'مشرفون جزائريون، أو صلة واضحة بالجزائر')],
        check_note='يذكر كل فحص فاشل ما يجب إصلاحه. مدوّنة السلوك مستحسنة وليست شرطًا.',
    ),
}

ISSUES = [
    dict(url='https://github.com/djazairdev/djazair.dev/issues', title='Proofread the Arabic methodology page',
         labels=['good first issue', 'translation'], repo='djazairdev/djazair.dev', language='Markdown', days=2, need='Fluent Arabic, Markdown'),
    dict(url='https://github.com/djazairdev/djazair.dev/issues', title='Test the Trends data table with a screen reader',
         labels=['good first issue', 'accessibility'], repo='djazairdev/djazair.dev', language='TypeScript', days=5, need='NVDA, JAWS or VoiceOver'),
    dict(url='https://github.com/djazairdev/djazair.dev/issues', title='Test the year-on-year growth calculation against the baseline',
         labels=['help wanted', 'tests'], repo='djazairdev/djazair.dev', language='Python', days=22, need='Python'),
]


def _block(title, inner) -> Markup:
    return Markup(f'<section class="dev-block"><h2 class="dev-h">{esc(title)}</h2>{inner}</section>')


def _both(key: str) -> dict:
    return {lang: T[lang][key] for lang in T}


PEERS = ['MA', 'TN', 'EG', 'NG', 'KE', 'ZA']


def sample(data) -> dict:
    """The values the gallery shows, from the derived data (``data.Derived``)."""
    ov, peers, q = data.overview(), data.peers(), data.quarters
    s = data.series
    rank = lambda row, group: row[f'{group}_rank']
    a, p = ov['accounts'], ov['pushes_per_account']
    yoy = s('yoy', 'DZ')
    return {
        'names': NAMES_EN, 'quarters': q,
        'accounts': {c: s('accounts', c) for c in ['DZ'] + PEERS},
        'pushes': {c: s('pushes_per_account', c) for c in ['DZ'] + PEERS},
        'accounts_north_median': s('accounts', 'median_north_africa'),
        'pushes_north_median': s('pushes_per_account', 'median_north_africa'),
        'yoy': {'DZ': yoy},
        'yoy_north_median': s('yoy', 'median_north_africa'), 'yoy_africa_median': s('yoy', 'median_africa'),
        'q1_yoy': [[int(k[:4]), v] for k, v in zip(q, yoy) if k.endswith('-Q1') and v is not None],
        'topics': {c: peers[c]['topics'] for c in ['DZ'] + PEERS},
        'per_million': {c: peers[c]['accounts_per_million'] for c in ['DZ'] + PEERS},
        'latest': {
            'accounts': {'value': a['value'], 'prev': a['year_earlier'], 'yoy': ov['yoy']['value'],
                         'growth_north_rank': rank(ov['yoy'], 'north_africa'), 'growth_africa_rank': rank(ov['yoy'], 'africa'),
                         'growth_north_median': ov['yoy']['north_africa_median']},
            'pushes': {'value': p['value'], 'prev': p['year_earlier'], 'north_rank': rank(p, 'north_africa'),
                       'africa_rank': rank(p, 'africa'), 'north_median': p['north_africa_median'],
                       'core_median': p['core_peers_median'], 'africa_median': p['africa_median']},
            'repos': {'value': ov['repos_per_account']['value'], 'prev': ov['repos_per_account']['year_earlier']},
            'orgs': {'value': ov['orgs_per_account']['value'], 'prev': ov['orgs_per_account']['year_earlier']},
        },
    }


def demo_charts(d: dict) -> list:
    """The chart kit on real values: (chart, source key) pairs."""
    name = lambda c: {'en': d['names'][c], 'ar': NAMES_AR[c]}
    q = d['quarters']
    acc = d['accounts']
    accounts = LineChart(
        id='dev-accounts', quarter=q[-1], title=_both('acc_title'), summary=_both('acc_summary'), unit=_both('unit_acc'),
        x=q, fmt=lambda v, lang: fint(v, lang), tick_fmt=tick_compact, peers_label=_both('six_peers'),
        lines=[Line(c, name(c), acc[c]) for c in PEERS]
              + [Line('median_north_africa', _both('median'), d['accounts_north_median'], 'median'),
                 Line('DZ', name('DZ'), acc['DZ'], 'dz')])
    index = lambda vs: [v / vs[0] * 100 for v in vs]
    indexed = LineChart(
        id='dev-accounts-indexed', quarter=q[-1], title=_both('idx_title'), summary=_both('idx_summary'), unit=_both('unit_idx'),
        x=q, fmt=lambda v, lang: fint(round(v), lang), tick_fmt=tick_int, baseline=100, peers_label=_both('six_peers'),
        lines=[Line(c, name(c), index(acc[c]), 'hl' if c == 'KE' else 'peer') for c in PEERS]
              + [Line('median_north_africa', _both('median'), index(d['accounts_north_median']), 'median'),
                 Line('DZ', name('DZ'), index(acc['DZ']), 'dz')])
    s = 4                                        # growth needs a year of history
    yoy = LineChart(
        id='dev-yoy', quarter=q[-1], title=_both('yoy_title'), summary=_both('yoy_summary'), unit=_both('unit_yoy'),
        x=q[s:], fmt=lambda v, lang: fpct(v, 1, lang), tick_fmt=tick_pct,
        lines=[Line('median_africa', _both('africa_median'), d['yoy_africa_median'][s:], 'median'),
               Line('median_north_africa', _both('north_median'), d['yoy_north_median'][s:], 'ref'),
               Line('DZ', name('DZ'), d['yoy']['DZ'][s:], 'dz')],
        notes=[Note('2025-Q1', 'DZ', _both('yoy_note'), dy=110)])
    bars = BarChart(
        id='dev-q1-growth', quarter=q[-1], title=_both('bar_title'), summary=_both('bar_summary'),
        bars=[Bar(str(y), str(y), v) for y, v in d['q1_yoy']], fmt=lambda v, lang: fpct(v, 1, lang, sign=False), highlight='2026')
    a = d['latest']['accounts']
    units = UnitMap(
        id='dev-unit-map', quarter=q[-1], title=_both('um_title'), summary=_both('um_summary'),
        total=int(a['value']), start=int(a['prev']), start_label=_both('um_start'), added_label=_both('um_added'),
        total_label=_both('um_total'), square_label=_both('um_note'))
    return [(accounts, 'src_acc'), (indexed, 'src_acc'), (yoy, 'src_yoy'), (bars, 'src_yoy'), (units, 'src_um')]


def render(ctx: Ctx) -> Page:
    lang, t = ctx.lang, T[ctx.lang]
    d = sample(ctx.site.data)
    names = d['names'] if lang == 'en' else NAMES_AR
    L = d['latest']
    first_q, last_q = d['quarters'][0], d['quarters'][-1]

    buttons = Markup('<div class="dev-row">'
                     + C.btn(t['explore'], '#') + C.btn(t['method'], '#', 'secondary', arrow=False)
                     + C.btn(t['explore'], '#', size='s') + C.btn(t['more'], '#', 'secondary', size='s')
                     + C.button(t['disabled'], 'primary', 'm', disabled=True) + C.button(t['disabled'], 'secondary', 's', disabled=True)
                     + '</div>')
    chips = Markup('<div class="dev-row">' + C.chip(t['up'], 'up') + C.chip(t['flat'], 'flat') + C.chip(Markup(f'{num(fpct(-0.81, 0, lang))} {esc(t["neutral"])}'), 'flat')
                   + C.chip(t['down'], 'down') + '</div><div class="dev-row">'
                   + C.label_chip('good first issue') + C.label_chip('help wanted') + C.label_chip('accessibility') + '</div>')

    a, p, r, o = L['accounts'], L['pushes'], L['repos'], L['orgs']
    tabs = Markup('<div class="mts">'
                  + C.metric_tab('accounts', t['accounts'], fint(a['value'], lang), f'▲ {fpct(a["yoy"], 1, lang, sign=False)}', True, accent=True)
                  + C.metric_tab('pushes', t['pushes'], fdec(p['value'], 2, lang), f'▲ {fpct(p["value"] / p["prev"] - 1, 0, lang, sign=False)}', False)
                  + C.metric_tab('repos', t['repos'], fdec(r['value'], 2, lang), f'▼ {fpct(1 - r["value"] / r["prev"], 0, lang, sign=False)}', False)
                  + C.metric_tab('orgs', t['orgs'], fdec(o['value'], 4, lang), f'▼ {fpct(1 - o["value"] / o["prev"], 0, lang, sign=False)}', False)
                  + '</div>')
    controls = Markup(f'{tabs}<div class="dev-row">'
                      + C.seg(t['mode'], [('actual', t['actual'], False), ('indexed', t['indexed'], True)], 'actual', 'mode')
                      + f'<div class="pks" role="group" aria-label="{esc(t["peers"])}">'
                      + C.peer_chip('KE', names['KE'], True) + C.peer_chip('TN', names['TN']) + C.peer_chip('MA', names['MA'])
                      + '</div></div>')

    acc_spark = C.spark_block(spark(d['accounts']['DZ']), quarter_label(first_q, lang, 'axis'), quarter_label(last_q, lang, 'axis'))
    topics = sorted(d['topics'].items(), key=lambda kv: -kv[1])
    bars = hbars([kv for kv in topics if kv[0] in ('EG', 'NG', 'TN')] + [('DZ', d['topics']['DZ'])], lambda v: fint(v, lang), names)
    tiles = Markup('<div class="tiles">'
                   + C.tile(n=1, title=esc(t['accounts']), value=fint(a['value'], lang),
                            chip_html=C.chip(f'▲ {fpct(a["yoy"], 1, lang, sign=False)} {t["in_year"]}', 'up'), viz=acc_spark,
                            ranks=[(esc(t['north']), a['growth_north_rank'], 7), (esc(t['africa']), a['growth_africa_rank'], 29)],
                            note=Markup(f'{esc(t["acc_note"])} {num(fpct(a["growth_north_median"], 1, lang))}'), lang=lang, href='#')
                   + C.tile(n=5, title=esc(t['topics']), value=fint(d['topics']['DZ'], lang),
                            chip_html=C.chip(f'{fpct(-0.81, 0, lang)}', 'flat'), viz=bars,
                            ranks=[(esc(t['peer_group']), 7, 7)], note=esc(t['topics_note']), lang=lang)
                   + '</div>')
    push_spark = C.spark_block(spark(d['pushes']['DZ'], d['pushes_north_median']),
                               quarter_label(first_q, lang, 'axis'), quarter_label(last_q, lang, 'axis'))
    card = C.indicator_card(
        n=2, title=esc(t['pushes']), quarter=quarter_label(last_q, lang, 'short'), value=fdec(p['value'], 2, lang),
        extras=C.chip(f'▲ {fpct(p["value"] / p["prev"] - 1, 0, lang, sign=False)} {t["vs_q"]}', 'flat'), viz=push_spark,
        ranks=[(esc(t['north']), p['north_rank'], 7), (esc(t['africa']), p['africa_rank'], 29)],
        medians=[(esc(t['med_na']), fdec(p['north_median'], 2, lang)), (esc(t['med_cp']), fdec(p['core_median'], 2, lang)),
                 (esc(t['med_af']), fdec(p['africa_median'], 2, lang))],
        measures_html=C.measures_disclosure(ctx, [esc(x) for x in t['does']], [esc(x) for x in t['doesnt']]), lang=lang)

    figures = Markup(''.join(figure(ctx, chart, n, source=esc(t[src])) for n, (chart, src) in enumerate(demo_charts(d), 1)))

    order = ['DZ', 'MA', 'TN', 'EG', 'NG', 'KE', 'ZA']
    rows = []
    for c in order:
        acc = d['accounts'][c][-1]
        yoy = acc / d['accounts'][c][-5] - 1
        rows.append((c, [esc(names[c]), (C.num(fint(acc, lang)), acc), (C.num(fpct(yoy, 1, lang)), round(yoy, 6)),
                         (C.num(fint(d['per_million'][c], lang)), d['per_million'][c])]))
    table = C.data_table(esc(t['caption']), [(esc(t['economy']), 'start'), (esc(t['accounts']), 'end'), (esc(t['growth']), 'end'),
                                             (esc(t['per_m']), 'end')], rows, sortable=True, highlight='DZ')

    hub = Markup('<div class="issues">' + ''.join(C.issue_card(ctx, i) for i in ISSUES) + '</div>'
                 + C.check_panel(ctx, [(k, esc(v), True) for k, v in t['checks']], esc(t['check_note']))
                 + C.check_panel(ctx, [(k, esc(v), k != 'issues') for k, v in t['checks']][:4], esc(t['check_note'])))
    code = C.code_block(ctx, 'projects.yml', ['# Add your project at the end of projects.yml', '- repository: owner/name',
                                              '  category: library', '  tags: [arabic, payments]', '  maintainer_pledge: true',
                                              '  added: 2026-10-06'])

    body = C.page_head(eyebrow_text='djazair.dev · /_dev/', title=esc(t['title']), lede=esc(t['lede']))
    body += Markup('<div class="container dev">'
                   + _block(t['buttons'], buttons) + _block(t['chips'], chips) + _block(t['controls'], controls)
                   + _block(t['tiles'], tiles + Markup('<div class="dev-card">') + card + Markup('</div>'))
                   + _block(t['charts'], Markup(f'<div class="dev-figs">{figures}</div>')) + _block(t['table'], table)
                   + _block(t['disclosure'], C.details(ctx.t('measures.summary'), C.measures(ctx, [esc(x) for x in t['does']], [esc(x) for x in t['doesnt']])))
                   + _block(t['hub'], hub) + _block(t['code'], code) + '</div>')
    return Page(title=t['title'], description=t['lede'], body=body,
                head=Markup('<style>.dev{display:flex;flex-direction:column;gap:56px;padding-bottom:96px}'
                            '.dev-block{display:flex;flex-direction:column;gap:20px}.dev-h{font-size:22px;font-weight:800}'
                            '.dev-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.dev-stack{display:flex;flex-direction:column;gap:18px}'
                            '.dev-card{max-width:640px}.dev .checks{margin-top:16px}.dev-figs{display:flex;flex-direction:column;gap:32px}'
                            '.dev-figs .fig:nth-child(4),.dev-figs .fig:nth-child(5){max-width:720px}</style>'))
