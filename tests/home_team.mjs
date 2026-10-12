import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

function style() {
  const values = new Map();
  return {setProperty: (key, value) => values.set(key, value),
    removeProperty: key => values.delete(key), values};
}
const pieces = Array.from({length: 4}, () => ({style: style()}));
const classes = new Set();
let rect = {top: 1100, bottom: 1380}, observed, scheduled, motionChange;
const listeners = {};
const board = {style: style(), querySelectorAll: () => pieces,
  getBoundingClientRect: () => rect,
  classList: {toggle: (name, on) => on ? classes.add(name) : classes.delete(name)}};
const motion = {matches: false, addEventListener: (_, fn) => { motionChange = fn; }};
const document = {hidden: false, querySelector: () => board,
  addEventListener: (name, fn) => { listeners[name] = fn; }};
const window = {innerHeight: 1000, IntersectionObserver: true,
  addEventListener: (name, fn) => { listeners[name] = fn; }};
vm.runInNewContext(readFileSync(new URL('../site/static/js/home-team.js', import.meta.url), 'utf8'), {
  document, window, matchMedia: () => motion,
  IntersectionObserver: class {
    constructor(fn) { observed = fn; }
    observe() {}
  },
  requestAnimationFrame: fn => { scheduled = fn; return 1; },
  cancelAnimationFrame: () => { scheduled = undefined; }
});
function scroll(top) {
  rect = {top, bottom: top + 280};
  listeners.scroll();
  if (scheduled) { const fn = scheduled; scheduled = undefined; fn(); }
  return pieces.map(piece => Number(piece.style.values.get('--team-piece-progress')));
}
assert.deepEqual(pieces.map(piece => Number(piece.style.values.get('--team-piece-progress'))), [0, 0, 0, 0]);
observed([{isIntersecting: true}]);
const entering = scroll(800);
assert(entering[0] > entering[1] && entering[1] > entering[2] && entering[2] > entering[3], 'pieces arrive in order');
assert.deepEqual(scroll(450), [1, 1, 1, 1], 'readable assembled state in the middle');
const leaving = scroll(-120);
assert(leaving.every(value => value > 0 && value < 1), 'pieces fade and separate on exit');
assert.deepEqual(scroll(-290), [0, 0, 0, 0], 'fully hidden beyond the viewport');
assert.deepEqual(scroll(-120), leaving, 'reverse scrolling retraces the exit');
assert.deepEqual(scroll(450), [1, 1, 1, 1]);
assert.deepEqual(scroll(800), entering, 'reverse scrolling retraces the entrance');
motion.matches = true;
motionChange();
assert(!classes.has('team-assembling'), 'reduced motion keeps the static illustration');
assert(!classes.has('team-in-view'));
assert.equal(board.style.values.size, 0);
assert(pieces.every(piece => piece.style.values.size === 0), 'no opacity or movement remains on reduced motion');
motion.matches = false;
motionChange();
document.hidden = true;
listeners.visibilitychange();
assert.equal(scheduled, undefined, 'hidden tabs have no pending animation');
console.log('Puzzle entrance, hold, exit, reversal and reduced-motion checks passed.');
