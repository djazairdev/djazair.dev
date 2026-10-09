/* Contribution matching and an optional saved Hub view. Only a relative filter URL
   is kept on this device; every issue and GET search remains usable without JavaScript. */
(function () {
  'use strict';
  var section = document.getElementById('contributions');
  var form = section && section.querySelector('form');
  var cards = section ? Array.from(section.querySelectorAll('.opportunity')) : [];
  var savedLinks = Array.from(document.querySelectorAll('[data-saved-hub]'));
  var saveButtons = Array.from(document.querySelectorAll('[data-save-view]'));
  var key = 'djazair-hub-view';
  var locale = document.documentElement.lang === 'ar' ? 'ar' : 'en';
  var destination = '/' + locale + '/hub/';
  var originalLabels = new Map();
  saveButtons.forEach(function (button) {
    originalLabels.set(button, button.textContent);
    button.hidden = false;
  });
  function savedView() {
    try {
      var raw = localStorage.getItem(key);
      if (!raw || !/^\/(en|ar)\/hub\/(?:\?|#|$)/.test(raw)) return null;
      var url = new URL(raw, location.origin);
      if (url.origin !== location.origin) return null;
      return destination + url.search + '#issues';
    } catch (_) { return null; }
  }
  function refreshSavedLinks() {
    var saved = savedView();
    savedLinks.forEach(function (link) { link.href = saved || destination + '#issues'; });
  }
  function currentView() {
    if (!form) return destination + location.search + '#issues';
    var params = new URLSearchParams();
    ['type', 'lang', 'q'].forEach(function (name) {
      var value = form.elements[name].value.trim();
      if (value) params.set(name, value);
    });
    return destination + (params.toString() ? '?' + params.toString() : '') + '#issues';
  }
  function fold(text) {
    return (text || '').normalize('NFKD').replace(/[\u0300-\u036f\u064b-\u065f\u0670]/g, '').toLowerCase();
  }
  function resetLabels() {
    var saved = savedView() === currentView();
    saveButtons.forEach(function (button) {
      button.textContent = saved ? button.dataset.saved : originalLabels.get(button);
    });
  }
  function apply() {
    var type = form.elements.type.value, lang = form.elements.lang.value;
    var words = fold(form.elements.q.value).split(/\s+/).filter(Boolean);
    var shown = 0;
    cards.forEach(function (card) {
      var match = (!type || type === card.dataset.type) && (!lang || lang === card.dataset.lang) &&
        words.every(function (word) { return fold(card.textContent).indexOf(word) >= 0; });
      card.hidden = !match;
      if (match) shown++;
    });
    var count = section.querySelector('[data-count]');
    count.textContent = count.dataset.count.replace('{n}', String(shown));
    section.querySelector('.opportunity-empty').hidden = shown > 0;
    section.querySelector('[data-matching-hub]').href = currentView();
    resetLabels();
  }
  if (form && cards.length) {
    // A saved view is opt-in; otherwise start with the complete selection.
    var saved = savedView();
    var params = new URLSearchParams(saved ? new URL(saved, location.origin).search : '');
    ['type', 'lang', 'q'].forEach(function (name) {
      if (params.has(name)) form.elements[name].value = params.get(name);
      if (!form.elements[name].value) form.elements[name].value = '';
    });
    form.addEventListener('change', apply);
    var timer;
    form.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(apply, 180); });
    apply();
  }
  saveButtons.forEach(function (button) {
    button.addEventListener('click', function () {
      try {
        localStorage.setItem(key, currentView());
        button.textContent = button.dataset.saved;
        refreshSavedLinks();
      } catch (_) { button.textContent = button.dataset.error; }
    });
  });
  var feed = document.getElementById('issues');
  if (feed) {
    feed.addEventListener('change', resetLabels);
    feed.addEventListener('input', resetLabels);
    var clear = feed.querySelector('.hp-clear');
    if (clear) clear.addEventListener('click', resetLabels);
  }
  refreshSavedLinks();
})();
