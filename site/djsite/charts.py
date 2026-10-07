"""Build-time SVG charts.

One renderer per chart type draws with explicit colours from a palette: ``DARK`` on the
page (it mirrors the CSS tokens) and ``DARK`` or ``LIGHT`` in downloaded files, so the
page and the downloads can never drift apart. The same data always gives the same SVG.

Time always runs left to right, in Arabic too, and maps are never mirrored. Arabic words
inside a chart are set right to left; figures stay left to right.

Chart specs are language-neutral: names and titles are ``Text``, either one string or
``{'en': ..., 'ar': ...}``, and formatters take ``(value, lang)``. The figure that shows a
chart (``figures.py``) picks the language and writes the downloads.
"""
from __future__ import annotations

import csv
import io
import json
import math
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, Sequence, Union

from . import unitmap
from .fmt import fcompact, fdec, fint, fpct, has_arabic, num, parse_quarter, quarter_label
from .markup import Markup, esc
from .palette import DARK

Text = Union[str, dict]

SANS = "Tajawal, 'Segoe UI', Arial, sans-serif"
MONO = "'JetBrains Mono', Menlo, Consolas, monospace"

SOURCE_URL = 'https://github.com/github/innovationgraph'
LICENCE = 'CC0-1.0'
LICENCE_URL = 'https://creativecommons.org/publicdomain/zero/1.0/'


def loc(text: Optional[Text], lang: str) -> str:
    if text is None:
        return ''
    return text[lang] if isinstance(text, dict) else text


def both(text: Optional[Text]) -> dict:
    return {lang: loc(text, lang) for lang in ('en', 'ar')}


# ---------------------------------------------------------------- measuring and scales
def text_width(s: str, size: float, mono: bool = False, bold: bool = False) -> float:
    """Approximate advance width, for margins and label room (Tajawal and JetBrains Mono)."""
    if mono:
        return len(s) * 0.6 * size
    w = 0.0
    for ch in s:
        if '؀' <= ch <= 'ۿ':
            w += 0.5
        elif ch in ' \u2002':
            w += 0.27
        elif ch in 'il.,:;|!\'()':
            w += 0.27
        elif ch.isupper():
            w += 0.63
        elif ch.isdigit():
            w += 0.56
        else:
            w += 0.5
    return w * size * (1.06 if bold else 1)


def nice_ticks(lo: float, hi: float, n: int = 5) -> list:
    """Round tick values covering [lo, hi] with about ``n`` steps of 1, 2, 2.5 or 5 × 10^k."""
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if raw <= m * mag + 1e-12)
    start = math.floor(lo / step + 1e-9) * step
    end = math.ceil(hi / step - 1e-9) * step
    return [round(start + i * step, 12) for i in range(round((end - start) / step) + 1)]


def tick_decimals(step: float) -> int:
    d = max(0, -math.floor(math.log10(step) + 1e-9))
    while d < 6 and abs(step * 10 ** d - round(step * 10 ** d)) > 1e-9:
        d += 1
    return d


def place_labels(targets: Sequence[float], gap: float, lo: float, hi: float) -> list:
    """Positions for labels that want to sit at ``targets``: at least ``gap`` apart, in the
    same order, inside [lo, hi], each as near its target as the others allow (overlapping
    labels form a group centred on their targets' mean)."""
    n = len(targets)
    if not n:
        return []
    order = sorted(range(n), key=lambda i: (targets[i], i))
    groups = []                                   # [start, [indices]]
    for i in order:
        groups.append([targets[i], [i]])
        while len(groups) > 1:
            (s1, a), (s2, b) = groups[-2], groups[-1]
            if s2 >= s1 + len(a) * gap - 1e-9:
                break
            items = a + b
            mean = sum(targets[k] for k in items) / len(items)
            groups[-2:] = [[mean - (len(items) - 1) * gap / 2, items]]
    seq = [start + k * gap for start, items in groups for k in range(len(items))]
    seq[0] = max(seq[0], lo)
    for k in range(1, n):
        seq[k] = max(seq[k], seq[k - 1] + gap)
    seq[-1] = min(seq[-1], hi)
    for k in range(n - 2, -1, -1):
        seq[k] = min(seq[k], seq[k + 1] - gap)
    pos = [0.0] * n
    for k, i in enumerate(order):
        pos[i] = seq[k]
    return pos


# ---------------------------------------------------------------- tick and value formats
def tick_compact(v, lang, step):
    return '0' if v == 0 else fcompact(v, lang)


def tick_dec(v, lang, step):
    return '0' if v == 0 else fdec(v, tick_decimals(step), lang)


def tick_int(v, lang, step):
    return fint(v, lang)


def tick_pct(v, lang, step):
    return '0' if v == 0 else fpct(v, tick_decimals(step * 100), lang, sign=False)


# ---------------------------------------------------------------- SVG text
def _num(v: float) -> str:
    return f'{v:.1f}'.rstrip('0').rstrip('.') if v != int(v) else str(int(v))


