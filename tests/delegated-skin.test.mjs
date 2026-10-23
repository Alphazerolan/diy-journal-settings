import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { delegatedJournalCSS, watchDelegatedJournal } from '../src/delegated-skin.mjs';
import { watchSkin } from '../src/skin-lifecycle.mjs';

const selection = 'data-dsh-delegated-skin', render = 'data-dsh-diy-journal-rendering';
const css = 'html[data-dsh-skin="diy-journal"] body {color: blue}';
const tick = () => new Promise(resolve => setTimeout(resolve, 15));

function environment() {
  const observers = new Set();
  class Node extends EventTarget {
    attrs = new Map(); children = [];
    getAttribute(key) { return this.attrs.get(key) ?? null; }
    hasAttribute(key) { return this.attrs.has(key); }
    setAttribute(key, value) {
      if (this.getAttribute(key) === value) return;
      this.attrs.set(key, value); this.changed(key);
    }
    removeAttribute(key) { if (this.attrs.delete(key)) this.changed(key); }
    changed(key) {
      for (const o of observers) if (o.targets.some(([node, opts]) => node === this && opts.attributeFilter?.includes(key))) queueMicrotask(o.callback);
    }
    append(...nodes) { for (const node of nodes) { node.parent = this; this.children.push(node); } }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(n => n !== this); }
  }
  const doc = new EventTarget();
  Object.assign(doc, { body: new Node(), documentElement: new Node(), head: new Node(), createElement: () => new Node() });
  const requests = [];
  const win = { document: doc, AbortController, CustomEvent, setTimeout, clearTimeout, console: { warn() {} },
    MutationObserver: class {
      targets = []; constructor(callback) { this.callback = callback; observers.add(this); }
      observe(node, opts) { this.targets.push([node, opts]); }
      disconnect() { observers.delete(this); }
    },
    fetch(url, options) { requests.push({url, ...options}); return Promise.resolve({ ok: true, text: async () => css }); }
  };
  return { win, doc, requests, observers,
    choose(id) { if (id) doc.documentElement.setAttribute(selection, id); else doc.documentElement.removeAttribute(selection); } };
}

test('rewrites only the journal scope, preserving dark selectors, URLs and other IDs', () => {
  const input = `${css}\n:where(html[data-dsh-skin='diy-journal']) body[data-ds-dark-theme]{background:url(/assets/a.svg)}\nhtml[data-dsh-skin=other]{color:red}`;
  const output = delegatedJournalCSS(input);
  assert(!output.includes('data-dsh-skin="diy-journal"'));
  assert(output.includes(':has(> body[data-dsh-diy-journal-rendering])'));
  assert(output.includes('body[data-ds-dark-theme]'));
  assert(output.includes('url(/assets/a.svg)'));
  assert(output.includes('html[data-dsh-skin=other]'));
  assert.throws(() => delegatedJournalCSS('body {color:blue}'), /unscoped/);
});

test('old centers and stock theme do not activate; selected plugin mounts once and yields to default', async () => {
  const e = environment(), stop = watchDelegatedJournal(e.win);
  await tick(); assert.equal(e.requests.length, 0);
  assert(e.doc.body.hasAttribute('data-dsh-diy-journal-handoff'));
  e.choose('diy-journal-plugin'); await tick();
  assert.equal(e.doc.head.children.length, 2); assert(e.doc.body.hasAttribute(render));
  assert.equal(e.doc.documentElement.getAttribute('data-dsh-skin'), null);
  e.choose(null); await tick();
  assert.equal(e.doc.head.children.length, 0); assert(!e.doc.body.hasAttribute(render));
  assert(e.doc.body.hasAttribute('data-dsh-diy-journal')); // Settings and capability stay available.
  e.choose('diy-journal-plugin'); await tick(); assert.equal(e.doc.head.children.length, 2);
  stop(); stop(); assert.equal(e.doc.head.children.length, 0); assert.equal(e.observers.size, 0);
  assert(!e.doc.body.hasAttribute('data-dsh-diy-journal'));
});

test('other skins, other delegated selections and wallpaper suppress and release the renderer', async () => {
  const e = environment(), stop = watchDelegatedJournal(e.win);
  e.choose('diy-journal-plugin'); await tick();
  e.doc.documentElement.setAttribute('data-dsh-skin', 'blue-fantasy'); await tick();
  assert(!e.doc.body.hasAttribute(render)); assert.equal(e.doc.head.children.length, 0);
  // Preview cancellation restores the original explicit delegated selection.
  e.doc.documentElement.removeAttribute('data-dsh-skin'); await tick(); assert(e.doc.body.hasAttribute(render));
  e.doc.body.setAttribute('data-we-wallpaper', '1'); await tick(); assert(!e.doc.body.hasAttribute(render));
  e.doc.body.removeAttribute('data-we-wallpaper'); await tick(); assert(e.doc.body.hasAttribute(render));
  e.choose('claude-style'); await tick(); assert(!e.doc.body.hasAttribute(render));
  stop();
});

