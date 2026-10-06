"""Number, quarter and date formatting for ``en`` and ``ar-DZ`` (PRD AC-IDX-6).

Numbers come out as ``Intl.NumberFormat`` would write them: ``en`` → ``586,990.5``,
``ar-DZ`` → ``586.990,5`` with Western digits. Negative values use the minus sign
U+2212. In Arabic text, wrap every number in ``num()`` so its sign and per cent stay
in place: the span is ``dir="ltr"``, which isolates it from the surrounding text.
"""
from __future__ import annotations

import datetime as _dt
import re

from .markup import Markup, esc

MINUS = '−'

AR_MONTHS = ['جانفي', 'فيفري', 'مارس', 'أفريل', 'ماي', 'جوان', 'جويلية', 'أوت', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']
EN_MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
             'November', 'December']
AR_QUARTERS = {1: 'الأول', 2: 'الثاني', 3: 'الثالث', 4: 'الرابع'}

_ARABIC = re.compile('[؀-ۿ]')


def _local(s: str, lang: str) -> str:
    """'1,234.5' → '1.234,5' for Arabic (ar-DZ)."""
    if lang != 'ar':
        return s
    return s.translate(str.maketrans({',': '.', '.': ','}))


def _signed(body: str, negative: bool, sign: bool) -> str:
    if negative:
        return MINUS + body
    return ('+' + body) if sign else body


def fint(n, lang: str = 'en', sign: bool = False) -> str:
    """Integer with grouping: 586,990 / 586.990."""
    r = round(n)
    return _signed(_local(f'{abs(r):,}', lang), r < 0, sign and r != 0)


def fdec(x, digits: int, lang: str = 'en', sign: bool = False) -> str:
    """Fixed decimals with grouping: 586,990.5 / 586.990,5."""
    body = f'{abs(x):,.{digits}f}'
    negative = x < 0 and float(body.replace(',', '')) != 0
    return _signed(_local(body, lang), negative, sign and float(body.replace(',', '')) != 0)


def fpct(x, digits: int = 1, lang: str = 'en', sign: bool = True) -> str:
    """A fraction as a percentage: 0.491 → +49.1% / +49,1%."""
    body = f'{abs(x) * 100:,.{digits}f}'
    zero = float(body.replace(',', '')) == 0
    return _signed(_local(body, lang), x < 0 and not zero, sign and not zero) + '%'


def fnum(x, digits: int, lang: str = 'en') -> str:
    """``fint`` for 0 digits, otherwise ``fdec``."""
    return fint(x, lang) if digits == 0 else fdec(x, digits, lang)


def fcompact(n, lang: str = 'en') -> str:
    """Axis labels: 500k, 1.5M (en); 500 ألف, 1,5 مليون (ar)."""
    a = abs(n)
    if a >= 1_000_000:
        body = f'{a / 1_000_000:.1f}'.rstrip('0').rstrip('.')
        out = f'{_local(body, lang)}M' if lang == 'en' else f'{_local(body, lang)} مليون'
    elif a >= 1_000:
        body = f'{a / 1_000:.1f}'.rstrip('0').rstrip('.')
        out = f'{_local(body, lang)}k' if lang == 'en' else f'{_local(body, lang)} ألف'
    else:
        out = fint(a, lang)
    return (MINUS + out) if n < 0 else out


def ordinal(n: int) -> str:
    """English ordinal: 1st, 2nd, 3rd, 11th, 22nd."""
    suffix = 'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f'{n}{suffix}'


def rank_text(rank: int, of: int, lang: str = 'en') -> str:
    """'3rd of 7' / '3 من 7'."""
    return f'{ordinal(rank)} of {of}' if lang == 'en' else f'{rank} من {of}'


def parse_quarter(q: str):
    """'2026-Q1', '2026Q1' or '2026 Q1' → (2026, 1)."""
    m = re.fullmatch(r'(\d{4})\s*-?\s*Q([1-4])', q.strip())
    if not m:
        raise ValueError(f'not a quarter: {q!r}')
    return int(m.group(1)), int(m.group(2))


def quarter_label(q: str, lang: str = 'en', style: str = 'text') -> str:
    """Quarter labels.

    ``text``: 'Q1 2026' / 'الربع الأول 2026'. ``short``: 'Q1 2026' / 'الربع 1 · 2026'.
    ``axis``: '2026 Q1' (sorts as text; used in tables and chart readouts, both languages).
    """
    year, n = parse_quarter(q)
    if style == 'axis':
        return f'{year} Q{n}'
    if lang == 'en':
        return f'Q{n} {year}'
    return f'الربع {AR_QUARTERS[n]} {year}' if style == 'text' else f'الربع {n} · {year}'


def date_label(d, lang: str = 'en', short: bool = False) -> str:
    """Gregorian dates: '7 July 2026' / '7 جويلية 2026' (Algerian month names)."""
    if isinstance(d, str):
        d = _dt.date.fromisoformat(d[:10])
    if lang == 'ar':
        return f'{d.day} {AR_MONTHS[d.month - 1]} {d.year}'
    month = EN_MONTHS[d.month - 1]
    return f'{d.day} {month[:3] if short else month} {d.year}'


def has_arabic(text) -> bool:
    return bool(_ARABIC.search(str(text)))


def num(value, cls: str = 'num') -> Markup:
    """A figure for running text: mono, tabular and isolated from the text around it.

    Pure figures are isolated left to right, so '+49,1%' keeps its sign on the left in
    Arabic. Text with Arabic words ('3 من 7') keeps the sans face, so its spaces aren't
    monospaced, and reads right to left.
    """
    text = str(value)
    if has_arabic(text):
        return Markup(f'<span class="{cls} nums" dir="rtl">{esc(text)}</span>')
    return Markup(f'<span class="{cls}" dir="ltr">{esc(text)}</span>')