def svg_text(x, y, s, *, size, fill, font=SANS, weight=None, align='left', cls='', extra='', inner=None) -> str:
    """One <text>. ``align`` is visual (left, right or center). Text with Arabic letters is
    set right to left, so its anchor flips; figures stay left to right."""
    rtl = has_arabic(s)
    anchor = {'center': 'middle', 'left': 'end' if rtl else 'start', 'right': 'start' if rtl else 'end'}[align]
    attrs = [f'x="{_num(x)}"', f'y="{_num(y)}"']
    if anchor != 'start':
        attrs.append(f'text-anchor="{anchor}"')
    if rtl:
        attrs.append('direction="rtl" unicode-bidi="embed"')
    if font != SANS:
        attrs.append(f'font-family="{font}"')
    attrs.append(f'font-size="{_num(size)}"')
    if weight:
        attrs.append(f'font-weight="{weight}"')
    attrs.append(f'fill="{fill}"')
    if cls:
        attrs.append(f'class="{cls}"')
    if extra:
        attrs.append(extra)
    return f'<text {" ".join(attrs)}>{inner if inner is not None else esc(s)}</text>'


def _value_span(value: str, size, fill, weight=None) -> str:
    """A figure inside a label: monospace and always left to right."""
    w = f' font-weight="{weight}"' if weight else ''
    return (f'<tspan font-family="{MONO}" font-size="{_num(size)}"{w} fill="{fill}" direction="ltr" '
            f'unicode-bidi="embed">{esc(value)}</tspan>')


def _path(points) -> str:
    out, pen = [], False
    for p in points:
        if p is None:
            pen = False
            continue
        out.append(f'{"L" if pen else "M"}{p[0]:.1f} {p[1]:.1f}')
        pen = True
    return ' '.join(out)


# ---------------------------------------------------------------- sparkline, rank strip, tiny bars
def spark(values: list, median: Optional[list] = None, w: int = 100, h: int = 34) -> Markup:
    """A sparkline that stretches to its box while strokes keep their width (decorative:
    the tile around it states the value, and the page's tables hold the series)."""
    vals = [v for v in values if v is not None] + [v for v in (median or []) if v is not None]
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.12 or 1
    lo, hi = lo - pad, hi + pad
    n = len(values)
    X = lambda i: i * w / (n - 1)
    Y = lambda v: h - (v - lo) / (hi - lo) * h
    pts = lambda vs: [(X(i), Y(v)) if v is not None else None for i, v in enumerate(vs)]
    out = []
    if median:
        out.append(f'<path class="sp-md" d="{_path(pts(median))}" vector-effect="non-scaling-stroke"/>')
    line = [p for p in pts(values) if p]
    out.append(f'<path class="sp-area" d="{_path(line)} L{w} {h} L0 {h} Z"/>')
    out.append(f'<path class="sp-ln" d="{_path(line)}" vector-effect="non-scaling-stroke"/>')
    lx, ly = line[-1]
    out.append(f'<path class="sp-end" d="M{lx:.2f} {ly:.2f} l0 0" vector-effect="non-scaling-stroke"/>')
    return Markup(f'<svg class="spark" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true" '
                  f'focusable="false">{"".join(out)}</svg>')


def rank_strip(rank: int, of: int, label: str, full: int = 29) -> Markup:
    """One cell per economy, Algeria's rank lit. Every strip uses the same 29-cell scale,
    so a rank of 7 and a rank of 29 compare at a glance. Mirrored in Arabic (rank 1 first)."""
    s, g = 8, 3
    width = full * (s + g) - g
    lit = ' class="on"'
    cells = ''.join(f'<rect x="{i * (s + g)}" width="{s}" height="{s}" rx="1.8"{lit if i + 1 == rank else ""}/>'
                    for i in range(of))
    return Markup(f'<svg class="rank-strip" viewBox="0 0 {width} {s}" role="img" aria-label="{esc(label)}">{cells}</svg>')


def hbars(items: Iterable, fmt: Callable, names: dict, highlight: str = 'DZ') -> Markup:
    """Peer comparison inside a tile, as HTML so labels stay crisp. ``items``: [(code, value)]."""
    items = list(items)
    top = max(v for _, v in items) or 1
    rows = []
    for code, v in items:
        on = ' class="on"' if code == highlight else ''
        rows.append(f'<div{on}><span class="hb-name">{esc(names.get(code, code))}</span>'
                    f'<span class="hb-track"><span class="hb-bar" style="inline-size: {v / top * 100:.1f}%"></span></span>'
                    f'<span class="hb-val num" dir="ltr">{esc(fmt(v))}</span></div>')
    return Markup(f'<div class="hbars">{"".join(rows)}</div>')


def last(values: Sequence[Optional[float]]) -> tuple:
    """(index, value) of the last value that isn't missing."""
    i = max(k for k, v in enumerate(values) if v is not None)
    return i, values[i]


# ---------------------------------------------------------------- chart specs
ROLES = ('peer', 'ref', 'median', 'hl', 'dz')     # drawing order: Algeria last, on top
LINE_STYLE = {   # role: (colour, wide width, narrow width, dash)
    'dz': ('algeria', 3.2, 2.6, None),
    'hl': ('highlight', 2.4, 2, None),
    'median': ('median', 1.6, 1.5, '5 5'),
    'ref': ('peer', 1.8, 1.6, None),
    'peer': ('peer', 1.4, 1.2, None),
}
TABLE_ORDER = {'dz': 0, 'median': 1, 'ref': 1, 'hl': 2, 'peer': 2}   # Algeria, medians, then peers as given
LABEL_STYLE = {  # role: (colour, weight)
    'dz': ('algeria', 800), 'hl': ('highlight', 700), 'median': ('ink2', 500), 'ref': ('ink3', 500), 'peer': ('ink3', 400),
}


