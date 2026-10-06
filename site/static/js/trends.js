/* djazair.dev Trends: the crosshair readout, and peer chips that clear when pressed again.
   The page works without this file: radio buttons and CSS switch the views. */
(function () {
  'use strict';

  var root = document.getElementById('trends');
  var source = document.getElementById('trends-data');
  if (!root || !source) return;
  var data = JSON.parse(source.textContent);
  var last = data.q.length - 1;
  var state = { i: last, act: false };
  var wide = root.querySelector('.cw-w');
  var narrow = root.querySelector('.cw-n');
  var tip = wide.querySelector('.tip');
  var live = document.getElementById('tr-live');
  var none = document.getElementById('tr-hl-none');
  var comma = document.documentElement.lang === 'ar' ? '، ' : ', ';

  function checked(name) {
    var el = root.querySelector('input[name="' + name + '"]:checked');
    return el ? el.value : null;
  }

  function current() {
    var ind = checked('tr-ind') || 'accounts';
    var scale = checked('tr-scale') || 'actual';
    return { ind: ind, scale: scale, hl: checked('tr-hl') || 'none', v: data.views[ind + '-' + scale] };
  }

  function percent(n) { return n + '%'; }

  // Crosshair and dots for one drawing; returns the crosshair's place across it (0 to 1).
  function place(cw, size, c) {
    var g = c.v[size].g;            // [width, height, plot top, plot height, plot left, step]
    var x = g[4] + state.i * g[5];
    var left = percent(x / g[0] * 100);
    var xh = cw.querySelector('.xh');
    xh.style.left = left;
    xh.style.top = percent(g[2] / g[1] * 100);
    xh.style.height = percent(g[3] / g[1] * 100);
    [['.tdot-dz', 'DZ'], ['.tdot-hl', c.hl]].forEach(function (d) {
      var dot = cw.querySelector(d[0]);
      var ys = c.v[size].y[d[1]];
      var y = ys ? ys[state.i] : null;
      dot.hidden = y === null || y === undefined;
      if (!dot.hidden) {
        dot.style.left = left;
        dot.style.top = percent(y / g[1] * 100);
      }
    });
    return x / g[0];
  }

  function fill(box, c) {
    Array.prototype.forEach.call(box.querySelectorAll('[data-s]'), function (row) {
      row.querySelector('.ro-v').textContent = c.v.t[row.getAttribute('data-s')][state.i];
    });
  }

  function render() {
    var c = current();
    root.setAttribute('data-ind', c.ind);
    root.setAttribute('data-scale', c.scale);
    root.setAttribute('data-hl', c.hl);
    var across = place(wide, 'w', c);
    place(narrow, 'n', c);
    tip.querySelector('.tip-q').textContent = data.q[state.i];
    fill(tip, c);
    tip.style.left = percent(across * 100);
    tip.classList.toggle('tip-flip', across > 0.58);
    var rows = root.querySelector('.ro-rows.i-' + c.ind + '.s-' + c.scale);
    if (rows) fill(rows, c);
    root.querySelector('.ro-q').textContent = data.q[state.i];
    wide.setAttribute('data-act', state.act ? 'true' : 'false');
  }

  function announce() {
    var c = current();
    var parts = [data.names.DZ + ' ' + c.v.t.DZ[state.i], data.names.median_north_africa + ' ' + c.v.t.median_north_africa[state.i]];
    if (c.hl !== 'none') parts.push(data.names[c.hl] + ' ' + c.v.t[c.hl][state.i]);
    live.textContent = data.q[state.i] + ': ' + parts.join(comma);
  }

  function indexAt(e, cw, size) {
    var g = current().v[size].g;
    var r = cw.getBoundingClientRect();
    var x = (e.clientX - r.left) / r.width * g[0];
    return Math.max(0, Math.min(last, Math.round((x - g[4]) / g[5])));
  }

  function moveTo(i, act) {
    if (i === state.i && act === state.act) return;
    state.i = i;
    state.act = act;
    render();
  }

  // Wide chart: pointer, and the keyboard once it has focus.
  wide.tabIndex = 0;
  wide.setAttribute('role', 'group');
  wide.setAttribute('aria-label', wide.getAttribute('data-label'));
  wide.addEventListener('pointermove', function (e) { moveTo(indexAt(e, wide, 'w'), true); });
  wide.addEventListener('pointerleave', function () {
    if (document.activeElement !== wide) moveTo(last, false);
  });
  wide.addEventListener('focus', function () { moveTo(state.i, true); announce(); });
  wide.addEventListener('blur', function () { moveTo(last, false); });
  wide.addEventListener('keydown', function (e) {
    var to = { ArrowLeft: state.i - 1, ArrowRight: state.i + 1, Home: 0, End: last }[e.key];
    if (to === undefined) return;
    e.preventDefault();
    moveTo(Math.max(0, Math.min(last, to)), true);
    announce();
  });

  // Phone chart: drag across it; the readout under it follows.
  narrow.setAttribute('data-act', 'true');
  var hint = root.querySelector('.ro-hint');
  if (hint) hint.hidden = false;
  function drag(e) { moveTo(indexAt(e, narrow, 'n'), state.act); }
  narrow.addEventListener('pointerdown', drag);
  narrow.addEventListener('pointermove', function (e) {
    if (e.pointerType !== 'mouse' || e.buttons) drag(e);
  });

  // Pressing the peer that is already brought forward puts it back.
  var hl = checked('tr-hl');
  Array.prototype.forEach.call(root.querySelectorAll('input.tr-hl'), function (input) {
    input.addEventListener('click', function () {
      if (input.value !== hl) return;
      none.checked = true;
      hl = 'none';
      render();
    });
  });
  root.addEventListener('change', function (e) {
    if (e.target.name === 'tr-hl') hl = e.target.value;
    render();
    if (state.act) announce();
  });

  render();
}());
