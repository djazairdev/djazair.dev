/* djazair.dev: small enhancements. Every page works without this file. */
(function () {
  'use strict';

  var doc = document;
  var lang = doc.documentElement.lang || 'en';

  // Remember the language the reader picks, so / sends them there next time.
  doc.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-lang]');
    if (!a) return;
    try { localStorage.setItem('djz-lang', a.getAttribute('data-lang')); } catch (err) { /* storage blocked */ }
  });

  // Phone menu (<details>): close it on Escape or a click outside.
  var menu = doc.querySelector('details.menu');
  if (menu) {
    doc.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.open) {
        menu.open = false;
        menu.querySelector('summary').focus();
      }
    });
    doc.addEventListener('click', function (e) {
      if (menu.open && !menu.contains(e.target)) menu.open = false;
    });
  }

  // Download menus: close on Escape or a click outside.
  doc.addEventListener('click', function (e) {
    doc.querySelectorAll('details.dl[open]').forEach(function (d) {
      if (!d.contains(e.target)) d.open = false;
    });
  });
  doc.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    doc.querySelectorAll('details.dl[open]').forEach(function (d) {
      d.open = false;
      d.querySelector('summary').focus();
    });
  });

  // Index sub-nav: on phones, bring the current section into view.
  var current = doc.querySelector('.subnav-row [aria-current]');
  if (current) {
    var a = current.getBoundingClientRect();
    var r = current.parentElement.getBoundingClientRect();
    if (a.left < r.left || a.right > r.right) current.scrollIntoView({ block: 'nearest', inline: 'center' });
  }

  // Chart controls: segmented controls and metric tabs pick one; a peer chip toggles.
  // Page scripts listen for the 'djz:change' event on the group.
  doc.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.seg button, .mts .mt, .pks .pk');
    if (!b) return;
    var group = b.parentElement;
    var value = b.getAttribute('data-value');
    if (b.classList.contains('pk')) {
      var wasOn = b.getAttribute('aria-pressed') === 'true';
      group.querySelectorAll('.pk').forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
      b.setAttribute('aria-pressed', wasOn ? 'false' : 'true');
      if (wasOn) value = '';
    } else {
      group.querySelectorAll('button').forEach(function (x) {
        x.setAttribute('aria-pressed', x === b ? 'true' : 'false');
      });
    }
    group.dispatchEvent(new CustomEvent('djz:change', { bubbles: true, detail: { value: value } }));
  });

  // Sortable tables: headers marked data-sort become buttons. Cells sort by data-v when present.
  var SORT_ICON = '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';
  function sortKey(cell) {
    var v = cell.getAttribute('data-v');
    if (v === null) return cell.textContent.trim();
    var n = Number(v);
    return isNaN(n) ? v : n;
  }
  doc.querySelectorAll('table[data-sortable]').forEach(function (table) {
    var heads = table.querySelectorAll('thead th[data-sort]');
    heads.forEach(function (th) {
      var b = doc.createElement('button');
      b.type = 'button';
      b.className = 'sort';
      b.innerHTML = th.innerHTML + SORT_ICON;
      th.textContent = '';
      th.appendChild(b);
      b.addEventListener('click', function () {
        var body = table.tBodies[0];
        var i = th.cellIndex;
        var rows = Array.prototype.slice.call(body.rows);
        // Numbers sort largest first, names A to Z; pressing again reverses.
        var current = th.getAttribute('aria-sort');
        var first = typeof sortKey(rows[0].cells[i]) === 'number' ? 'descending' : 'ascending';
        var dir = current ? (current === 'descending' ? 'ascending' : 'descending') : first;
        heads.forEach(function (h) { h.removeAttribute('aria-sort'); });
        th.setAttribute('aria-sort', dir);
        rows.sort(function (r1, r2) {
          var x = sortKey(r1.cells[i]), y = sortKey(r2.cells[i]);
          var c = (typeof x === 'number' && typeof y === 'number') ? x - y : String(x).localeCompare(String(y), lang);
          return dir === 'ascending' ? c : -c;
        });
        rows.forEach(function (row) { body.appendChild(row); });
      });
    });
  });

  // Copy buttons on code samples.
  doc.querySelectorAll('[data-copy]').forEach(function (b) {
    if (!navigator.clipboard) return;
    b.hidden = false;
    var label = b.textContent;
    b.addEventListener('click', function () {
      var code = b.closest('.code').querySelector('.code-src');
      navigator.clipboard.writeText(code.textContent).then(function () {
        b.textContent = b.getAttribute('data-copied') || label;
        setTimeout(function () { b.textContent = label; }, 1600);
      });
    });
  });
})();