test('late CSS responses cannot remount after cancel, a newer selection, or disposal', async () => {
  for (const action of ['cancel', 'other', 'dispose']) {
    const e = environment(); const completions = [];
    e.win.fetch = (url, options) => { e.requests.push(options); return new Promise(resolve => completions.push(resolve)); };
    const stop = watchDelegatedJournal(e.win); e.choose('diy-journal-plugin'); await tick();
    if (action === 'dispose') stop(); else e.choose(action === 'cancel' ? null : 'other');
    await tick(); assert(e.requests.every(r => r.signal.aborted));
    completions.forEach(done => done({ok:true, text:async()=>css})); await tick();
    assert.equal(e.doc.head.children.length, 0); assert(!e.doc.body.hasAttribute(render)); stop();
  }
});

test('a failed stylesheet leaves no partial theme and can retry after reselect', async () => {
  const e = environment(); let broken = true, errors = 0;
  e.doc.addEventListener('diy-journal:render-error', () => errors++);
  e.win.fetch = async url => ({ok: !broken || !url.endsWith('patches'), text:async()=>css});
  const stop = watchDelegatedJournal(e.win); e.choose('diy-journal-plugin'); await tick();
  assert.equal(errors, 1); assert.equal(e.doc.head.children.length, 0); assert(!e.doc.body.hasAttribute(render));
  e.choose(null); await tick(); broken = false; e.choose('diy-journal-plugin'); await tick();
  assert(e.doc.body.hasAttribute(render)); stop();
});

test('projector and pending video work stop when delegated painting ends', async () => {
  const e = environment(); let hooks = 0, cleanups = 0;
  const stopHooks = watchSkin(() => ({ apply(ctx) { hooks++; ctx.onCleanup(() => cleanups++); } }), e.win);
  const source = readFileSync(new URL('../engine/scripts/video-runtime.js', import.meta.url), 'utf8');
  const context = vm.createContext({console}); vm.runInContext(source, context);
  let signal;
  e.win.fetch = (_url, options) => { signal = options.signal; return new Promise(() => {}); };
  const stopVideos = context.watchJournalVideos(e.win);
  e.doc.body.setAttribute(render, ''); await tick(); assert.equal(hooks, 1); assert(signal && !signal.aborted);
  e.doc.body.removeAttribute(render); await tick(); assert.equal(cleanups, 1); assert(signal.aborted);
  stopHooks(); stopVideos(); assert.equal(e.observers.size, 0);
});

test('descriptor separates delegated selection ID from the existing asset skin', () => {
  const descriptor = JSON.parse(readFileSync(new URL('../skin.json', import.meta.url)));
  const asset = JSON.parse(readFileSync(new URL('../skin/skin.json', import.meta.url)));
  assert.equal(descriptor.id, 'diy-journal-plugin'); assert.equal(asset.id, 'diy-journal');
  assert.equal(descriptor.wiring.id, 'ui-diy-journal');
});

test('explicit own claim makes legacy peers yield without blocking our renderer', async () => {
  const e = environment(); const stop = watchDelegatedJournal(e.win);
  e.doc.documentElement.setAttribute('data-dsh-skin', 'diy-journal-plugin');
  e.choose('diy-journal-plugin'); await tick();
  assert(e.doc.body.hasAttribute(render));
  e.doc.documentElement.setAttribute('data-dsh-skin', 'other'); await tick();
  assert(!e.doc.body.hasAttribute(render)); stop();
});

test('inline delegated CSS resolves picture and font assets through the original skin route', () => {
  const out = delegatedJournalCSS(css + `\na{background:url(assets/photo.webp);mask:url('./assets/tape 1.svg')}\n@font-face{src:url("assets/font.woff2")}\nb{background:url(data:image/png;base64,AAAA)}`);
  assert(out.includes('url(/api/skin-center/v2/skins/diy-journal/assets/photo.webp)'));
  assert(out.includes("url('/api/skin-center/v2/skins/diy-journal/assets/tape 1.svg')"));
  assert(out.includes('url("/api/skin-center/v2/skins/diy-journal/assets/font.woff2")'));
  assert(out.includes('url(data:image/png;base64,AAAA)'));
});
