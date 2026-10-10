/* Deep links to a formula or limitation open its enclosing native disclosure.
   Downloads and all panels remain usable without JavaScript. */
(() => {
  'use strict';
  const revealHash = () => {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const target = id && document.getElementById(id);
    if (!target || !target.closest('.data-methods')) return;
    let panel = target.closest('details');
    while (panel) {
      panel.open = true;
      panel = panel.parentElement.closest('details');
    }
    target.scrollIntoView({block: 'start'});
  };
  window.addEventListener('hashchange', revealHash);
  revealHash();
})();
