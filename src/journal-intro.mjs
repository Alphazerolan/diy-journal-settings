// One intro per document. Skin switches and plugin disposal always release it.
export function watchJournalIntro(win = window, options = {}) {
  // The ordinary client adopts the early controller instead of starting again.
  if (win.__diyJournalIntroController) return win.__diyJournalIntroController.dispose;
  const doc = win.document;
  const key = '__diyJournalIntroPlayed';
  const status = text => {
    win.__diyJournalIntroStatus = text;
    doc.dispatchEvent(new win.CustomEvent('diy-journal:intro-status', { detail: text }));
  };
  let stopPlayback = null, stopped = false, manual = false, sawPainting = false, observedBody = null;
  const reduced = win.matchMedia('(prefers-reduced-motion: reduce)');
  const painting = () => !doc.body?.hasAttribute?.('data-we-wallpaper') &&
    (doc.documentElement.getAttribute('data-dsh-skin') === 'diy-journal' || doc.body?.hasAttribute?.('data-dsh-diy-journal-rendering'));
  function sync() {
    if (stopped) return;
    if (doc.body && doc.body !== observedBody) {
      observedBody = doc.body;
      observer.observe(observedBody, { attributes: true, attributeFilter: ['data-dsh-diy-journal-rendering', 'data-we-wallpaper'] });
    }
    const skin = doc.documentElement.getAttribute('data-dsh-skin');
    if (painting()) sawPainting = true;
    const waiting = options.early && !sawPainting && (!skin || (options.delegated && skin === 'diy-journal-plugin')) && !manual && !doc.body?.hasAttribute?.('data-we-wallpaper') &&
      (!options.delegated || doc.documentElement.getAttribute('data-dsh-delegated-skin') === 'diy-journal-plugin');
    if (!painting() && !waiting) {
      stopPlayback?.(); return;
    }
    if (options.manualOnly && !manual) return;
    if (win[key] || !doc.body) return;
    if (doc.hidden) return;
    win[key] = true;
    if (reduced.matches) { status('系统已启用减少动画，已跳过开场。'); return; }
    status('正在读取开场动画…');
    const layer = doc.createElement('div');
    layer.id = 'diy-journal-intro';
    layer.setAttribute('role', 'dialog');
    layer.setAttribute('aria-label', '手账本开场动画');
    layer.style.cssText = 'position:fixed;inset:0;z-index:2147483000;background:#faf7ef;opacity:0;visibility:hidden;pointer-events:auto;';
    const video = doc.createElement('video');
    video.muted = true; video.playsInline = true; video.preload = 'auto';
    video.setAttribute('aria-hidden', 'true');
    // Zoom and timing are baked into this file. Do not add a second CSS camera move.
    video.style.cssText = 'display:block;width:100%;height:100%;object-fit:contain;';
    const skip = doc.createElement('button');
    skip.type = 'button'; skip.textContent = '跳过动画';
    skip.style.cssText = 'position:absolute;right:24px;bottom:24px;padding:9px 16px;border:1px solid #aac7cf;border-radius:8px;background:#fffaf0;color:#315b73;font:14px sans-serif;cursor:pointer;';
    const hint = doc.createElement('div');
    hint.textContent = '正在打开手账本…';
    hint.style.cssText = 'position:absolute;bottom:28px;left:24px;color:#315b73;font:14px sans-serif;';
    layer.append(video, skip, hint); doc.body.append(layer);
    if (options.early && !manual) { layer.style.visibility = 'visible'; layer.style.opacity = '1'; }
    let done = false, frame = null, shown = false, objectUrl = null, fadeStart = null;
    const needsReady = options.early && !manual;
    const ready = () => !needsReady || (painting()
      && !doc.querySelector('[data-dsh-boot]') && !!doc.querySelector('#root > *'));
    const request = new win.AbortController();
    const previousFocus = doc.activeElement;
    const cleanup = () => {
      if (done) return;
      done = true;
      win.clearTimeout(loadTimeout); win.clearTimeout(watchdog);
      if (frame !== null) win.cancelAnimationFrame(frame);
      doc.removeEventListener('keydown', onKey);
      doc.removeEventListener('visibilitychange', onVisibility);
      reduced.removeEventListener('change', onReduced);
      const restoreFocus = doc.activeElement === skip;
      video.pause(); video.removeAttribute('src'); video.load(); layer.remove();
      request.abort();
      if (objectUrl) win.URL.revokeObjectURL(objectUrl);
      if (restoreFocus && previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
      stopPlayback = null;
    };
    const onKey = event => { if (event.key === 'Escape') { event.preventDefault(); cleanup(); } };
    const onVisibility = () => { if (doc.hidden) cleanup(); };
    const onReduced = () => { if (reduced.matches) cleanup(); };
    const tick = (now = win.performance.now()) => {
      if (done) return;
      const boot = needsReady && doc.querySelector('[data-dsh-boot]');
      // The core keeps the failure report inside its boot node but removes the spinner.
      if (boot && !boot.querySelector('[data-dsh-boot-spinner]')) {
        status('DSH 启动遇到问题，已显示原始错误信息。'); cleanup(); return;
      }
      const isReady = ready();
      hint.textContent = isReady ? '' : '正在加载界面…';
      if (video.currentTime >= 4.65 && isReady && fadeStart === null) fadeStart = now;
      const p = needsReady ? (fadeStart === null ? 0 : Math.max(0, Math.min(1, (now - fadeStart) / 340)))
        : Math.max(0, Math.min(1, (video.currentTime - 4.65) / 0.34));
      layer.style.opacity = String(1 - p * p * (3 - 2 * p));
      if (p >= 1) { status('开场动画已播放完毕。'); cleanup(); return; }
      frame = win.requestAnimationFrame(tick);
    };
    const loadTimeout = win.setTimeout(() => { status('动画读取超时，已跳过。'); cleanup(); }, 3000);
    const watchdog = win.setTimeout(() => { status('已返回 DSH 加载界面。'); cleanup(); }, needsReady ? 15000 : 8500);
    stopPlayback = cleanup;
    skip.addEventListener('click', () => { status('已跳过开场动画。'); cleanup(); });
    video.addEventListener('error', () => { status('视频播放失败：' + (video.error?.message || '无法解码视频')); cleanup(); });
    video.addEventListener('ended', () => {
      // Keep the last frame until the app is ready; the frame loop owns the fade.
      if (!needsReady) { status('开场动画已播放完毕。'); cleanup(); }
    });
    video.addEventListener('playing', () => {
      if (done || shown) return;
      shown = true; win.clearTimeout(loadTimeout);
      status('正在播放开场动画。');
      layer.style.visibility = 'visible'; layer.style.opacity = '1';
      skip.focus({ preventScroll: true }); tick();
    });
    doc.addEventListener('keydown', onKey);
    doc.addEventListener('visibilitychange', onVisibility);
    reduced.addEventListener('change', onReduced);
    // DSH desktop intercepts fetch for API routes; a media src does not use
    // that bridge. A blob also avoids requiring HTTP Range in older hosts.
    win.fetch('/api/skin-center/v2/skins/diy-journal/assets/journal-opening-v7.mp4',
      { signal: request.signal, credentials: 'same-origin' })
      .then(response => { if (!response.ok) throw new Error('Intro asset unavailable'); return response.blob(); })
      .then(blob => {
        if (done) return;
        objectUrl = win.URL.createObjectURL(blob); video.src = objectUrl;
        return video.play();
      }).catch(error => { if (!done) status('开场动画未能播放：' + error.message); cleanup(); });
  }
  const observer = new win.MutationObserver(sync);
  const replay = () => {
    stopPlayback?.(); manual = true; win[key] = false; sync();
  };
  observer.observe(doc.documentElement, { attributes: true, attributeFilter: ['data-dsh-skin', 'data-dsh-delegated-skin'] });
  doc.addEventListener('DOMContentLoaded', sync, { once: true });
  doc.addEventListener('visibilitychange', sync);
  doc.addEventListener('diy-journal:replay-intro', replay);
  const dispose = () => {
    if (stopped) return;
    stopped = true; observer.disconnect();
    doc.removeEventListener('DOMContentLoaded', sync); stopPlayback?.();
    doc.removeEventListener('visibilitychange', sync);
    doc.removeEventListener('diy-journal:replay-intro', replay);
    delete win.__diyJournalIntroController;
  };
  win.__diyJournalIntroController = { dispose, early: !!options.early };
  sync();
  return dispose;
}