@dataclass
class Line:
    key: str                       # 'DZ', 'median_north_africa'
    name: Text
    values: Sequence[Optional[float]]
    role: str = 'peer'             # dz, hl, peer, median or ref
    label: bool = True             # end label on the wide drawing


@dataclass
class Note:
    """An annotation pointing at one line's value in one quarter (wide drawing only)."""
    x: str                         # quarter id
    key: str                       # line key
    text: Text                     # lines separated by '\n'; the first is bold
    dx: float = 0
    dy: float = -60


@dataclass
class Spec:
    id: str                        # 'trends-accounts': file names and element ids
    quarter: str                   # data quarter, '2026-Q1'
    title: Text
    summary: Text                  # one or two sentences: what the chart shows
    unit: Text = ''
    source: Text = 'GitHub Innovation Graph'
    credit: Text = ''              # line printed under downloaded charts (set by the figure)

    @property
    def folder(self) -> str:
        y, q = parse_quarter(self.quarter)
        return f'{y}-q{q}'

    def meta(self) -> dict:
        y, q = parse_quarter(self.quarter)
        return {'id': self.id, 'title': both(self.title), 'unit': both(self.unit), 'quarter': f'{y}-Q{q}',
                'source': loc(self.source, 'en'), 'source_url': SOURCE_URL, 'licence': LICENCE, 'licence_url': LICENCE_URL,
                'attribution': 'Data: GitHub Innovation Graph (CC0) · djazair.dev'}


def _csv(rows: list) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\r\n')
    writer.writerows(rows)
    return buf.getvalue().encode('utf-8')


def _plain(v):
    """A value as written to CSV and JSON: integers stay integers, others keep 6 decimals."""
    if v is None:
        return None
    if float(v).is_integer():
        return int(v)
    return round(float(v), 6)


