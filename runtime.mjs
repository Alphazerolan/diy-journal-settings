import { existsSync, lstatSync, readdirSync, readFileSync, mkdirSync, copyFileSync, renameSync, rmSync, writeFileSync } from 'node:fs';
import { join, resolve, dirname, relative, isAbsolute, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';
import { createHash, randomUUID } from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const run = promisify(execFile);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
export const SKIN_ID = 'diy-journal';

export function paths(env = process.env, from = fileURLToPath(import.meta.url)) {
  let installedHome;
  for (let p = dirname(from); dirname(p) !== p; p = dirname(p)) {
    if (basename(p) === 'node_modules' && basename(dirname(dirname(p))) === 'profiles') {
      installedHome = dirname(dirname(dirname(p))); break;
    }
  }
  const home = resolve(env.DSH_HOME?.trim() || installedHome || join(homedir(), '.dsh'));
  return { home, skin: join(resolve(env.DSH_SKINS_HOME || env.DSH_SKINS_DIR || join(home, 'skins')), SKIN_ID),
    workspace: join(home, 'diy-journal-editor'), state: join(home, 'diy-journal-bundle.json'),
    backups: join(home, 'diy-journal-editor-backups') };
}

// Refuse junctions as well as links, including linked ancestors of a target.
export function assertPlain(path) {
  let p = resolve(path);
  while (true) {
    if (existsSync(p) && lstatSync(p).isSymbolicLink()) throw new Error('不支持链接目录：' + p);
    const parent = dirname(p);
    if (parent === p) break;
    p = parent;
  }
}

export function files(root) {
  assertPlain(root);
  const out = [];
  function visit(dir) {
    for (const item of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, item.name);
      if (item.isSymbolicLink()) throw new Error('不支持链接文件：' + p);
      if (item.isDirectory()) visit(p);
      else if (item.isFile()) out.push(relative(root, p));
    }
  }
  visit(root);
  return out;
}

function child(root, rel) {
  const p = resolve(root, rel);
  const delta = relative(resolve(root), p);
  if (!delta || delta.startsWith('..') || isAbsolute(delta)) throw new Error('无效的包内路径');
  return p;
}

function copy(source, target) {
  mkdirSync(dirname(target), { recursive: true });
  copyFileSync(source, target);
}

// Three-way update: replace only bytes that still match the previous shipped
// version. Unknown local installs and edited photos/CSS are never overwritten.
// A complete staging tree is swapped into place; the old tree is a backup.
export function provision(bundle, locations) {
  const { skin, state, backups } = locations;
  for (const p of [skin, state, backups]) assertPlain(p);
  const manifest = JSON.parse(readFileSync(join(bundle, 'skin.json'), 'utf8'));
  if (manifest.id !== SKIN_ID) throw new Error('皮肤包身份不匹配');
  const shipped = Object.fromEntries(files(bundle).map(rel => [rel, hash(readFileSync(join(bundle, rel)))]));
  const existing = existsSync(skin);
  if (existing && JSON.parse(readFileSync(join(skin, 'skin.json'), 'utf8')).id !== SKIN_ID)
    throw new Error('现有目录不属于 DIY 手账本');
  let previous = {};
  if (existsSync(state)) {
    const data = JSON.parse(readFileSync(state, 'utf8'));
    if (data.skin === skin) previous = data.files || {};
  }
  const writes = [], preserved = [];
  for (const [rel, digest] of Object.entries(shipped)) {
    const destination = child(skin, rel);
    assertPlain(destination);
    if (!existsSync(destination)) writes.push(rel);
    else {
      const actual = hash(readFileSync(destination));
      if (actual === digest) continue;
      if (previous[rel] && actual === previous[rel]) writes.push(rel);
      else preserved.push(rel);
    }
  }
  const removals = Object.keys(previous).filter(rel => {
    const p = child(skin, rel);
    assertPlain(p);
    return !shipped[rel] && existsSync(p) && hash(readFileSync(p)) === previous[rel];
  });
  let backup = null;
  if (writes.length || removals.length) {
    mkdirSync(dirname(skin), { recursive: true });
    const stage = skin + '.stage-' + randomUUID();
    mkdirSync(stage);
    try {
      if (existing) for (const rel of files(skin)) copy(join(skin, rel), child(stage, rel));
      for (const rel of writes) copy(join(bundle, rel), child(stage, rel));
      for (const rel of removals) rmSync(child(stage, rel));
      if (existing) {
        backup = join(backups, 'skin-' + Date.now() + '-' + randomUUID());
        mkdirSync(backups, { recursive: true });
        // Backups may be on a different volume from a custom skins directory.
        mkdirSync(backup);
        for (const rel of files(skin)) copy(join(skin, rel), child(backup, rel));
        const old = skin + '.previous-' + randomUUID();
        renameSync(skin, old);
        try { renameSync(stage, skin); } catch (error) { renameSync(old, skin); throw error; }
        rmSync(old, { recursive: true });
      } else renameSync(stage, skin);
    } finally { if (existsSync(stage)) rmSync(stage, { recursive: true }); }
  }
  mkdirSync(dirname(state), { recursive: true });
  const tmp = state + '.' + randomUUID() + '.tmp';
  writeFileSync(tmp, JSON.stringify({ schema: 1, version: manifest.version, skin, files: shipped }, null, 2) + '\n');
  renameSync(tmp, state);
  return { version: manifest.version, installedVersion: JSON.parse(readFileSync(join(skin, 'skin.json'), 'utf8')).version,
    changed: writes.length + removals.length, preserved, backup };
}

export async function findPython(env = process.env) {
  const candidates = env.DIY_JOURNAL_PYTHON ? [[env.DIY_JOURNAL_PYTHON, []]]
    : [['python', []], ['python3', []], ...(process.platform === 'win32' ? [['py', ['-3']]] : [])];
  for (const [command, prefix] of candidates) {
    try {
      const { stdout } = await run(command, [...prefix, '-c', 'import sys; assert sys.version_info >= (3,9); print(sys.executable)'],
        { timeout: 8000, windowsHide: true, env });
      const executable = stdout.trim();
      if (isAbsolute(executable) && existsSync(executable)) return executable;
    } catch { /* Try the next known executable, never a shell command. */ }
  }
  throw new Error('样式菜单需要 Python 3.9 或更高版本。安装后重新打开菜单；皮肤仍可正常使用。');
}

export async function prepareEditor(root, locations, python) {
  assertPlain(locations.workspace);
  await run(python, [join(root, 'install.py'), '--prepare-only', '--dsh-home', locations.home, '--skin-dir', locations.skin],
    { timeout: 120000, windowsHide: true, maxBuffer: 1024 * 1024 });
}
