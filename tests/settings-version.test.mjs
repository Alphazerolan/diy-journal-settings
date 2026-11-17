import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const hookSource = readFileSync(new URL('../skin/hooks.mjs', import.meta.url), 'utf8');
const watchJournalSettingsVersion = vm.runInNewContext(
  hookSource.replace('export default function', 'function') + '\nwatchJournalSettingsVersion;');

function environment(version, previous = {}) {
  const values = new Map(Object.entries(previous));
  const body = { getAttribute: name => values.get(name) ?? null,
    setAttribute: (name, value) => values.set(name, value), removeAttribute: name => values.delete(name) };
  return { values, win: { document: { body, documentElement: body }, __DSH_BOOT__: { release: { version } } } };
}

test('actual release selects the rc1 settings layout while old and unknown releases stay legacy', () => {
  const cases = [
    ['0.1.7-rc.1', false], ['0.2.1-rc.2', false], ['0.2.1', false],
    ['0.2.2-alpha.99', false], ['0.2.2-beta.99', false], ['0.2.2-rc', false],
    ['0.2.2-rc0', false], ['0.2.2-rc.0', false],
    ['0.2.2-rc1', true], ['0.2.2-rc.1', true], ['0.2.2-rc.2', true], ['0.2.2-rc.3', true],
    ['0.2.2-rc.10', true], ['0.2.2', true], ['0.2.3-alpha.1', true], ['0.3.0', true],
    ['1.0.0', true], ['v0.2.2-rc1+build.123', true],
    ['', false], [null, false], [undefined, false], ['unknown', false],
    ['0.2.2-rc.', false], ['0.3.0-rc..1', false], ['0.2.2-rc.01', false]
  ];
  for (const [version, modern] of cases) {
    const { values, win } = environment(version);
    const stop = watchJournalSettingsVersion(win);
    assert.equal(values.get('data-diy-settings-layout'), modern ? 'rc1' : 'legacy', String(version));
    stop(); assert.equal(values.size, 0);
  }
});

test('skin and companion activations share one gate and restore previous values only after final cleanup', () => {
  const initial = { 'data-diy-settings-layout': 'old-owner', 'data-diy-dsh-version': 'old-version' };
  const { values, win } = environment('0.2.2-rc.1', initial);
  const first = watchJournalSettingsVersion(win), second = watchJournalSettingsVersion(win);
  first(); first(); assert.equal(values.get('data-diy-settings-layout'), 'rc1');
  second(); second(); assert.deepEqual(Object.fromEntries(values), initial);
  assert.equal(win.__diyJournalSettingsVersionGate, undefined);
});

test('compiled companion effect detects version even when another market hook already owns enhancements', () => {
  const { values, win } = environment('0.2.2-rc.3');
  win.__cgStateBooted = true;
  let factory;
  win.__ModuleLoader__ = { load: definition => { factory = definition.factory; } };
  const source = readFileSync(new URL('../client.js', import.meta.url), 'utf8');
  vm.runInNewContext(source, { window: win, document: win.document, console });
  const plugin = factory(name => {
    assert.equal(name, 'react'); return { createElement() {} };
  });
  const effects = [];
  plugin.apply({ effect: callback => effects.push(callback), slots: { inject() {} } });
  const stop = effects[0]();
  assert.equal(values.get('data-diy-settings-layout'), 'rc1');
  assert.equal(win.__cgStateBooted, true, 'gate must not acquire the projector');
  stop(); assert.equal(values.size, 0);
});
