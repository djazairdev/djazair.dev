"""/_dev/components/: every shared component in both languages, built only with ``--dev``.

It uses a snapshot of real Innovation Graph values (site/dev/sample.json); the real pages
read data/derived/. Demo issue rows are examples, not live Hub data.
"""
from __future__ import annotations

import json

from .. import components as C
from ..charts import hbars, spark
from ..config import SITE_DIR
from ..context import Ctx, Page
from ..fmt import fdec, fint, fpct, num, quarter_label
from ..markup import Markup, esc

SAMPLE = SITE_DIR / 'dev' / 'sample.json'

NAMES_AR = {'DZ': 'الجزائر', 'EG': 'مصر', 'LY': 'ليبيا', 'MA': 'المغرب', 'MR': 'موريتانيا', 'SD': 'السودان', 'TN': 'تونس',
            'NG': 'نيجيريا', 'KE': 'كينيا', 'ZA': 'جنوب أفريقيا'}

T = {
    'en': dict(
        title='Components', lede='Every shared component, in both directions. Built only with --dev; not part of the site.',
        buttons='Buttons', chips='Chips and labels', controls='Chart controls', tiles='Indicator tiles',
        figure='Figure frame and source line', table='Data table', disclosure='Disclosure', hub='Hub', code='Code sample',
        explore='Explore the Index', method='Methodology', disabled='Unavailable', more='Read more',
        up='▲ 49.1% in a year', flat='▼ 26% vs Q1 2025', neutral='vs peers', down='▼ fall in accounts',
        mode='Chart mode', actual='Actual', indexed='2020 Q1 = 100', peers='Highlight a peer',
        accounts='Developer accounts', pushes='Pushes per account', repos='Repositories per account', orgs='Organisations per account',
        topics='Topics above GitHub’s threshold', north='North Africa', africa='Africa', peer_group='Algeria and 6 peers',
        acc_note='Growth rank. North Africa median', topics_note='GitHub publishes a topic once 100+ developers use it',
        in_year='in a year', vs_q='vs Q1 2025', med_na='N. Africa', med_cp='Core peers', med_af='Africa (29)',
        does=['Pushes in the quarter, divided by all accounts', 'Web-interface edits, which count as pushes'],
        doesnt=['Commits: one push can hold many', 'Code quality or impact'],
        fig_title='Developer accounts in Algeria since 2020',
        source='Source: GitHub Innovation Graph (CC0), Q1 2026. Accounts at the end of each quarter.',
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
        figure='إطار الشكل وسطر المصدر', table='جدول البيانات', disclosure='قسم قابل للطي', hub='مركز المشاريع', code='مثال شيفرة',
        explore='استكشف المؤشر', method='المنهجية', disabled='غير متاح', more='اقرأ المزيد',
        up='▲ 49,1% خلال عام', flat='▼ 26% مقارنة بالربع 1 · 2025', neutral='مقابل النظراء', down='▼ تراجع في الحسابات',
        mode='نمط الرسم', actual='القيم الفعلية', indexed='2020 Q1 = 100', peers='أبرِز أحد النظراء',
        accounts='حسابات المطوّرين', pushes='عمليات الدفع لكل حساب', repos='المستودعات لكل حساب', orgs='المنظّمات لكل حساب',
        topics='المواضيع فوق عتبة GitHub', north='شمال أفريقيا', africa='أفريقيا', peer_group='الجزائر و6 نظراء',
        acc_note='ترتيب النموّ. وسيط شمال أفريقيا', topics_note='ينشر GitHub الموضوع حين يستخدمه 100 مطوّر أو أكثر',
        in_year='خلال عام', vs_q='مقارنة بالربع 1 · 2025', med_na='شمال أفريقيا', med_cp='النظراء', med_af='أفريقيا (29)',
        does=['عمليات الدفع خلال الربع مقسومة على كل الحسابات', 'التعديلات من واجهة الويب، فهي تُحتسب عمليات دفع'],
        doesnt=['الالتزامات: قد تضمّ عملية دفع واحدة عدّة التزامات', 'جودة الشيفرة أو أثرها'],
        fig_title='حسابات المطوّرين في الجزائر منذ 2020',
        source='المصدر: GitHub Innovation Graph ‏(CC0)، الربع الأول 2026. الحسابات في نهاية كل ربع.',
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


def render(ctx: Ctx) -> Page:
    lang, t = ctx.lang, T[ctx.lang]
    d = json.loads(SAMPLE.read_text('utf-8'))
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

    files = {'csv': '/_dev/sample.json', 'json': '/_dev/sample.json', 'svg-dark': '/_dev/sample.json',
             'svg-light': '/_dev/sample.json', 'png-dark': '/_dev/sample.json', 'png-light': '/_dev/sample.json'}
    figure = C.frame(Markup(f'<div class="dev-stack">{C.fig_label(ctx, 1, esc(t["fig_title"]))}{acc_spark}'
                            f'{C.source_line(esc(t["source"]), C.download_menu(ctx, files))}</div>'))

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
                   + _block(t['figure'], figure) + _block(t['table'], table)
                   + _block(t['disclosure'], C.details(ctx.t('measures.summary'), C.measures(ctx, [esc(x) for x in t['does']], [esc(x) for x in t['doesnt']])))
                   + _block(t['hub'], hub) + _block(t['code'], code) + '</div>')
    return Page(title=t['title'], description=t['lede'], body=body,
                head=Markup('<style>.dev{display:flex;flex-direction:column;gap:56px;padding-bottom:96px}'
                            '.dev-block{display:flex;flex-direction:column;gap:20px}.dev-h{font-size:22px;font-weight:800}'
                            '.dev-row{display:flex;flex-wrap:wrap;gap:12px;align-items:center}.dev-stack{display:flex;flex-direction:column;gap:18px}'
                            '.dev-card{max-width:640px}.dev .checks{margin-top:16px}</style>'))