def _json(data: dict) -> bytes:
    return (json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8')


@dataclass
class LineChart(Spec):
    x: Sequence[str] = ()          # quarter ids, oldest first
    lines: Sequence[Line] = ()
    fmt: Callable = None           # (value, lang) -> str: labels and the data table
    tick_fmt: Callable = tick_dec  # (value, lang, step) -> str
    baseline: Optional[float] = None   # dashed reference line (100 on indexed charts)
    notes: Sequence[Note] = ()
    peers_label: Text = ''         # legend entry for the peer lines on phones

    def ordered(self) -> list:
        """Lines in reading order for tables and files: Algeria, the medians, then the peers."""
        return sorted(self.lines, key=lambda ln: TABLE_ORDER[ln.role])

    def csv(self) -> bytes:
        lines = self.ordered()
        rows = [['quarter'] + [ln.key for ln in lines]]
        for i, q in enumerate(self.x):
            y, n = parse_quarter(q)
            rows.append([f'{y}-Q{n}'] + ['' if ln.values[i] is None else _plain(ln.values[i]) for ln in lines])
        return _csv(rows)

    def json(self) -> bytes:
        quarters = ['{}-Q{}'.format(*parse_quarter(q)) for q in self.x]
        return _json({**self.meta(), 'x': quarters,
                      'series': [{'key': ln.key, 'name': both(ln.name), 'values': [_plain(v) for v in ln.values]}
                                 for ln in self.ordered()]})


@dataclass
class Bar:
    key: str
    label: Text
    value: float


@dataclass
class BarChart(Spec):
    bars: Sequence[Bar] = ()
    fmt: Callable = None           # (value, lang) -> str
    highlight: Optional[str] = None
    time: bool = True              # categories in time order stay left to right in Arabic
    mono_labels: bool = True       # years and codes in monospace

    def ordered(self, lang: str) -> list:
        return list(self.bars) if self.time or lang != 'ar' else list(reversed(self.bars))

    def csv(self) -> bytes:
        return _csv([['key', 'value']] + [[b.key, _plain(b.value)] for b in self.bars])

    def json(self) -> bytes:
        return _json({**self.meta(), 'bars': [{'key': b.key, 'label': both(b.label), 'value': _plain(b.value)} for b in self.bars]})


@dataclass
class HBar:
    key: str
    label: Text
    value: float
    before: Optional[float] = None     # the same measure a year earlier
    rank: Optional[int] = None
    estimate: bool = False             # djazair.dev's estimate beside published figures: an outline


@dataclass
class HBarChart(Spec):
    """Horizontal bars, largest first. Each bar is what it was a year earlier plus what it
    gained since, in the unit map's two greens; a loss shows as a dashed outline. The bars
    are categories, not time, so the Arabic drawing is mirrored: names on the right.

    With ``highlight``, only that bar is green and the others are grey, for economies side by
    side. ``change`` is a ratio (+12.5%), or with ``change_kind='diff'`` a difference (+1),
    which suits small counts.

    With ``split=False`` each bar is one green, and the year earlier shows only in the change
    and the table: for lists where a bar's year-earlier value can be unknown rather than
    zero. ``new_label`` then stands in for the change of a bar that has none ('new')."""
    bars: Sequence[HBar] = ()
    fmt: Callable = None               # (value, lang) -> str
    change_fmt: Callable = None        # (change, lang) -> str
    category_label: Text = ''          # first column of the table: 'Language'
    now_label: Text = ''               # 'Q1 2026'
    before_label: Text = ''            # 'Q1 2025'
    added_label: Text = ''             # 'Added since'
    change_label: Text = ''            # 'Change'
    highlight: Optional[str] = None    # the one bar drawn in green, others grey ('DZ')
    highlight_label: Text = ''         # its legend entry: 'Algeria'
    change_kind: str = 'ratio'         # ratio | diff
    split: bool = True                 # the year earlier and the gain since in two greens
    new_label: Text = ''               # in place of the change when there is no year-earlier value

    def change(self, b: HBar) -> Optional[float]:
        if b.before is None:
            return None
        if self.change_kind == 'diff':
            return b.value - b.before
        return b.value / b.before - 1 if b.before else None

    def csv(self) -> bytes:
        estimates = any(b.estimate for b in self.bars)        # a column only for charts that mix in an estimate
        rows = [[b.key, b.rank, _plain(b.value), _plain(b.before), _plain(self.change(b))]
                + (['true' if b.estimate else 'false'] if estimates else []) for b in self.bars]
        return _csv([['key', 'rank', 'value', 'year_earlier', 'change'] + (['estimate'] if estimates else [])] + rows)

    def json(self) -> bytes:
        estimates = any(b.estimate for b in self.bars)
        return _json({**self.meta(), 'bars': [{'key': b.key, 'label': both(b.label), 'rank': b.rank, 'value': _plain(b.value),
                                               'year_earlier': _plain(b.before), 'change': _plain(self.change(b)),
                                               **({'estimate': b.estimate} if estimates else {})}
                                              for b in self.bars]})


@dataclass
class UnitMap(Spec):
    total: int = 0                 # accounts now
    start: int = 0                 # accounts a year earlier
    per: int = 1000                # accounts per square
    start_label: Text = ''         # 'Q1 2025'
    added_label: Text = ''         # 'Added since'
    total_label: Text = ''         # 'Q1 2026'
    square_label: Text = ''        # 'One square = 1,000 accounts'

    @property
    def squares(self) -> tuple:
        """(squares in total, squares added): rounded so the drawing adds up."""
        total = round(self.total / self.per)
        added = min(total, max(0, round((self.total - self.start) / self.per)))
        return total, added

    def layout(self) -> unitmap.Layout:
        total, added = self.squares
        return unitmap.layout(total, added)

    def rows(self) -> list:
        total, added = self.squares
        return [('start', self.start_label, self.start, total - added), ('added', self.added_label, self.total - self.start, added),
                ('total', self.total_label, self.total, total)]

    def csv(self) -> bytes:
        return _csv([['series', 'accounts', 'squares']] + [[k, v, s] for k, _, v, s in self.rows()])

    def json(self) -> bytes:
        return _json({**self.meta(), 'accounts_per_square': self.per,
                      'rows': [{'key': k, 'label': both(lab), 'accounts': v, 'squares': s} for k, lab, v, s in self.rows()]})


# ---------------------------------------------------------------- drawings
@dataclass
class Drawing:
    """An SVG body (without the root element) and its size."""
    width: float
    height: float
    body: str
    cls: str = ''
    defs: str = ''


LINE_SIZES = {'wide': dict(W=1180, H=480, font=14, top=40, bottom=44, gap=14),
              'narrow': dict(W=340, H=300, font=12.5, top=30, bottom=32, gap=0)}


def x_years(x: Sequence[str], plot_w: float, font: float) -> list:
    """Indexes of the first quarters of the years to label: every year if they fit, else every other
    year counted back from the last, so the latest year is always labelled."""
    q1 = [i for i, q in enumerate(x) if parse_quarter(q)[1] == 1]
    if len(q1) < 2:
        return q1
    room = plot_w * (q1[1] - q1[0]) / max(len(x) - 1, 1)
    step = 1 if room >= text_width('2026', font, mono=True) * 1.9 else 2
    return [i for k, i in enumerate(reversed(q1)) if k % step == 0][::-1]


def line_layout(chart: LineChart, lang: str, size: str) -> dict:
    g = LINE_SIZES[size]
    W, H, font = g['W'], g['H'], g['font']
    vals = [v for ln in chart.lines for v in ln.values if v is not None]
    lo = min(0.0, min(vals))
    hi = max(vals + ([chart.baseline] if chart.baseline is not None else []))
    ticks = nice_ticks(lo, hi, 5 if size == 'wide' else 4)
    step = ticks[1] - ticks[0]
    tick_labels = [chart.tick_fmt(t, lang, step) for t in ticks]
    tsize = font - 1.5
    left = max(40.0, max(text_width(s, tsize, mono=not has_arabic(s)) for s in tick_labels) + 16)
    right = 12.0
    labelled = [ln for ln in chart.lines if ln.label]
    if size == 'wide' and labelled:
        right = max(text_width(loc(ln.name, lang), font + (1 if ln.role == 'dz' else 0), bold=ln.role in ('dz', 'hl'))
                    + text_width(chart.fmt(last(ln.values)[1], lang), tsize, mono=True) + 14 for ln in labelled) + g['gap'] + 6
    pw, ph = W - left - right, H - g['top'] - g['bottom']
    n = len(chart.x)
    X = lambda i: left + i * pw / max(n - 1, 1)
    Y = lambda v: g['top'] + ph - (v - ticks[0]) / (ticks[-1] - ticks[0]) * ph
    return dict(W=W, H=H, font=font, tsize=tsize, top=g['top'], left=left, right=right, pw=pw, ph=ph, ticks=ticks,
                tick_labels=tick_labels, X=X, Y=Y, gap=g['gap'])


def line_drawing(chart: LineChart, lang: str, size: str, pal: dict = DARK) -> Drawing:
    L = line_layout(chart, lang, size)
    W, H, font, tsize, top, left, ph = L['W'], L['H'], L['font'], L['tsize'], L['top'], L['left'], L['ph']
    X, Y = L['X'], L['Y']
    wide = size == 'wide'
    out = []
    unit = loc(chart.unit, lang)
    if unit:
        out.append(svg_text(0, top - 18, unit, size=font, fill=pal['ink3']))
    zero = f' stroke="{pal["axis"]}"'
    grid = ''.join(f'<path d="M{left:.1f} {Y(t):.1f} H{W - L["right"]:.1f}"{zero if t == 0 else ""}/>' for t in L['ticks'])
    years = x_years(chart.x, L['pw'], tsize)
    grid += ''.join(f'<path d="M{X(i):.1f} {top + ph:.1f} v6" stroke="{pal["tick"]}"/>' for i in years)
    out.append(f'<g stroke="{pal["grid"]}" stroke-width="1" fill="none">{grid}</g>')
    labels = [svg_text(left - 10, Y(t) + tsize * 0.34, s, size=tsize, fill=pal['ink3'], align='right',
                       font=SANS if has_arabic(s) else MONO) for t, s in zip(L['ticks'], L['tick_labels'])]
    labels += [svg_text(X(i), top + ph + (22 if wide else 20), str(parse_quarter(chart.x[i])[0]), size=tsize, fill=pal['ink3'],
                        align='center', font=MONO) for i in years]
    out.append(f'<g>{"".join(labels)}</g>')
    if chart.baseline is not None:
        out.append(f'<path d="M{left:.1f} {Y(chart.baseline):.1f} H{W - L["right"]:.1f}" stroke="{pal["tick"]}" '
                   f'stroke-width="1" stroke-dasharray="2 4" fill="none"/>')

    lines = sorted(chart.lines, key=lambda ln: ROLES.index(ln.role))
    for ln in lines:
        colour, w_wide, w_narrow, dash = LINE_STYLE[ln.role]
        d = _path([(X(i), Y(v)) if v is not None else None for i, v in enumerate(ln.values)])
        width = w_wide if wide else w_narrow
        draw = ln.role in ('dz', 'hl')
        cls = f'ln-{ln.role} k-{ln.key}' + (' ln' if draw else ' fd')
        extra = f' stroke-dasharray="{dash}"' if dash else ' pathLength="1"' if draw else ''
        out.append(f'<path class="{cls}" d="{d}" fill="none" stroke="{pal[colour]}" stroke-width="{_num(width)}" '
                   f'stroke-linejoin="round" stroke-linecap="round"{extra}/>')
    dz = next((ln for ln in chart.lines if ln.role == 'dz'), None)
    if dz is not None:
        i, v = last(dz.values)
        out.append(f'<circle class="ann end" cx="{X(i):.1f}" cy="{Y(v):.1f}" r="{5 if wide else 4}" '
                   f'fill="{pal["algeria"]}" stroke="{pal["paper"]}" stroke-width="2.5"/>')

    if wide:
        labelled = [ln for ln in lines if ln.label]
        ys = place_labels([Y(last(ln.values)[1]) for ln in labelled], font + 5, top, top + ph + 8)
        texts = []
        x0 = X(len(chart.x) - 1) + L['gap']
        for ln, y in zip(labelled, ys):
            colour, weight = LABEL_STYLE[ln.role]
            name = loc(ln.name, lang)
            value = chart.fmt(last(ln.values)[1], lang)
            inner = esc(name) + '\u2002' + _value_span(value, tsize, pal[colour], 600 if ln.role == 'dz' else None)
            texts.append(svg_text(x0, y + font * 0.36, name, size=font + (1 if ln.role == 'dz' else 0), fill=pal[colour],
                                  weight=weight, cls=f'lb k-{ln.key}', inner=inner))
        out.append(f'<g class="fd">{"".join(texts)}</g>')
        for note in chart.notes:
            out.append(_note(chart, note, lang, X, Y, font, pal))
    return Drawing(W, H, ''.join(out), cls='chart-line')


def _note(chart: LineChart, note: Note, lang: str, X, Y, font: float, pal: dict) -> str:
    i = list(chart.x).index(note.x)
    ln = next(ln for ln in chart.lines if ln.key == note.key)
    x, y = X(i), Y(ln.values[i])
    tx, ty = x + note.dx, y + note.dy
    lines = loc(note.text, lang).split('\n')
    lh = font + 7
    first = ty - (len(lines) - 1) * lh if note.dy < 0 else ty + font
    lead_to = ty + 10 if note.dy < 0 else first - font - 4
    out = [f'<path d="M{x:.1f} {y + (9 if note.dy > 0 else -9):.1f} L{tx:.1f} {lead_to:.1f}" stroke="{pal["ink3"]}" stroke-width="1"/>',
           f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{pal["paper"]}" stroke="{pal["ink"]}" stroke-width="1.6"/>']
    for k, text in enumerate(lines):
        out.append(svg_text(tx, first + k * lh, text, size=font + (1 if k == 0 else 0), fill=pal['ink'] if k == 0 else pal['ink2'],
                            weight=700 if k == 0 else None, align='center'))
    return f'<g class="ann">{"".join(out)}</g>'


BAR_SIZES = {'wide': dict(W=560, H=280, font=15), 'narrow': dict(W=330, H=230, font=13)}


def bar_drawing(chart: BarChart, lang: str, size: str, pal: dict = DARK) -> Drawing:
    g = BAR_SIZES[size]
    W, H, font = g['W'], g['H'], g['font']
    top, bottom, side = 30, 34, 8
    bars = chart.ordered(lang)
    lo = min(0.0, min(b.value for b in bars))
    hi = max(0.0, max(b.value for b in bars))
    span = (hi - lo) or 1
    ph = H - top - bottom
    Y = lambda v: top + (hi - v) / span * ph
    bw = (W - 2 * side) / len(bars)
    out = []
    for i, b in enumerate(bars):
        on = b.key == chart.highlight
        x = side + i * bw + bw * 0.18
        y0, y1 = sorted((Y(0), Y(b.value)))
        fill = pal['algeria'] if on else pal['bar']
        out.append(f'<rect class="br{" on" if on else ""}" x="{x:.1f}" y="{y0:.1f}" width="{bw * 0.64:.1f}" '
                   f'height="{max(y1 - y0, 0.5):.1f}" rx="3" fill="{fill}"/>')
        value = chart.fmt(b.value, lang)
        vy = y0 - 9 if b.value >= 0 else y1 + font + 2
        out.append(svg_text(x + bw * 0.32, vy, value, size=font - 1, fill=pal['ink'] if on else pal['ink2'], font=MONO,
                            weight=700 if on else 500, align='center'))
        label = loc(b.label, lang)
        out.append(svg_text(x + bw * 0.32, H - 10, label, size=font - 1, fill=pal['ink3'], align='center',
                            font=MONO if chart.mono_labels and not has_arabic(label) else SANS))
    out.insert(0, f'<path d="M{side} {Y(0):.1f} H{W - side}" stroke="{pal["axis"]}" stroke-width="1"/>')
    return Drawing(W, H, ''.join(out), cls='chart-bar')


HBAR_SIZES = {'wide': dict(W=1180, font=14, row=40, bar=18, label=190, value=200),
              'narrow': dict(W=340, font=12.5, row=50, bar=12, label=0, value=124)}


def hbar_drawing(chart: HBarChart, lang: str, size: str, pal: dict = DARK) -> Drawing:
    """Wide: name, bar, then value and change on one row. Narrow: the name sits above its bar.
    Distances run from the reading start, so Arabic mirrors by placing them from the right."""
    g = HBAR_SIZES[size]
    W, font, row, bh = g['W'], g['font'], g['row'], g['bar']
    rtl = lang == 'ar'
    narrow = size == 'narrow'
    hi = max(max(b.value, (b.before or 0) if chart.split else 0) for b in chart.bars) or 1
    x0 = 0 if narrow else g['label'] + 14
    span = W - x0 - g['value']
    D = lambda v: x0 + v / hi * span                   # value -> distance from the reading start
    X = lambda d: W - d if rtl else d                  # distance -> x
    near, far = ('right', 'left') if rtl else ('left', 'right')

    def rect(d1, d2, y, extra) -> str:
        return f'<rect x="{X(d2) if rtl else d1:.1f}" y="{y:.1f}" width="{max(d2 - d1, 0.5):.1f}" height="{bh}" {extra}/>'

    out = []
    for i, b in enumerate(chart.bars):
        y = 4 + i * row
        if narrow:
            name_y, bar_y = y + font, y + font + 9
        else:
            bar_y = y + (row - bh) / 2
            name_y = bar_y + bh / 2 + font * 0.36
        value_y = bar_y + bh / 2 + (font - 1) * 0.36
        name = loc(b.label, lang)
        grey = bool(chart.highlight) and b.key != chart.highlight          # a peer beside the highlighted bar
        lit = bool(chart.highlight) and b.key == chart.highlight
        if b.rank is not None:
            out.append(svg_text(X(0), name_y, str(b.rank), size=font - 1.5, fill=pal['ink3'], font=MONO, align=near, cls='fd'))
        out.append(svg_text(X(26 if b.rank is not None else 0), name_y, name, size=font, fill=pal['algeria'] if lit else pal['ink'],
                            weight=700 if lit else 500, align=near, cls='fd'))
        before = (b.before or 0) if chart.split and not b.estimate else 0
        kept = min(before, b.value)
        old, new = ('peer_dim', 'peer') if grey else ('cell_old', 'algeria')
        if b.estimate:
            out.append(rect(x0, D(b.value), bar_y + 0.75, f'rx="2" fill="{pal["algeria_fill"]}" stroke="{pal[new]}" '
                            f'stroke-width="1.5" stroke-dasharray="4 3" class="hb-e gr"').replace(f'height="{bh}"', f'height="{bh - 1.5}"'))
        else:
            if kept:
                out.append(rect(x0, D(kept), bar_y, f'rx="2" fill="{pal[old]}" class="hb-o fd"'))
            if b.value > before:
                out.append(rect(D(kept), D(b.value), bar_y, f'rx="2" fill="{pal[new]}" class="hb-n gr"'))
            elif b.value < before:
                out.append(rect(D(b.value), D(before), bar_y + 0.5,
                                f'rx="2" fill="none" stroke="{pal["negative"]}" stroke-dasharray="3 3" class="hb-l fd"')
                           .replace(f'height="{bh}"', f'height="{bh - 1}"'))
        d = D(max(b.value, before)) + 10
        value = chart.fmt(b.value, lang)
        out.append(svg_text(X(d), value_y, value, size=font - 1, fill=pal['ink'], font=MONO, weight=600, align=near, cls='ann'))
        change = chart.change(b)
        if change is not None:
            d += text_width(value, font - 1, mono=True) + 10
            colour = pal['negative'] if change < 0 else pal['ink3'] if grey else pal['algeria']
            out.append(svg_text(X(d), value_y, chart.change_fmt(change, lang), size=font - 1.5, font=MONO, align=near,
                                fill=colour, cls='ann'))
        elif b.before is None and chart.new_label:
            d += text_width(value, font - 1, mono=True) + 10
            out.append(svg_text(X(d), value_y, loc(chart.new_label, lang), size=font - 1.5, align=near, fill=pal['ink3'],
                                cls='ann'))
    H = 8 + len(chart.bars) * row
    return Drawing(W, H, ''.join(out), cls=f'chart-hbar{" rtl" if rtl else ""}')


def unit_drawing(chart: UnitMap, lang: str, size: str = 'wide', pal: dict = DARK, uid: str = 'um', texture: bool = True) -> Drawing:
    m = chart.layout()
    pad = 6
    W, H = m.width + 2 * pad, m.height + 2 * pad
    p = m.pitch
    s = p * 0.8
    o = (p - s) / 2
    old, new = {}, {}
    for c in m.cells:
        band = min(11, int(c.t * 12))
        (new if c.new else old).setdefault(band, []).append(
            f'<rect x="{c.x + o:.1f}" y="{c.y + o:.1f}" width="{s:.1f}" height="{s:.1f}" rx="{s * .2:.1f}"/>')
    cells = (f'<g fill="{pal["cell_old"]}">' + ''.join(f'<g class="o b{b}">{"".join(r)}</g>' for b, r in sorted(old.items())) + '</g>'
             + f'<g class="um-new" fill="{pal["algeria"]}">'
             + ''.join(f'<g class="n b{b}">{"".join(r)}</g>' for b, r in sorted(new.items())) + '</g>')
    defs, back = '', ''
    if texture:
        first = m.cells[0]
        defs = (f'<pattern id="{uid}-g" width="{p:.3f}" height="{p:.3f}" patternUnits="userSpaceOnUse" '
                f'x="{(first.x + pad) % p:.3f}" y="{(first.y + pad) % p:.3f}"><path d="M{p:.3f} 0 L0 0 0 {p:.3f}" fill="none" '
                f'stroke="{pal["grid"]}" stroke-width="1"/></pattern>'
                f'<radialGradient id="{uid}-f" cx="55%" cy="40%" r="62%"><stop offset="40%" stop-color="#fff"/>'
                f'<stop offset="100%" stop-color="#fff" stop-opacity="0"/></radialGradient>'
                f'<mask id="{uid}-m"><rect width="{W:.0f}" height="{H:.0f}" fill="url(#{uid}-f)"/></mask>')
        back = f'<rect width="{W:.0f}" height="{H:.0f}" fill="url(#{uid}-g)" mask="url(#{uid}-m)"/>'
    body = (back + f'<g transform="translate({pad} {pad})"><path d="{m.outline}" fill="{pal["map_fill"]}" stroke="{pal["map_line"]}" '
            f'stroke-width="1" stroke-linejoin="round"/>{cells}</g>')
    return Drawing(round(W, 1), round(H, 1), body, cls='um', defs=defs)


def drawing(chart: Spec, lang: str, size: str = 'wide', pal: dict = DARK, uid: str = 'c') -> Drawing:
    if isinstance(chart, LineChart):
        return line_drawing(chart, lang, size, pal)
    if isinstance(chart, BarChart):
        return bar_drawing(chart, lang, size, pal)
    if isinstance(chart, HBarChart):
        return hbar_drawing(chart, lang, size, pal)
    if isinstance(chart, UnitMap):
        return unit_drawing(chart, lang, size, pal, uid)
    raise TypeError(type(chart).__name__)


# ---------------------------------------------------------------- on the page and in files
def svg(chart: Spec, lang: str, size: str, uid: str, desc: str, cls: str = '') -> Markup:
    """The on-page SVG: an image with a title and a description, read left to right."""
    d = drawing(chart, lang, size, DARK, uid)
    defs = f'<defs>{d.defs}</defs>' if d.defs else ''
    classes = ' '.join(c for c in ('chart', d.cls, cls) if c)
    return Markup(f'<svg class="{classes}" viewBox="0 0 {_num(d.width)} {_num(d.height)}" role="img" '
                  f'aria-labelledby="{uid}-t {uid}-d" direction="ltr" font-family="{SANS}">'
                  f'<title id="{uid}-t">{esc(loc(chart.title, lang))}</title><desc id="{uid}-d">{esc(desc)}</desc>'
                  f'{defs}{d.body}</svg>')


def legend_items(chart: Spec, lang: str, pal: dict) -> list:
    """(swatch kind, colour, text) for downloads and the phone legend."""
    if isinstance(chart, UnitMap):
        total, added = chart.squares
        return [('square', pal['cell_old'], f'{loc(chart.start_label, lang)} {fint(total - added, lang)}'),
                ('square', pal['algeria'], f'{loc(chart.added_label, lang)} {fint(added, lang)}'),
                ('none', '', loc(chart.square_label, lang))]
    if isinstance(chart, HBarChart):
        if not chart.split:
            return []
        if chart.highlight:
            return [('square', pal['peer_dim'], loc(chart.before_label, lang)), ('square', pal['peer'], loc(chart.added_label, lang)),
                    ('square', pal['algeria'], loc(chart.highlight_label, lang))]
        return [('square', pal['cell_old'], loc(chart.before_label, lang)), ('square', pal['algeria'], loc(chart.added_label, lang))]
    return []


def download_svg(chart: Spec, lang: str, pal: dict) -> bytes:
    """A standalone SVG: the wide drawing on its own paper, with the title, a legend where the
    drawing needs one, and the credit line, so a chart pasted into a slide still credits its data."""
    d = drawing(chart, lang, 'wide', pal, uid=f'{chart.id}-dl')
    pad, head = 32, 52
    items = legend_items(chart, lang, pal)
    width = d.width + 2 * pad
    legend_h = 34 if items else 0
    height = pad + head + d.height + legend_h + 40 + pad - 16
    rtl = lang == 'ar'
    edge_l, edge_r = pad, width - pad
    title = svg_text(edge_r if rtl else edge_l, pad + 16, loc(chart.title, lang), size=20, fill=pal['ink'], weight=700,
                     align='right' if rtl else 'left')
    out = [f'<rect width="100%" height="100%" fill="{pal["paper"]}"/>', title,
           f'<g transform="translate({pad} {pad + head})">{d.body}</g>']
    y = pad + head + d.height + 26
    if items:
        x, sign = (edge_r, -1) if rtl else (edge_l, 1)     # cursor runs in the reading direction
        for kind, colour, text in items:
            if kind == 'square':
                out.append(f'<rect x="{x - 12 if rtl else x:.1f}" y="{y - 10:.1f}" width="12" height="12" rx="2.5" fill="{colour}"/>')
                x += sign * 18
            out.append(svg_text(x, y, text, size=13, fill=pal['ink2'], align='right' if rtl else 'left'))
            x += sign * (text_width(text, 13) + 24)
        y += legend_h
    out.append(svg_text(edge_r if rtl else edge_l, height - pad + 6, loc(chart.credit, lang), size=12, fill=pal['ink3'],
                        align='right' if rtl else 'left'))
    defs = f'<defs>{d.defs}</defs>' if d.defs else ''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{_num(width)}" height="{_num(height)}" '
            f'viewBox="0 0 {_num(width)} {_num(height)}" direction="ltr" font-family="{SANS}" xml:lang="{lang}">'
            f'<title>{esc(loc(chart.title, lang))}</title>{defs}{"".join(out)}</svg>\n').encode('utf-8')


def table(chart: Spec, lang: str, names: dict) -> tuple:
    """(head, rows) for ``components.data_table``: every value the chart draws.
    ``names``: interface strings for the first column ('quarter', 'series', 'value', ...)."""
    if isinstance(chart, LineChart):
        lines = chart.ordered()
        head = [(esc(names['quarter']), 'start')] + [(esc(loc(ln.name, lang)), 'end') for ln in lines]
        rows = []
        for i in range(len(chart.x) - 1, -1, -1):
            cells = [num(quarter_label(chart.x[i], lang, 'axis'))]
            for ln in lines:
                v = ln.values[i]
                cells.append(('—', None) if v is None else (num(chart.fmt(v, lang)), _plain(v)))
            rows.append((chart.x[i], cells))
        return head, rows
    if isinstance(chart, BarChart):
        head = [(esc(names['category']), 'start'), (esc(names['value']), 'end')]
        rows = [(b.key, [esc(loc(b.label, lang)), (num(chart.fmt(b.value, lang)), _plain(b.value))]) for b in chart.bars]
        return head, rows
    if isinstance(chart, HBarChart):
        head = [(esc(loc(chart.category_label, lang)), 'start'), (esc(loc(chart.now_label, lang)), 'end'),
                (esc(loc(chart.before_label, lang)), 'end'), (esc(loc(chart.change_label, lang)), 'end')]
        if all(b.before is None for b in chart.bars) and not chart.new_label:      # no year earlier to show
            return head[:2], [(b.key, [esc(loc(b.label, lang)), (num(chart.fmt(b.value, lang)), _plain(b.value))])
                              for b in chart.bars]
        rows = []
        for b in chart.bars:
            change = chart.change(b)
            if change is not None:
                change_cell = (num(chart.change_fmt(change, lang)), _plain(change))
            elif b.before is None and chart.new_label:
                change_cell = (esc(loc(chart.new_label, lang)), None)
            else:
                change_cell = ('—', None)
            rows.append((b.key, [esc(loc(b.label, lang)), (num(chart.fmt(b.value, lang)), _plain(b.value)),
                                 ('—', None) if b.before is None else (num(chart.fmt(b.before, lang)), _plain(b.before)),
                                 change_cell]))
        return head, rows
    if isinstance(chart, UnitMap):
        head = [(esc(names['series']), 'start'), (esc(names['accounts']), 'end'), (esc(names['squares']), 'end')]
        rows = [(k, [esc(loc(lab, lang)), (num(fint(v, lang)), v), (num(fint(sq, lang)), sq)]) for k, lab, v, sq in chart.rows()]
        return head, rows
    raise TypeError(type(chart).__name__)
