import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { paths, provision, findPython } from '../runtime.mjs';
import { watchSkin } from '../src/skin-lifecycle.mjs';

function fixture(t) {
  const base = mkdtempSync(join(tmpdir(), 'journal-bundle-'));
  t.after(() => rmSync(base, { recursive: true, force: true }));
  const bundle = join(base, 'bundle'); mkdirSync(bundle);
  const put = (rel, data) => { const p = join(bundle, rel); mkdirSync(dirname(p), { recursive: true }); writeFileSync(p, data); };
  put('skin.json', JSON.stringify({ id: 'diy-journal', version: '1.0.0' }));
  put('skin.css', 'old css'); put('assets/photo.svg', 'original photo');
  return { bundle, put, locations: paths({ DSH_HOME: join(base, 'home') }) };
}

test('fresh install includes skin; upgrade preserves edits and backs up replaced defaults', t => {
  const { bundle, put, locations } = fixture(t);
  assert.equal(provision(bundle, locations).changed, 3);
  writeFileSync(join(locations.skin, 'assets/photo.svg'), 'personal photo');
  mkdirSync(locations.workspace); writeFileSync(join(locations.workspace, 'layout.json'), 'personal layout');
  put('skin.css', 'new css'); put('assets/photo.svg', 'new default');
  put('skin.json', JSON.stringify({ id: 'diy-journal', version: '1.1.0' }));
  const result = provision(bundle, locations);
  assert.equal(readFileSync(join(locations.skin, 'skin.css'), 'utf8'), 'new css');
  assert.equal(readFileSync(join(locations.skin, 'assets/photo.svg'), 'utf8'), 'personal photo');
  assert.equal(readFileSync(join(locations.workspace, 'layout.json'), 'utf8'), 'personal layout');
  assert.equal(readFileSync(join(result.backup, 'skin.css'), 'utf8'), 'old css');
  assert.equal(result.preserved.length, 1);
  assert.equal(provision(bundle, locations).changed, 0);
});

test('asset cleanup retains dependencies of custom styles and extra user files', t => {
  for (const customization of ['skin.css', 'custom.css', null]) {
    const { bundle, put, locations } = fixture(t);
    provision(bundle, locations);
    if (customization) writeFileSync(join(locations.skin, customization), 'body {background:url(assets/photo.svg)}');
    rmSync(join(bundle, 'assets/photo.svg'));
    put('assets/photo.webp', 'compact default');
    put('skin.css', 'body {background:url(assets/photo.webp)}');
    provision(bundle, locations);
    assert.equal(existsSync(join(locations.skin, 'assets/photo.svg')), Boolean(customization));
    assert.equal(existsSync(join(locations.skin, 'assets/photo.webp')), true);
  }
});

test('adopting an existing manual skin preserves unknown custom bytes', t => {
  const { bundle, locations } = fixture(t);
  mkdirSync(locations.skin, { recursive: true });
  writeFileSync(join(locations.skin, 'skin.json'), JSON.stringify({ id: 'diy-journal', version: '9.0.0' }));
  writeFileSync(join(locations.skin, 'skin.css'), 'custom CSS');
  const result = provision(bundle, locations);
  assert.equal(readFileSync(join(locations.skin, 'skin.css'), 'utf8'), 'custom CSS');
  assert.equal(result.installedVersion, '9.0.0');
});

test('wrong skin identity is rejected before writing', t => {
  const { bundle, put, locations } = fixture(t);
  put('skin.json', '{"id":"different-skin"}');
  assert.throws(() => provision(bundle, locations), /身份不匹配/);
  assert.equal(existsSync(locations.skin), false);
});

test('custom DSH home and skin directory override are respected', () => {
  const p = paths({ DSH_HOME: '/custom-home', DSH_SKINS_DIR: '/other-skins' });
  assert.match(p.home, /custom-home$/); assert.match(p.skin, /other-skins[\\/]diy-journal$/);
  const inferred = paths({}, '/custom/profiles/desktop/node_modules/@author/plugin/runtime.mjs');
  assert.match(inferred.home, /custom$/);
});

test('unavailable configured Python has a useful error without affecting skin', async () => {
  await assert.rejects(findPython({ ...process.env, DIY_JOURNAL_PYTHON: 'nonexistent-journal-python' }), /Python 3.9/);
});

test('skin lifecycle releases ownership on switch and starts again on return', async () => {
  let selected = null, observer, started = 0, ended = 0;
  const win = { document: { documentElement: { getAttribute: () => selected } },
    setTimeout, clearTimeout, MutationObserver: class {
      constructor(callback) { observer = callback; } observe() {} disconnect() { observer = () => {}; }
    } };
  const dispose = watchSkin(() => ({ apply(ctx) {
    started++; win.__cgStateBooted = true;
    ctx.onCleanup(() => { ended++; win.__cgStateBooted = false; });
  } }), win);
  const tick = () => new Promise(resolve => setTimeout(resolve, 10));
  await tick(); assert.equal(started, 0);
  selected = 'diy-journal'; observer(); await tick(); assert.equal(started, 1);
  observer(); await tick(); assert.equal(started, 1);
  selected = 'blue-fantasy'; observer(); await tick(); assert.equal(ended, 1);
  selected = 'diy-journal'; observer(); await tick(); assert.equal(started, 2);
  dispose(); dispose(); assert.equal(ended, 2);
});

test('skin lifecycle does not duplicate an existing market hook owner', async () => {
  const win = { __cgStateBooted: true,
    document: { documentElement: { getAttribute: () => 'diy-journal' } }, setTimeout, clearTimeout,
    MutationObserver: class { observe() {} disconnect() {} } };
  let starts = 0;
  const dispose = watchSkin(() => { starts++; }, win);
  await new Promise(resolve => setTimeout(resolve, 10)); dispose();
  assert.equal(starts, 0); assert.equal(win.__cgStateBooted, true);
});

test('published manifest exposes the standard bundle and keeps user state out', () => {
  const root = new URL('../', import.meta.url);
  const pkg = JSON.parse(readFileSync(new URL('package.json', root)));
  assert.equal(pkg.dsh.bundle.patch, './cordis.patch.yml');
  assert.match(readFileSync(new URL(pkg.dsh.bundle.patch, root), 'utf8'), new RegExp(pkg.name));
  assert(pkg.files.includes('skin')); assert(!pkg.files.includes('runtime.json'));
  assert(pkg.dsh.engines.dsh); assert(pkg.peerDependencies['@deepseek-ai/dsh']);
});
