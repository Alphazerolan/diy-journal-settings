import test from 'node:test';
import assert from 'node:assert/strict';
import defineSkinHooks from '../skin/hooks.mjs';

test('bundled projector can activate twice and releases its observers/listeners', t => {
  const keys = ['window', 'document', 'location', 'MutationObserver', 'cancelAnimationFrame', 'requestAnimationFrame'];
  const previous = Object.fromEntries(keys.map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
  t.after(() => { for (const key of keys) {
    if (previous[key]) Object.defineProperty(globalThis, key, previous[key]); else delete globalThis[key];
  } });
  let observers = 0;
  const listeners = new Set();
  globalThis.window = { addEventListener: (_name, fn) => listeners.add(fn),
    removeEventListener: (_name, fn) => listeners.delete(fn) };
  globalThis.document = { documentElement: { getAttribute: () => 'diy-journal', hasAttribute: () => false },
    body: { hasAttribute: () => false }, querySelectorAll: () => [] };
  globalThis.location = { hash: '', pathname: '/', search: '' };
  globalThis.MutationObserver = class { active = false;
    observe() { this.active = true; observers++; }
    disconnect() { if (this.active) observers--; this.active = false; }
  };
  globalThis.requestAnimationFrame = fn => setTimeout(fn, 1);
  globalThis.cancelAnimationFrame = clearTimeout;
  for (let cycle = 0; cycle < 2; cycle++) {
    const callbacks = [];
    const hooks = defineSkinHooks();
    hooks.apply({ onCleanup: fn => callbacks.push(fn) });
    assert.equal(window.__cgStateBooted, true);
    assert.equal(observers, 1); assert.equal(listeners.size, 1);
    // Another activation must not take ownership of the first one's observer.
    const duplicate = [];
    defineSkinHooks().apply({ onCleanup: fn => duplicate.push(fn) });
    duplicate.forEach(fn => fn());
    assert.equal(observers, 1);
    callbacks.forEach(fn => fn());
    callbacks.forEach(fn => fn());
    assert.equal(window.__cgStateBooted, false);
    assert.equal(observers, 0); assert.equal(listeners.size, 0);
  }
});
