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

  // A download or embed menu opens towards the side with room. Its button can sit at either end
  // of a line (a long source line wraps it to the start), and on phones the menu must stay on
  // screen. Its place is worked out before it moves: tried past the left edge of a right-to-left
  // page (or the right edge of a left-to-right one), it would scroll the whole page sideways.
  doc.addEventListener('toggle', function (e) {
    var d = e.target;
    if (!d.matches || !d.matches('details.dl') || !d.open) return;
    var m = d.querySelector('.dl-menu');
    var vw = doc.documentElement.clientWidth;
    var a = d.getBoundingClientRect();
    var w = m.offsetWidth;
    var rtl = getComputedStyle(d).direction === 'rtl';
    var end = rtl ? a.left : a.right - w;           // left edge when it hangs from the button's end (the default)
    var start = rtl ? a.right - w : a.left;         // and from its start (dl-flip)
    var over = function (left) { return Math.max(0, 8 - left) + Math.max(0, left + w - (vw - 8)); };
    var flip = over(start) < over(end);
    var left = flip ? start : end;
    var shift = Math.max(0, 8 - left) - Math.max(0, left + w - (vw - 8));
    m.classList.toggle('dl-flip', flip);
    m.style.translate = shift ? shift + 'px 0' : '';
  }, true);

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
  // data-v="" marks a missing figure: it sorts last whichever way the column runs.
  function sortKey(cell) {
    var v = cell.getAttribute('data-v');
    if (v === '') return null;
    if (v === null) return cell.textContent.trim();
    var n = Number(v);
    return isNaN(n) ? v : n;
  }
  doc.querySelectorAll('table[data-sortable]').forEach(function (table) {
    var heads = table.querySelectorAll('thead th[data-sort]');
    var status = table.parentNode.querySelector('.sort-status');
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
        var keys = rows.map(function (row) { return sortKey(row.cells[i]); });
        var numeric = keys.some(function (k) { return typeof k === 'number'; });
        // Numbers sort largest first, names A to Z; pressing again reverses.
        var current = th.getAttribute('aria-sort');
        var dir = current ? (current === 'descending' ? 'ascending' : 'descending') : (numeric ? 'descending' : 'ascending');
        heads.forEach(function (h) { h.removeAttribute('aria-sort'); });
        th.setAttribute('aria-sort', dir);
        rows.map(function (row, n) { return { row: row, key: keys[n], n: n }; }).sort(function (a, z) {
          if (a.key === null || z.key === null) return (a.key === null) - (z.key === null) || a.n - z.n;
          var c = (typeof a.key === 'number' && typeof z.key === 'number') ? a.key - z.key : String(a.key).localeCompare(String(z.key), lang);
          return (dir === 'ascending' ? c : -c) || a.n - z.n;
        }).forEach(function (x) { body.appendChild(x.row); });
        if (status) {
          var msg = status.getAttribute('data-' + (numeric ? (dir === 'descending' ? 'desc' : 'asc') : (dir === 'ascending' ? 'az' : 'za')));
          status.textContent = msg.replace('{col}', b.textContent.trim());
        }
      });
    });
  });

  // Charts below the fold draw in when they arrive, where CSS can't tie drawing to scrolling.
  var scrollDriven = window.CSS && CSS.supports && CSS.supports('animation-timeline: view()');
  var still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!scrollDriven && !still && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        en.target.classList.remove('draw-wait');
        en.target.classList.add('draw-go');
        io.unobserve(en.target);
      });
    }, { threshold: 0.3 });
    // Trends views (svg.v) draw each time they're shown, in CSS.
    doc.querySelectorAll('svg.chart:not(.v)').forEach(function (svg) {
      if (svg.getBoundingClientRect().top > window.innerHeight) {
        svg.classList.add('draw-wait');
        io.observe(svg);
      }
    });
  }

  // Home's hero replays the years in a loop (pages/home.py); it rests while it's out of sight.
  var hero = doc.querySelector('.hero-pause');
  hero = hero && hero.closest('.hero');
  if (hero && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      hero.classList.toggle('hero-idle', !entries[entries.length - 1].isIntersecting);
    }).observe(hero);
  }

  // PNG downloads: drawn here from the chart's SVG file, with the site's fonts embedded so
  // the text looks as it does on the page. Without JavaScript these menu items stay hidden.
  var canPng = window.fetch && window.Promise && window.FileReader && window.URL && HTMLCanvasElement.prototype.toBlob;
  if (canPng) {
    doc.querySelectorAll('li[data-png]').forEach(function (li) { li.hidden = false; });
  }
  var fontCss = null;
  function inlineFonts() {
    if (fontCss) return fontCss;
    var rules = [];
    Array.prototype.forEach.call(doc.styleSheets, function (sheet) {
      try {
        Array.prototype.forEach.call(sheet.cssRules, function (r) {
          if (window.CSSFontFaceRule && r instanceof CSSFontFaceRule) rules.push(r.cssText);
        });
      } catch (err) { /* another origin's stylesheet */ }
    });
    fontCss = Promise.all(rules.map(function (css) {
      var m = css.match(/url\("?([^")]+)"?\)/);
      if (!m) return css;
      return fetch(m[1]).then(function (r) { return r.blob(); }).then(function (blob) {
        return new Promise(function (resolve) {
          var reader = new FileReader();
          reader.onload = function () { resolve(css.replace(m[0], 'url("' + reader.result + '")')); };
          reader.onerror = function () { resolve(''); };
          reader.readAsDataURL(blob);
        });
      });
    })).then(function (list) { return list.join('\n'); });
    return fontCss;
  }
  function save(blob, name) {
    var link = doc.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = name;
    doc.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(function () { URL.revokeObjectURL(link.href); }, 4000);
  }
  doc.addEventListener('click', function (e) {
    var a = canPng && e.target.closest && e.target.closest('a[data-png]');
    if (!a) return;
    e.preventDefault();
    var menu = a.closest('details');
    if (menu) menu.open = false;
    Promise.all([fetch(a.href).then(function (r) { return r.text(); }), inlineFonts()]).then(function (res) {
      var svg = res[0].replace(/(<svg[^>]*>)/, '$1<style>' + res[1] + '</style>');
      var w = Number(svg.match(/width="([\d.]+)"/)[1]);
      var h = Number(svg.match(/height="([\d.]+)"/)[1]);
      var url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
      var img = new Image();
      img.onload = function () {
        // A beat for the embedded fonts, then draw at twice the size for sharp text.
        setTimeout(function () {
          var canvas = doc.createElement('canvas');
          canvas.width = Math.round(w * 2);
          canvas.height = Math.round(h * 2);
          var c = canvas.getContext('2d');
          c.scale(2, 2);
          c.drawImage(img, 0, 0, w, h);
          URL.revokeObjectURL(url);
          canvas.toBlob(function (blob) { if (blob) save(blob, a.getAttribute('download')); }, 'image/png');
        }, 60);
      };
      img.src = url;
    });
  });

  // Share (ticket #42): the phone's share sheet, or the chart's link copied. Without either,
  // the link just goes to the figure.
  doc.querySelectorAll('[data-share]').forEach(function (a) {
    if (!navigator.share && !navigator.clipboard) return;
    var label = a.querySelector('span');
    var text = label.textContent;
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var url = location.origin + location.pathname + a.getAttribute('href');
      if (navigator.share) {
        navigator.share({ title: doc.title, url: url }).catch(function () {});
        return;
      }
      navigator.clipboard.writeText(url).then(function () {
        label.textContent = a.getAttribute('data-copied') || text;
        setTimeout(function () { label.textContent = text; }, 1600);
      });
    });
  });

  // Embed panels: the dark or light switch rewrites the code and the preview link, and the
  // button copies the code. Without JavaScript the code is there to select, with a note.
  doc.querySelectorAll('.emb-panel').forEach(function (p) {
    var code = p.querySelector('.emb-code');
    var preview = p.querySelector('.emb-acts a');
    var base = preview.getAttribute('href');
    var src = code.value.match(/src="([^"]+)"/)[1];
    var ts = p.querySelector('.emb-ts');
    ts.hidden = false;
    p.querySelector('.emb-note').hidden = true;
    ts.addEventListener('change', function (e) {
      var end = e.target.value === 'light' ? 'light/' : '';     // the light page sits under the dark one
      code.value = code.value.replace(/src="[^"]+"/, 'src="' + src + end + '"');
      preview.setAttribute('href', base + end);
    });
    code.addEventListener('focus', function () { code.select(); });
  });
  doc.querySelectorAll('[data-copy-from]').forEach(function (b) {
    if (!navigator.clipboard) return;
    b.hidden = false;
    var label = b.textContent;
    b.addEventListener('click', function () {
      navigator.clipboard.writeText(doc.getElementById(b.getAttribute('data-copy-from')).value).then(function () {
        b.textContent = b.getAttribute('data-copied') || label;
        setTimeout(function () { b.textContent = label; }, 1600);
      });
    });
  });

  // Copy buttons on code samples.
  doc.querySelectorAll('[data-copy]').forEach(function (b) {
    if (!navigator.clipboard) return;
    b.hidden = false;
    var label = b.textContent;
    b.addEventListener('click', function () {
      var code = b.closest('.code, .cite').querySelector('.code-src, .cite-text');   // code samples and the citation
      navigator.clipboard.writeText(code.textContent).then(function () {
        b.textContent = b.getAttribute('data-copied') || label;
        setTimeout(function () { b.textContent = label; }, 1600);
      });
    });
  });
})();
