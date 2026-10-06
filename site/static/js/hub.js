/* djazair.dev Hub: search, label tabs and the language, project and age filters, applied to
   the issue list in place. The page works without this file: the whole list shows. */
(function () {
  'use strict';

  var doc = document;
  var feed = doc.getElementById('issues');
  if (!feed) return;
  var tools = feed.querySelector('.hub-tools');
  var tabs = feed.querySelector('.hp-kind');
  var count = feed.querySelector('.hp-n');
  var clear = feed.querySelector('.hp-clear');
  var empty = feed.querySelector('.hp-empty');
  var search = doc.getElementById('hub-q');
  var details = feed.querySelector('details.hf');
  var state = feed.querySelector('.hf-state');
  var cards = Array.prototype.slice.call(feed.querySelectorAll('.hp-list .issue'));
  if (!tools || !count || !cards.length) return;

  var lang = doc.documentElement.lang || 'en';
  var rules = window.Intl && Intl.PluralRules ? new Intl.PluralRules(lang) : null;
  var names = ['lang', 'repo', 'age', 'kind'];
  var phone = window.matchMedia('(max-width: 960px)');

  function fold(text) {
    // Case, accents and Arabic diacritics don't matter when searching.
    return (text || '').normalize('NFKD').replace(/[̀-ًͯ-ٰٟ]/g, '').toLowerCase();
  }

  cards.forEach(function (card) {
    var main = card.querySelector('.ic-main');
    card._text = fold(main ? main.textContent : card.textContent);
  });

  function value(name) {
    var el = feed.querySelector('input[name="' + name + '"]:checked');
    return el ? el.value : '';
  }

  function pick(name, v) {
    var el = feed.querySelector('input[name="' + name + '"][value="' + (window.CSS && CSS.escape ? CSS.escape(v) : v) + '"]');
    if (el) el.checked = true;
    return !!el;
  }

  function counted(el, n) {
    var cat = rules ? rules.select(n) : (n === 1 ? 'one' : 'other');
    var form = el.getAttribute('data-' + cat) || el.getAttribute('data-other');
    // Figures as the site writes them: 1,234 in English, 1.234 in Arabic.
    return form.replace('{n}', String(n).replace(/\B(?=(\d{3})+(?!\d))/g, lang === 'ar' ? '.' : ','));
  }

  var timer = null;
  function apply(announce) {
    var f = { lang: value('lang'), repo: value('repo'), age: value('age'), kind: value('kind') };
    var words = fold(search.value).split(/\s+/).filter(Boolean);
    var shown = 0;
    cards.forEach(function (card) {
      var ok = (!f.lang || card.getAttribute('data-lang') === f.lang) &&
        (!f.repo || card.getAttribute('data-repo') === f.repo) &&
        (!f.age || Number(card.getAttribute('data-days')) <= Number(f.age)) &&
        (!f.kind || (' ' + card.getAttribute('data-kind') + ' ').indexOf(' ' + f.kind + ' ') >= 0) &&
        words.every(function (w) { return card._text.indexOf(w) >= 0; });
      card.hidden = !ok;
      if (ok) shown += 1;
    });
    var active = ['lang', 'repo', 'age'].filter(function (k) { return f[k]; }).length;
    var any = active > 0 || !!f.kind || words.length > 0;
    clear.hidden = !any;
    empty.hidden = shown > 0;
    if (state) {
      state.textContent = active ? state.getAttribute('data-some').replace('{n}', active) : state.getAttribute('data-none');
    }
    // The count is a live region: update it at once for clicks, after a pause for typing.
    clearTimeout(timer);
    var text = counted(count, shown);
    var say = function () { if (count.textContent !== text) count.textContent = text; };
    if (announce === 'later') timer = setTimeout(say, 450);
    else say();
    remember(f);
  }

  function remember(f) {
    if (!window.history || !history.replaceState) return;
    var params = new URLSearchParams();
    if (search.value.trim()) params.set('q', search.value.trim());
    names.forEach(function (k) { if (f[k]) params.set(k, f[k]); });
    var query = params.toString();
    history.replaceState(null, '', location.pathname + (query ? '?' + query : '') + location.hash);
  }

  function restore() {
    var params = new URLSearchParams(location.search);
    names.forEach(function (k) { if (params.has(k)) pick(k, params.get(k)); });
    if (params.has('q')) search.value = params.get('q');
  }

  function reset() {
    names.forEach(function (k) { pick(k, ''); });
    search.value = '';
    apply();
    search.focus();
  }

  function layout() {
    // A sidebar on wide screens; on phones the filters fold under "Filters".
    if (details) details.open = !phone.matches;
  }

  tools.hidden = false;
  if (tabs) tabs.hidden = false;
  layout();
  if (phone.addEventListener) phone.addEventListener('change', layout);
  restore();
  apply('now');

  feed.addEventListener('change', function (e) {
    if (e.target.name && names.indexOf(e.target.name) >= 0) apply();
  });
  search.addEventListener('input', function () { apply('later'); });
  search.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && search.value) { search.value = ''; apply(); }
  });
  clear.addEventListener('click', reset);

  // "6 open issues" on a project card shows that project's issues.
  doc.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a.pj-issues[data-repo]');
    if (!a || !pick('repo', a.getAttribute('data-repo'))) return;
    e.preventDefault();
    apply();
    feed.scrollIntoView({ behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    count.parentNode.setAttribute('tabindex', '-1');
    count.parentNode.focus({ preventScroll: true });
  });
})();
