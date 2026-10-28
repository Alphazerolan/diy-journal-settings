// Skin Center owns the selection stamp; this plugin only reads it.
// Older centers without this signal keep using the existing asset-skin path.
export function delegatedJournalCSS(css) {
  const stamp = /\[data-dsh-skin\s*=\s*(?:"diy-journal"|'diy-journal'|diy-journal)\s*\]/g;
  if (typeof css !== 'string' || !stamp.test(css)) throw new Error('Skin Center returned unscoped journal CSS');
  stamp.lastIndex = 0;
  // Inline sheets resolve relative URLs against the document, unlike the
  // center's stylesheet links. Preserve quotes/escapes and rebase our assets.
  return css.replace(stamp, ':has(> body[data-dsh-diy-journal-rendering])')
    .replace(/url\(\s*(?:(["'])(.*?)\1|([^'"\s)]+))\s*\)/gi, (whole, quote, quoted, plain) => {
      const path = quoted ?? plain;
      if (!/^(?:\.\/)?assets\//.test(path)) return whole;
      const q = quote || '';
      return 'url(' + q + '/api/skin-center/v2/skins/diy-journal/' + path.replace(/^\.\//, '') + q + ')';
    });
}

export function watchDelegatedJournal(win = window, adapt = css => css) {
  const doc = win.document;
  const selection = 'data-dsh-delegated-skin';
  const live = 'data-dsh-diy-journal';
  const handoff = 'data-dsh-diy-journal-handoff';
  const rendering = 'data-dsh-diy-journal-rendering';
  const endpoint = '/api/skin-center/v2/skins/diy-journal/';
  let closed = false, epoch = 0, request = null, styles = [], body = null, failed = false;
  const selected = () => doc.documentElement.getAttribute(selection) === 'diy-journal-plugin'
    && [null, 'diy-journal-plugin'].includes(doc.documentElement.getAttribute('data-dsh-skin'))
    && !doc.body?.hasAttribute('data-we-wallpaper');
  function release() {
    epoch++; request?.abort(); request = null;
    body?.removeAttribute(rendering);
    styles.forEach(node => node.remove()); styles = [];
  }
  function advertise() {
    if (!doc.body || doc.body === body) return;
    if (body) { release(); body.removeAttribute(live); body.removeAttribute(handoff); }
    body = doc.body;
    body.setAttribute(live, '1'); body.setAttribute(handoff, '1');
    observer.observe(body, { attributes: true, attributeFilter: ['data-we-wallpaper'] });
  }
  async function sync() {
    if (closed) return;
    advertise();
    if (!selected() || !body) { release(); failed = false; return; }
    if (styles.length || request || failed) return;
    const generation = ++epoch;
    const controller = request = new win.AbortController();
    try {
      // Reuse Skin Center's sanitizer and asset URLs, never raw user CSS.
      const texts = await Promise.all(['stylesheet', 'patches'].map(async part => {
        const response = await win.fetch(endpoint + part, { credentials: 'same-origin', signal: controller.signal, cache: 'no-store' });
        if (!response.ok) throw new Error('Cannot load journal ' + part);
        return adapt(delegatedJournalCSS(await response.text()));
      }));
      if (closed || epoch !== generation || !selected()) return;
      const nodes = texts.map((text, i) => {
        const node = doc.createElement('style');
        node.setAttribute('data-diy-delegated-style', String(i)); node.textContent = text; return node;
      });
      // Prepare both sheets before enabling their shared scope.
      styles = nodes; doc.head.append(...nodes);
      body.setAttribute(rendering, '');
    } catch (error) {
      if (!closed && epoch === generation && error.name !== 'AbortError') {
        release(); failed = true;
        doc.dispatchEvent(new win.CustomEvent('diy-journal:render-error', { detail: '手账本外观加载失败，请重新选择皮肤。' }));
        win.console?.warn('[DIY Journal] Delegated skin unavailable:', error);
      }
    } finally { if (epoch === generation) request = null; }
  }
  const observer = new win.MutationObserver(sync);
  observer.observe(doc.documentElement, { attributes: true, attributeFilter: [selection, 'data-dsh-skin'], childList: true });
  doc.addEventListener('DOMContentLoaded', sync);
  sync();
  return () => {
    if (closed) return;
    closed = true; observer.disconnect(); doc.removeEventListener('DOMContentLoaded', sync);
    release(); body?.removeAttribute(live); body?.removeAttribute(handoff);
  };
}
