/* A one-time claw descends from the viewport edge and places the dot over Algeria’s i (or Arabic punctuation).
   Inspired by Jhey's Building Text with SVG: https://codepen.io/jh3y/pen/PwYRWRJ. */
(function () {
  'use strict';
  var heading = document.querySelector('#trend .section-head-text');
  if (!heading || !window.IntersectionObserver || !Element.prototype.animate) return;
  var motion = matchMedia('(prefers-reduced-motion: reduce)');
  var animations = new Set();
  var dot = heading.querySelector('.trend-letter') || heading.querySelector('.trend-dot');
  var letter = heading.querySelector('.trend-letter-ink');
  var claw = heading.querySelector('.trend-assembly');
  var frame = 0, cable = null;
  var ease = 'cubic-bezier(.22,1,.36,1)';
  if (dot && !motion.matches) heading.classList.add('trend-building');

  function finish() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    heading.classList.remove('trend-building');
    if (claw) claw.remove();
    if (cable) cable.remove();
    cable = null;
  }
  function rise(element, delay) {
    if (!element) return;
    var animation = element.animate([{ opacity: 0, transform: 'translateY(20px)' },
                                     { opacity: 1, transform: 'translateY(0)' }],
                                   { duration: 850, delay: delay, easing: ease, fill: 'backwards' });
    animations.add(animation);
    function done() { animations.delete(animation); }
    animation.finished.then(done, done);
  }
  function payload() {
    var style = getComputedStyle(dot);
    var rect = dot.getBoundingClientRect();
    var canvas = document.createElement('canvas');
    var context = canvas.getContext('2d');
    if (!context) return null;
    var font = style.fontWeight + ' ' + style.fontSize + ' ' + style.fontFamily;
    context.font = font;
    var metrics = context.measureText(letter ? 'i' : '.');
    var ascent = metrics.fontBoundingBoxAscent || parseFloat(style.fontSize) * .8;
    var descent = metrics.fontBoundingBoxDescent || parseFloat(style.fontSize) * .2;
    var baseline = (rect.height - ascent - descent) / 2 + ascent;
    if (letter) {
      // Isolate the font's actual dot, using the blank rows between it and the stem.
      // The live i remains the only text glyph; its dot is simply clipped until release.
      var scale = Math.max(2, Math.min(3, window.devicePixelRatio || 1));
      var padding = Math.ceil(parseFloat(style.fontSize) * .25) * scale;
      canvas.width = Math.ceil((rect.width + parseFloat(style.fontSize) * .2) * scale) + padding * 2;
      canvas.height = Math.ceil(rect.height * scale) + padding * 2;
      context.scale(scale, scale);
      context.font = font;
      context.fillStyle = style.color;
      context.fillText('i', padding / scale, baseline + padding / scale);
      var pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
      function inkAt(x, y) { return pixels[(y * canvas.width + x) * 4 + 3] > 8; }
      function rowHasInk(y) {
        for (var x = 0; x < canvas.width; x++) if (inkAt(x, y)) return true;
        return false;
      }
      var top = -1, bottom = -1, stem = -1;
      for (var y = 0; y < canvas.height; y++) {
        if (top < 0 && rowHasInk(y)) top = y;
        else if (top >= 0 && bottom < 0 && !rowHasInk(y)) bottom = y;
        else if (bottom >= 0 && rowHasInk(y)) { stem = y; break; }
      }
      if (top < 0 || bottom < 0 || stem - bottom < 1) return null;
      var left = canvas.width, right = 0;
      for (var row = top; row < bottom; row++) {
        for (var col = 0; col < canvas.width; col++) {
          if (inkAt(col, row)) { left = Math.min(left, col); right = Math.max(right, col); }
        }
      }
      if (left > right) return null;
      letter.style.setProperty('--trend-i-cut', ((bottom + stem - padding * 2) / (2 * scale)) + 'px');
      var cargo = document.createElement('canvas');
      cargo.width = right - left + 1;
      cargo.height = bottom - top;
      cargo.getContext('2d').drawImage(canvas, left, top, cargo.width, cargo.height,
                                     0, 0, cargo.width, cargo.height);
      var width = cargo.width / scale, height = cargo.height / scale;
      cargo.style.width = width + 'px';
      cargo.style.height = height + 'px';
      cargo.style.left = (32 - width / 2) + 'px';
      cargo.style.top = (48 - height / 2) + 'px';
      return { cargo: cargo, x: (left + cargo.width / 2 - padding) / scale, y: (top + cargo.height / 2 - padding) / scale };
    }
    var inkCenter = baseline - (metrics.actualBoundingBoxAscent - metrics.actualBoundingBoxDescent) / 2;
    var cargo = document.createElement('span');
    cargo.textContent = '.';
    cargo.style.fontFamily = style.fontFamily;
    cargo.style.fontWeight = style.fontWeight;
    cargo.style.fontSize = style.fontSize;
    cargo.style.lineHeight = rect.height + 'px';
    cargo.style.width = rect.width + 'px';
    cargo.style.left = (32 - rect.width / 2) + 'px';
    cargo.style.top = (48 - inkCenter) + 'px';
    return { cargo: cargo, x: rect.width / 2, y: inkCenter };
  }
  function deliver() {
    if (!dot || !claw) { finish(); return; }
    var data = payload();
    if (!data) { finish(); return; }
    var cargo = data.cargo;
    cargo.className = 'trend-carried-dot';
    claw.appendChild(cargo);
    document.body.appendChild(claw);
    claw.classList.add('trend-flying');
    cable = document.createElement('span');
    cable.className = 'trend-flight-cable';
    cable.setAttribute('aria-hidden', 'true');
    document.body.appendChild(cable);
    var grips = claw.querySelectorAll('.trend-grip');
    var start = performance.now(), dropped = false;
    function tick(now) {
      var elapsed = now - start;
      if (elapsed >= 2550 || motion.matches) { finish(); return; }
      var current = dot.getBoundingClientRect();
      var landing = current.top + data.y - 48;
      var y;
      if (elapsed < 1400) {
        var progress = elapsed / 1400;
        var eased = progress * progress * (3 - 2 * progress);
        y = -64 + (landing + 64) * eased;
      } else {
        if (!dropped) {
          dropped = true;
          heading.classList.remove('trend-building');
          cargo.style.visibility = 'hidden';
          grips.forEach(function (grip, index) { grip.style.transform = 'rotate(' + (index ? -22 : 22) + 'deg)'; });
        }
        var retreat = Math.max(0, (elapsed - 1700) / 850);
        y = landing + (-64 - landing) * retreat * retreat;
      }
      var x = current.left + data.x;
      claw.style.transform = 'translate3d(' + (x - 32) + 'px,' + y + 'px,0)';
      cable.style.left = x + 'px';
      cable.style.height = Math.max(0, y + 27) + 'px';
      frame = requestAnimationFrame(tick);
    }
    frame = requestAnimationFrame(tick);
  }
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      observer.unobserve(heading);
      heading.setAttribute('data-trend-revealed', 'true');
      if (motion.matches) { finish(); return; }
      rise(heading.querySelector('.eyebrow'), 0);
      rise(heading.querySelector('.trend-context') || heading.querySelector('h2'), 100);
      rise(heading.querySelector('.trend-highlight-text'), 150);
      rise(heading.querySelector('.lede'), 300);
      deliver();
    });
  }, { threshold: .25, rootMargin: '-64px 0px 0px' });
  motion.addEventListener('change', function () {
    if (!motion.matches) return;
    animations.forEach(function (animation) { animation.cancel(); });
    finish();
  });
  window.addEventListener('resize', function () { if (frame) finish(); });
  document.addEventListener('visibilitychange', function () { if (document.hidden && frame) finish(); });
  document.fonts.ready.then(function () {
    if (letter && !motion.matches && !payload()) finish();
    observer.observe(heading);
  });
}());
