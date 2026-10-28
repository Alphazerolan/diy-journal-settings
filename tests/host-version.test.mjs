import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { hostCompatibility, detectHostCompatibility } from '../src/host-version.mjs';
import { adaptJournalCSS } from '../src/compat-css.mjs';
const modules = JSON.parse(readFileSync(new URL('../engine/scripts/dsh_rc3_classes.json', import.meta.url)));

test('only verified host releases select a version adapter', () => {
  assert.equal(hostCompatibility('0.2.1-rc.2').profile, 'rc2');
  assert.equal(hostCompatibility('v0.2.1-rc.3+desktop').profile, 'rc3');
  for (const version of [null, '0.2.1-rc.30', '0.2.1', '1.0.0', '<script>'])
    assert.equal(hostCompatibility(version).verified, false);
  assert.equal(detectHostCompatibility(() => { throw Error('absent'); }).profile, 'unverified');
});

test('rc3 adapts preserved local CSS without mutating other releases or scope', () => {
  const css = 'html[data-dsh-skin="diy-journal"] :is(.hIlkoa_sessionRow,.hIlkoa_searchResultRow){color:blue}';
  const result = adaptJournalCSS(css, 'rc3', modules);
  assert.match(result, /\.wnFoaW_sessionRow/);
  assert.ok(result.startsWith('html[data-dsh-skin="diy-journal"]'));
  assert.equal(adaptJournalCSS(result, 'rc3', modules), result);
  for (const profile of ['rc2', 'unverified', undefined]) assert.equal(adaptJournalCSS(css, profile, modules), css);
});
