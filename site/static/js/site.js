/* djazair.dev: small enhancements. Every page works without this file. */
(function () {
  'use strict';

  // Remember the language the reader picks, so / sends them there next time.
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-lang]');
    if (!a) return;
    try { localStorage.setItem('djz-lang', a.getAttribute('data-lang')); } catch (err) { /* storage blocked */ }
  });

  // Phone menu (<details>): close it on Escape or a click outside.
  var menu = document.querySelector('details.menu');
  if (menu) {
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && menu.open) {
        menu.open = false;
        menu.querySelector('summary').focus();
      }
    });
    document.addEventListener('click', function (e) {
      if (menu.open && !menu.contains(e.target)) menu.open = false;
    });
  }

  // Index sub-nav: on phones, bring the current section into view.
  var current = document.querySelector('.subnav-row [aria-current]');
  if (current) {
    var row = current.parentElement;
    var a = current.getBoundingClientRect();
    var r = row.getBoundingClientRect();
    if (a.left < r.left || a.right > r.right) {
      current.scrollIntoView({ block: 'nearest', inline: 'center' });
    }
  }
})();
