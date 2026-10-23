import test from 'node:test';
import assert from 'node:assert/strict';
import { watchJournalIntro } from '../src/journal-intro.mjs';

function environment({ skin = 'diy-journal', reduced = false } = {}) {
  const timers = new Map(), frames = new Map(); let next = 0, mutation, now = 0;
  let loading = false, failed = false;
  class Element extends EventTarget {
    style = {}; children = []; isConnected = true; currentTime = 0;
    setAttribute(name, value) { this[name] = value; }
    removeAttribute(name) { delete this[name]; }
    append(...items) { items.forEach(item => { item.parent = this; this.children.push(item); }); }
    remove() { this.isConnected = false; this.parent.children = this.parent.children.filter(x => x !== this); }
    focus() { doc.activeElement = this; }
    pause() { this.paused = true; }
    load() {}
    play() { return Promise.resolve(); }
  }
  const doc = new EventTarget();
  doc.body = new Element(); doc.documentElement = { getAttribute: () => skin };
  doc.activeElement = new Element(); doc.createElement = () => new Element();
  doc.querySelector = selector => selector === '[data-dsh-boot]'
    ? (loading ? { querySelector: () => failed ? null : {} } : null) : (loading ? null : {});
  const media = new EventTarget(); media.matches = reduced;
  const win = { document: doc, matchMedia: () => media, performance: { now: () => now },
    AbortController, CustomEvent, URL: { createObjectURL: () => 'blob:intro', revokeObjectURL() {} },
    fetch: async () => ({ ok: true, blob: async () => new Blob(['video']) }),
    setTimeout(fn, delay) { const id = ++next; timers.set(id, { fn, delay }); return id; },
    clearTimeout(id) { timers.delete(id); },
    requestAnimationFrame(fn) { const id = ++next; frames.set(id, fn); return id; },
    cancelAnimationFrame(id) { frames.delete(id); },
    MutationObserver: class { constructor(fn) { mutation = fn; } observe() {} disconnect() { mutation = null; } }
  };
  return { win, doc, timers, frames, setSkin(value) { skin = value; mutation?.(); },
    loading(value, failure = false) { loading = value; failed = failure; },
    layer: () => doc.body.children[0],
    frame(ms = 16) { now += ms; const pending = [...frames.values()]; frames.clear(); pending.forEach(fn => fn(now)); } };
}

test('early injection starts before skin stamp and client adopts it without replay', () => {
  const env = environment({ skin: null }); env.loading(true);
  const dispose = watchJournalIntro(env.win, { early: true });
  const layer = env.layer(); assert.ok(layer);
  assert.equal(watchJournalIntro(env.win, { manualOnly: true }), dispose);
  assert.equal(env.doc.body.children.length, 1);
  const video = layer.children[0]; video.dispatchEvent(new Event('playing'));
  video.currentTime = 5; video.dispatchEvent(new Event('ended')); env.frame(5000);
  assert.equal(layer.style.opacity, '1');
  env.setSkin('diy-journal'); env.loading(false); env.frame();
  env.frame(400); assert.equal(env.layer(), undefined); dispose();
});

test('late client does not autoplay, but explicit replay remains available', () => {
  const env = environment(); const dispose = watchJournalIntro(env.win, { manualOnly: true });
  assert.equal(env.layer(), undefined);
  env.doc.dispatchEvent(new Event('diy-journal:replay-intro')); assert.ok(env.layer()); dispose();
});

test('early player releases the native boot error and on loading watchdog', () => {
  for (const reason of ['error', 'watchdog']) {
    const env = environment(); env.loading(true);
    const dispose = watchJournalIntro(env.win, { early: true });
    env.layer().children[0].dispatchEvent(new Event('playing'));
    if (reason === 'error') { env.loading(true, true); env.frame(); }
    else [...env.timers.values()].find(t => t.delay === 15000).fn();
    assert.equal(env.layer(), undefined); dispose();
  }
});

test('plays once, fades on video time, releases resources and restores focus', () => {
  const env = environment(), previous = env.doc.activeElement;
  const dispose = watchJournalIntro(env.win), layer = env.layer(), video = layer.children[0];
  assert.equal(layer.style.cssText.includes('visibility:hidden'), true);
  video.dispatchEvent(new Event('playing'));
  assert.equal(layer.style.visibility, 'visible');
  assert.equal(env.doc.activeElement, layer.children[1]);
  video.currentTime = 4.82; env.frame();
  assert.ok(Number(layer.style.opacity) > 0 && Number(layer.style.opacity) < 1);
  video.currentTime = 5; env.frame();
  assert.equal(env.layer(), undefined); assert.equal(env.timers.size, 0); assert.equal(env.frames.size, 0);
  assert.equal(env.doc.activeElement, previous);
  env.setSkin('other'); env.setSkin('diy-journal'); assert.equal(env.layer(), undefined);
  dispose(); dispose();
});

test('other skins and reduced motion never load video', () => {
  for (const options of [{ skin: 'other' }, { reduced: true }]) {
    const env = environment(options); const dispose = watchJournalIntro(env.win);
    assert.equal(env.layer(), undefined); assert.equal(env.timers.size, 0); dispose();
  }
});

test('an initially hidden desktop waits for visibility and explicit replay works', () => {
  const env = environment(); env.doc.hidden = true;
  const dispose = watchJournalIntro(env.win); assert.equal(env.layer(), undefined);
  env.doc.hidden = false; env.doc.dispatchEvent(new Event('visibilitychange'));
  assert.ok(env.layer()); env.layer().children[1].dispatchEvent(new Event('click'));
  env.doc.dispatchEvent(new Event('diy-journal:replay-intro')); assert.ok(env.layer());
  dispose();
});

test('desktop bridge rejection fails open without a lingering layer', async () => {
  const env = environment(); env.win.fetch = async () => { throw new Error('unavailable'); };
  const dispose = watchJournalIntro(env.win);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(env.layer(), undefined); assert.equal(env.timers.size, 0); dispose();
});

test('skip, media failure, skin switch, timeout and disposal never leave a blocking layer', () => {
  for (const reason of ['skip', 'error', 'switch', 'timeout', 'dispose', 'escape']) {
    const env = environment(), dispose = watchJournalIntro(env.win), layer = env.layer();
    if (reason === 'skip') layer.children[1].dispatchEvent(new Event('click'));
    if (reason === 'error') layer.children[0].dispatchEvent(new Event('error'));
    if (reason === 'switch') env.setSkin('other');
    if (reason === 'timeout') [...env.timers.values()].find(x => x.delay === 3000).fn();
    if (reason === 'dispose') dispose();
    if (reason === 'escape') { const event = new Event('keydown'); event.key = 'Escape'; env.doc.dispatchEvent(event); }
    assert.equal(env.layer(), undefined, reason); assert.equal(env.timers.size, 0, reason);
    dispose();
  }
});
