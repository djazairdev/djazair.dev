/* Local teammates assemble with scroll. Original illustration and implementation,
   inspired by Charlotte Dann's https://codepen.io/pouretrebelle/pen/NWNOLPN.
   Only the decorative puzzle moves; content and links remain available throughout. */
(function () {
  'use strict';
  var board = document.querySelector('#local-team .team-assembly');
  if (!board || !window.IntersectionObserver) return;
  var motion = matchMedia('(prefers-reduced-motion: reduce)');
  var frame = 0, visible = false;
  function update() {
    frame = 0;
    if (motion.matches || document.hidden) return;
    var height = window.innerHeight;
    var progress = Math.max(0, Math.min(1, (height * .88 - board.getBoundingClientRect().top) / (height * .52)));
    board.style.setProperty('--team-progress', progress.toFixed(4));
  }
  function schedule() {
    if (!frame && visible && !motion.matches && !document.hidden) frame = requestAnimationFrame(update);
  }
  function configure() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    board.classList.toggle('team-assembling', !motion.matches);
    if (motion.matches) board.style.removeProperty('--team-progress');
    else schedule();
  }
  var observer = new IntersectionObserver(function (entries) {
    visible = entries[0].isIntersecting;
    if (visible) schedule();
    else if (frame) { cancelAnimationFrame(frame); frame = 0; }
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
