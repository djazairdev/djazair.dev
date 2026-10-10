/* Home scorecard: pointer depth and one-time chart reveals. The static data stays readable. */
(function () {
  'use strict';
  var section = document.querySelector('#scorecard');
  if (!section) return;
  var motion = matchMedia('(prefers-reduced-motion: reduce)');
  var pointer = matchMedia('(hover: hover) and (pointer: fine)');
  var cards = Array.from(section.querySelectorAll('.tile'));
  var animations = new Set();
  var resets = [];

  cards.forEach(function (card) {
    var box = null, frame = 0, point = null;
    function reset() {
      if (frame) cancelAnimationFrame(frame);
      frame = 0;
      box = point = null;
      card.classList.remove('score-tilting');
      ['--score-rx', '--score-ry', '--score-px', '--score-py'].forEach(function (key) {
        card.style.removeProperty(key);
      });
    }
    resets.push(reset);
    card.addEventListener('pointermove', function (event) {
      if (motion.matches || !pointer.matches || event.pointerType === 'touch') return;
      box = box || card.getBoundingClientRect();
      point = [event.clientX, event.clientY];
      if (frame) return;
      frame = requestAnimationFrame(function () {
        frame = 0;
        var x = Math.max(0, Math.min(1, (point[0] - box.left) / box.width));
        var y = Math.max(0, Math.min(1, (point[1] - box.top) / box.height));
        card.style.setProperty('--score-rx', ((.5 - y) * 4).toFixed(2) + 'deg');
        card.style.setProperty('--score-ry', ((x - .5) * 4).toFixed(2) + 'deg');
        card.style.setProperty('--score-px', (x * 100).toFixed(1) + '%');
        card.style.setProperty('--score-py', (y * 100).toFixed(1) + '%');
        card.classList.add('score-tilting');
      });
    }, { passive: true });
    ['pointerleave', 'pointercancel', 'pointerdown', 'focus'].forEach(function (event) {
      card.addEventListener(event, reset);
    });
  });

  function resetTilt() { resets.forEach(function (reset) { reset(); }); }
  window.addEventListener('scroll', resetTilt, { passive: true });
  window.addEventListener('resize', resetTilt, { passive: true });
  window.addEventListener('blur', resetTilt);
  pointer.addEventListener('change', resetTilt);
  motion.addEventListener('change', function () {
    resetTilt();
    if (motion.matches) animations.forEach(function (animation) { animation.cancel(); });
  });

  // Nothing is hidden by default: no JavaScript, unsupported APIs and reduced motion show final charts.
  if (motion.matches || !window.IntersectionObserver || !Element.prototype.animate) return;
  function reveal(element, frames, options, cleanup) {
    var animation = element.animate(frames, options);
    animations.add(animation);
    function done() {
      animations.delete(animation);
      if (cleanup) cleanup();
    }
    animation.finished.then(done, done);
  }
  var ease = 'cubic-bezier(.22,1,.36,1)';
  var observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var target = entry.target;
      observer.unobserve(target);
      target.setAttribute('data-score-revealed', 'true');
      if (motion.matches) return;
      if (target.classList.contains('tile-chart')) {
        target.querySelectorAll('.sp-ln').forEach(function (line) {
          // A chronological wipe keeps the stroke continuous in stretched, non-scaling SVGs.
          reveal(line, [{ clipPath: 'inset(-10px 100% -10px -10px)' },
                        { clipPath: 'inset(-10px -10px -10px -10px)' }],
                 { duration: 950, easing: ease });
        });
        target.querySelectorAll('.sp-area, .sp-end').forEach(function (element) {
          reveal(element, [{ opacity: 0 }, { opacity: 1 }],
                 { duration: 450, delay: element.classList.contains('sp-end') ? 650 : 150, fill: 'backwards' });
        });
        target.querySelectorAll('.hb-bar').forEach(function (bar, index) {
          bar.style.transformOrigin = document.documentElement.dir === 'rtl' ? 'right center' : 'left center';
          reveal(bar, [{ transform: 'scaleX(0)' }, { transform: 'scaleX(1)' }],
                 { duration: 750, delay: index * 70, easing: ease, fill: 'backwards' }, function () {
                   bar.style.removeProperty('transform-origin');
                 });
        });
      } else {
        target.querySelectorAll('.rank-strip .on').forEach(function (square) {
          reveal(square, [{ opacity: .25 }, { opacity: 1 }],
                 { duration: 450, delay: 650, easing: ease, fill: 'backwards' });
        });
      }
    });
  }, { threshold: .25, rootMargin: '-64px 0px 0px' });
  section.querySelectorAll('.tile-chart, .tile-foot').forEach(function (element) { observer.observe(element); });
}());
