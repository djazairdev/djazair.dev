/* Local teammates assemble and separate in CSS 3D with scroll. Original illustration
   and implementation; depth inspired by https://github.com/yourlin/mortise-puzzle.
   Only the decorative puzzle moves; content and links remain available throughout. */
(function () {
  'use strict';
  var board = document.querySelector('#local-team .team-assembly');
  if (!board || !window.IntersectionObserver) return;
  var motion = matchMedia('(prefers-reduced-motion: reduce)');
  var pieces = board.querySelectorAll('.team-piece');
  var frame = 0, visible = false;
  function clamp(value) { return Math.max(0, Math.min(1, value)); }
  function update() {
    frame = 0;
    if (motion.matches || document.hidden) return;
    var height = window.innerHeight;
    var rect = board.getBoundingClientRect();
    // Hold the connected puzzle through the middle of the viewport. Both edges
    // use the same progress, so reversing scroll retraces the assembly exactly.
    var enter = clamp((height * .94 - rect.top) / (height * .40));
    var leave = clamp((rect.bottom - height * .06) / (height * .30));
    var progress = Math.min(enter, leave);
    board.style.setProperty('--team-progress', progress.toFixed(4));
    pieces.forEach(function (piece, i) {
      var p = clamp((progress - i * .06) / .82);
      piece.style.setProperty('--team-piece-progress', (p * p * (3 - 2 * p)).toFixed(4));
    });
  }
  function schedule() {
    if (!frame && visible && !motion.matches && !document.hidden) frame = requestAnimationFrame(update);
  }
  function configure() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    board.classList.toggle('team-assembling', !motion.matches);
    board.classList.toggle('team-in-view', visible && !motion.matches);
    if (motion.matches) {
      board.style.removeProperty('--team-progress');
      pieces.forEach(function (piece) { piece.style.removeProperty('--team-piece-progress'); });
    }
    else update();
  }
  var observer = new IntersectionObserver(function (entries) {
    visible = entries[0].isIntersecting;
    board.classList.toggle('team-in-view', visible && !motion.matches);
    if (visible) schedule();
    else {
      if (frame) cancelAnimationFrame(frame);
      update();
    }
  });
  configure();
  observer.observe(board);
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule, { passive: true });
  window.addEventListener('pageshow', schedule);
  document.addEventListener('visibilitychange', function () {
    if (document.hidden && frame) { cancelAnimationFrame(frame); frame = 0; }
    else schedule();
  });
  motion.addEventListener('change', configure);
}());
