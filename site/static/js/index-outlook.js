/* Enhance native forecast radios and the illustrative growth scenario. All facts,
   example scenarios and links remain available without JavaScript. */
(() => {
  'use strict';
  const forecast = document.querySelector('.forecast-switch');
  if (forecast) {
    const sync = () => {
      const selected = forecast.querySelector('input:checked');
      if (selected) forecast.dataset.group = selected.value;
    };
    forecast.addEventListener('change', sync);
    sync();
  }
  const panel = document.querySelector('[data-growth-scenario]');
  if (!panel) return;
  const base = Number(panel.dataset.base), years = Number(panel.dataset.years);
  const chart = panel.querySelector('.scenario-chart');
  const ceiling = Number(chart.dataset.ceiling);
  if (!(base > 0 && years > 0 && ceiling > 0)) return;
  const input = panel.querySelector('input[type=range]');
  // Match the site's ar-DZ format regardless of the browser's bundled ICU locale data.
  const number = new Intl.NumberFormat('en-GB', {maximumFractionDigits: 0});
  const percent = new Intl.NumberFormat('en-GB', {style: 'percent', maximumFractionDigits: 2});
  const local = text => panel.dataset.lang === 'ar' ? text.replace(/[,.]/g, mark => mark === ',' ? '.' : ',') : text;
  const update = () => {
    const rate = Math.min(35, Math.max(0, Number(input.value))) / 100;
    const total = base * (1 + rate) ** years;
    const text = local(percent.format(rate));
    panel.querySelector('[data-scenario-total]').textContent = local(number.format(Math.round(total)));
    panel.querySelector('[data-scenario-rate]').textContent = text;
    panel.querySelector('[data-scenario-legend]').textContent = text;
    input.setAttribute('aria-valuetext', text);
    const path = Array.from({length: 49}, (_, i) => {
      const x = 44 + i / 48 * 410;
      const y = 230 - base * (1 + rate) ** (years * i / 48) / ceiling * 200;
      return `${i ? 'L' : 'M'}${x.toFixed(2)},${y.toFixed(2)}`;
    }).join(' ');
    panel.querySelector('[data-scenario-path]').setAttribute('d', path);
    panel.querySelector('[data-scenario-end]').setAttribute('cy', String(230 - total / ceiling * 200));
  };
  input.addEventListener('input', update);
  update();
  panel.querySelector('.scenario-control').hidden = false;
})();
