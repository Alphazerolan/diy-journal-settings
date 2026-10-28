import { spawn } from 'node:child_process';
import { randomBytes, timingSafeEqual } from 'node:crypto';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve, dirname, join } from 'node:path';
import { paths, provision, findPython, prepareEditor } from './runtime.mjs';
import { registerIntroInjection } from './src/intro-injection.mjs';
import { detectHostCompatibility } from './src/host-version.mjs';

export const name = 'diy-journal-settings';
export const inject = ['webServer'];
const root = dirname(fileURLToPath(import.meta.url));
const prefix = '/api/local-diy-journal';

export function localRequest(req) {
  const ip = req.socket?.remoteAddress?.replace(/^::ffff:/, '');
  if (ip !== '127.0.0.1' && ip !== '::1') return false;
  try {
    const host = new URL('http://' + req.headers.host);
    if (!['127.0.0.1', 'localhost', '[::1]'].includes(host.hostname)) return false;
    if (req.headers['sec-fetch-site'] === 'cross-site') return false;
    if (req.headers.origin && new URL(req.headers.origin).host !== host.host) return false;
    return true;
  } catch { return false; }
}

export function createLauncher(python, skinRoot = root, dshHome = null, skinDir = null) {
  let child = null, url = null, pending = null;
  return {
    running: () => Boolean(child && url),
    async open() {
      if (child && url) return url;
      if (pending) return pending;
      const script = join(skinRoot, 'scripts', 'style_menu.py');
      if (!existsSync(script)) throw new Error('找不到样式菜单，请重新安装 DIY 手账本。');
      pending = new Promise((accept, reject) => {
        const proc = spawn(python, ['-u', script, '--no-browser'], {
          cwd: skinRoot, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
          env: { ...process.env, ...(dshHome ? { DSH_HOME: dshHome } : {}),
            ...(skinDir ? { DIY_JOURNAL_SKIN_DIR: skinDir } : {}),
            DIY_JOURNAL_BUNDLED_SKIN_DIR: join(root, 'skin'), PYTHONIOENCODING: 'utf-8' }
        });
        child = proc;
        let output = '', errors = '', ready = false;
        const timer = setTimeout(() => {
          proc.kill(); reject(new Error('样式菜单启动超时，请重试。'));
        }, 15000);
        proc.stderr.on('data', data => { errors = (errors + data).slice(-2000); });
        proc.stdout.on('data', data => {
          output = (output + data).slice(-4096);
          const match = output.match(/http:\/\/127\.0\.0\.1:\d+\/#[A-Za-z0-9_-]{32,}/);
          if (!ready && match) {
            ready = true; clearTimeout(timer); url = match[0]; accept(url);
          }
        });
        proc.once('error', () => {
          clearTimeout(timer);
          if (child === proc) { child = null; url = null; }
          reject(new Error('无法启动本地菜单，请检查 Python 是否可用。'));
        });
        proc.once('exit', () => {
          clearTimeout(timer);
          if (child === proc) { child = null; url = null; }
          if (!ready) reject(new Error('样式菜单未能启动。' + errors.slice(-300)));
        });
      });
      try { return await pending; } finally { pending = null; }
    },
    dispose() { child?.kill(); child = null; url = null; }
  };
}

export function apply(ctx) {
  const locations = paths();
  const compatibility = detectHostCompatibility();
  registerIntroInjection(ctx, locations.skin);
  let installation, setupError, launcher, opening, disposed = false;
  try { installation = provision(join(root, 'skin'), locations); }
  catch (error) { setupError = error.message; }
  async function open() {
    if (disposed) throw new Error('插件已停用，请重新打开设置。');
    if (setupError) throw new Error(setupError);
    if (launcher) return launcher.open();
    if (!opening) opening = (async () => {
      const python = await findPython();
      await prepareEditor(root, locations, python);
      if (disposed) throw new Error('插件已停用。');
      launcher = createLauncher(python, locations.workspace, locations.home, locations.skin);
      return launcher.open();
    })().finally(() => { opening = null; });
    return opening;
  }
  const token = randomBytes(32).toString('hex');
  const reply = (res, code, data) => {
    res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(JSON.stringify(data));
  };
  ctx.effect(() => {
    const disposers = [
      ctx.webServer.register({ kind: 'exact', path: prefix + '/status', handler(req, res) {
        if (!localRequest(req)) return reply(res, 403, { error: '仅支持本机访问。' });
        if (req.method !== 'GET') return reply(res, 405, { error: '请求方式错误。' });
        reply(res, 200, { token, running: launcher?.running() || false, skin: installation, compatibility,
          error: setupError || null });
      }}),
      ctx.webServer.register({ kind: 'exact', path: prefix + '/open', async handler(req, res) {
        if (!localRequest(req)) return reply(res, 403, { error: '仅支持本机访问。' });
        const supplied = Buffer.from(String(req.headers['x-diy-launch-token'] || ''));
        if (supplied.length !== token.length || !timingSafeEqual(supplied, Buffer.from(token)))
          return reply(res, 403, { error: '入口已过期，请重新打开设置。' });
        if (req.method !== 'POST') return reply(res, 405, { error: '请求方式错误。' });
        try { reply(res, 200, { url: await open() }); }
        catch (error) { reply(res, 500, { error: error.message }); }
      }})
    ];
    return () => { disposed = true; disposers.forEach(dispose => dispose?.()); launcher?.dispose(); };
  });
}
