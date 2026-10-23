// Supply the state projector for the asset or delegated renderer,
// without duplicating an existing trusted market hook activation.
export function watchSkin(createHooks, win = window) {
  const doc = win.document;
  let cleanup = null, stopped = false;
  function sync() {
    if (stopped) return;
    const active = !doc.body?.hasAttribute('data-we-wallpaper') &&
      (doc.documentElement.getAttribute('data-dsh-skin') === 'diy-journal' || doc.body?.hasAttribute('data-dsh-diy-journal-rendering'));
    if (!active) { cleanup?.(); cleanup = null; return; }
    if (cleanup || win.__cgStateBooted) return;
    const callbacks = [];
    let instance;
    const dispose = () => {
      callbacks.splice(0).reverse().forEach(fn => fn());
      instance?.dispose?.();
    };
    try {
      instance = createHooks();
      instance.apply({ skinId: 'diy-journal', onCleanup: fn => callbacks.push(fn) });
      cleanup = dispose;
    } catch (error) { dispose(); console.warn('[DIY Journal] Skin enhancements unavailable:', error); }
  }
  // Let skin-center finish its current activation/cleanup before acquiring it.
  let timer;
  const schedule = () => { win.clearTimeout(timer); timer = win.setTimeout(sync, 0); };
  const observer = new win.MutationObserver(schedule);
  observer.observe(doc.documentElement, { attributes: true, attributeFilter: ['data-dsh-skin'] });
  if (doc.body) observer.observe(doc.body, { attributes: true, attributeFilter: ['data-dsh-diy-journal-rendering', 'data-we-wallpaper'] });
  schedule();
  return () => { stopped = true; observer.disconnect(); win.clearTimeout(timer); cleanup?.(); cleanup = null; };
}
