/* One-time directional tile reveals and layered pointer parallax.
   Inspired by https://codepen.io/aptyyyp/pen/bGmyLMj and https://codepen.io/cathbailh/pen/KKGJpyV.
   Text and links are always present; all decorative motion respects reduced-motion preferences. */
(function () {
  'use strict';
  var section = document.querySelector('#hub-teaser');
  if (!section) return;
  var motion = matchMedia('(prefers-reduced-motion: reduce)');
  var pointer = matchMedia('(hover: hover) and (pointer: fine)');
  var cards = Array.from(section.querySelectorAll('.hub-path'));
  var animations = new Set();
  var resets = [];
  var ease = 'cubic-bezier(.22,1,.36,1)';
  function animate(element, frames, options) {
    var animation = element.animate(frames, options);
    animations.add(animation);
    function done() { animations.delete(animation); }
    animation.finished.then(done, done);
  }
  function rise(element, delay) {
    animate(element, [{ opacity: 0, transform: 'translateY(20px)' },
                      { opacity: 1, transform: 'translateY(0)' }],
            { duration: 750, delay: delay, easing: ease, fill: 'backwards' });
  }
  cards.forEach(function (card) {
    var frame = 0, box = null, point = null;
    function reset() {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      box = point = null;
      card.classList.remove('hub-parallax');
      ['rx', 'ry', 'x', 'y', 'fx', 'fy', 'bx', 'by', 'px', 'py'].forEach(function (key) {
        card.style.removeProperty('--hub-' + key);
      });
    }
    resets.push(reset);
    card.addEventListener('pointermove', function (event) {
      if (motion.matches || !pointer.matches || event.pointerType === 'touch' ||
          card.contains(document.activeElement)) return;
      box = box || card.getBoundingClientRect();
      point = [event.clientX, event.clientY];
      if (frame) return;
      frame = requestAnimationFrame(function () {
        frame = 0;
        var x = Math.max(0, Math.min(1, (point[0] - box.left) / box.width));
        var y = Math.max(0, Math.min(1, (point[1] - box.top) / box.height));
        function set(key, value, unit) { card.style.setProperty('--hub-' + key, value.toFixed(2) + unit); }
        set('rx', (.5 - y) * 5, 'deg');
        set('ry', (x - .5) * 5, 'deg');
        set('x', (x - .5) * 4, 'px');
        set('y', (y - .5) * 4, 'px');
        set('fx', (x - .5) * 10, 'px');
        set('fy', (y - .5) * 10, 'px');
        set('bx', (.5 - x) * 12, 'px');
        set('by', (.5 - y) * 12, 'px');
        set('px', x * 100, '%');
        set('py', y * 100, '%');
        card.classList.add('hub-parallax');
      });
    }, { passive: true });
    ['pointerleave', 'pointercancel', 'pointerdown', 'focusin'].forEach(function (event) {
      card.addEventListener(event, reset);
    });
  });
  function resetAll() { resets.forEach(function (reset) { reset(); }); }
  window.addEventListener('scroll', resetAll, { passive: true });
  window.addEventListener('resize', resetAll, { passive: true });
  window.addEventListener('blur', resetAll);
  document.addEventListener('visibilitychange', function () { if (document.hidden) resetAll(); });
  pointer.addEventListener('change', resetAll);
  motion.addEventListener('change', function () {
    resetAll();
    if (motion.matches) animations.forEach(function (animation) { animation.cancel(); });
  });
  if (!window.IntersectionObserver || !Element.prototype.animate) return;
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var target = entry.target;
      observer.unobserve(target);
      target.setAttribute('data-hub-revealed', 'true');
      if (motion.matches) return;
      if (target.classList.contains('hub-path')) {
        var order = cards.indexOf(target);
        var rtl = document.documentElement.dir === 'rtl';
        target.querySelectorAll('.hub-art-tile').forEach(function (tile) {
          var row = Number(tile.dataset.row), col = Number(tile.dataset.col);
          var wave = order === 1 ? Math.abs(col - 3) + row : (order === 2 ? 6 - col : col) + row;
          var rotation = (row + col) % 2 ? 'rotateX(100deg) rotateY(25deg)' : 'rotateX(-100deg) rotateY(-25deg)';
          if (rtl) rotation = (row + col) % 2 ? 'rotateX(100deg) rotateY(-25deg)' : 'rotateX(-100deg) rotateY(25deg)';
          var frames = pointer.matches ? [
            { opacity: 0, transform: rotation + ' scale(.8)' },
            { opacity: 1, transform: 'rotateX(0deg) rotateY(0deg) scale(1)' }
          ] : [{ opacity: 0, transform: 'translateY(6px)' }, { opacity: 1, transform: 'translateY(0)' }];
          animate(tile, frames, { duration: pointer.matches ? 700 : 400, delay: wave * (pointer.matches ? 45 : 20), easing: ease, fill: 'backwards' });
        });
      } else if (target.classList.contains('section-head-text')) {
        Array.from(target.children).forEach(function (element, index) { rise(element, index * 90); });
      } else {
        rise(target, 0);
      }
    });
  }, { threshold: .15, rootMargin: '-64px 0px 0px' });
  section.querySelectorAll('.section-head-text, .hub-path, .hub-preview-head, .issue, .empty-state, .hub-listing').forEach(function (element) {
    observer.observe(element);
  });
}());
