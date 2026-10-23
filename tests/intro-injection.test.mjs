import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { introRows, registerIntroInjection } from '../src/intro-injection.mjs';

test('only the persisted active journal with a video injects; errors leave boot untouched', () => {
  const home = mkdtempSync(join(tmpdir(), 'journal-boot-'));
  try {
    const skin = join(home, 'skins', 'diy-journal');
    mkdirSync(join(skin, 'assets'), { recursive: true });
    const state = join(home, 'skin-center-active.json');
    assert.deepEqual(introRows(skin), []);
    writeFileSync(state, JSON.stringify({ active: 'diy-journal' }));
    assert.deepEqual(introRows(skin), []);
    writeFileSync(join(skin, 'assets', 'journal-opening-v7.mp4'), 'fixture');
    const [row] = introRows(skin);
    assert.equal(row.kind, 'script'); assert.equal(row.placement, 'body');
    assert.doesNotThrow(() => new Function(row.text));
    assert.ok(!row.text.includes('</script'));
    let callback;
    registerIntroInjection({ on(event, fn) { assert.equal(event, 'webserver/index-inject'); callback = fn; } }, skin);
    const rows = []; callback(rows); assert.equal(rows.length, 1);
    writeFileSync(state, JSON.stringify({ active: 'other' }));
    assert.deepEqual(introRows(skin), []);
    writeFileSync(state, '{bad'); assert.deepEqual(introRows(skin), []);
  } finally { rmSync(home, { recursive: true, force: true }); }
});
