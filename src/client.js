window.__ModuleLoader__.load({
  id: '@alphazerolan/dsh-plugin-diy-journal',
  factory: require => {
    /* BUNDLED_SKIN_RUNTIME */
    const React = require('react');
    const h = React.createElement;
    const prefix = '/api/local-diy-journal';
    function JournalSettings() {
      const [busy, setBusy] = React.useState(false);
      const [message, setMessage] = React.useState('');
      const [url, setUrl] = React.useState('');
      React.useEffect(() => {
        const report = event => setMessage(event.detail);
        document.addEventListener('diy-journal:intro-status', report);
        return () => document.removeEventListener('diy-journal:intro-status', report);
      }, []);
      const [skin, setSkin] = React.useState(null);
      const [center, setCenter] = React.useState(null);
      React.useEffect(() => {
        let live = true;
        Promise.all([
          fetch(prefix + '/status', { credentials: 'same-origin' }).then(r => r.json()),
          fetch('/api/skin-center/v2/active', { credentials: 'same-origin' })
            .then(r => r.ok ? r.json() : null).catch(() => null)
        ]).then(([status, active]) => {
          if (!live) return;
          setSkin(status.skin); setCenter(active?.ok ? active : false);
          if (status.error) setMessage(status.error);
        }).catch(() => { if (live) setMessage('无法读取插件状态，请重新打开设置。'); });
        return () => { live = false; };
      }, []);
      async function selectSkin(active) {
        setBusy(true); setMessage('正在切换皮肤…');
        try {
          const response = await fetch('/api/skin-center/v2/active', {
            method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ active })
          });
          const result = await response.json();
          if (!response.ok || !result.ok) throw new Error('切换失败，请在皮肤中心重新选择。');
          window.location.reload();
        } catch (error) { setMessage(error.message); setBusy(false); }
      }
      async function openMenu() {
        if (busy) return;
        setBusy(true); setMessage('正在准备样式菜单…'); setUrl('');
        try {
          const state = await fetch(prefix + '/status', { credentials: 'same-origin' });
          const info = await state.json();
          if (!state.ok) throw new Error(info.error || '无法连接菜单入口。');
          if (info.error) throw new Error(info.error);
          const response = await fetch(prefix + '/open', {
            method: 'POST', credentials: 'same-origin',
            headers: { 'X-DIY-Launch-Token': info.token }
          });
          const result = await response.json();
          if (!response.ok) throw new Error(result.error || '菜单启动失败。');
          if (!/^http:\/\/127\.0\.0\.1:\d+\/#[A-Za-z0-9_-]{32,}$/.test(result.url))
            throw new Error('菜单地址无效。');
          setUrl(result.url);
          window.open(result.url, '_blank', 'noopener,noreferrer');
          setMessage('菜单已准备好。若未自动打开，请点击下方链接。');
        } catch (error) { setMessage(error.message); }
        finally { setBusy(false); }
      }
      const card = {
        background: '#fffaf0', color: '#315b73', border: '1px solid #d9cbb2',
        borderRadius: 12, padding: 24, margin: '12px 0', lineHeight: 1.7,
        boxShadow: '0 3px 10px #526c8012', maxWidth: 720
      };
      return h('section', { style: card, 'aria-label': 'DIY 手账本设置', id: 'diy-journal-settings-panel' },
        h('style', null, 'html[data-dsh-skin="diy-journal"] [data-shortcut-modal="settings"]:has(#diy-journal-settings-panel){--cg-settings-section-title:"DIY 手账本"!important;}html[data-dsh-skin="diy-journal"] [data-shortcut-modal="settings"]:has(#diy-journal-settings-panel) .wCInkW_options::after{content:none!important;display:none!important;}'),
        h('div', { style: {fontSize: 28, fontFamily: 'KaiTi, STKaiti, cursive', marginBottom: 8} }, 'DIY 手账本'),
        h('p', null, '选照片、换胶带，拼出你的手账页面。'),
        h('p', { style: {fontSize: 14} }, skin
          ? '已内置皮肤 ' + skin.version + ' · 照片与布局独立保存，升级时保留。'
          : '正在检查内置皮肤…'),
        skin?.preserved?.length > 0 && h('p', { style: {fontSize: 13} },
          '检测到本地定制，已保留现有文件。'),
        center === false && h('p', { role: 'alert' },
          '请先安装并启用 DSH 皮肤中心，然后重新打开此页。皮肤外观由皮肤中心统一加载。'),
        center && h('div', { style: {display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap'} },
          h('button', { type: 'button', disabled: busy || !skin,
            onClick: () => selectSkin('diy-journal'), style: {padding: '8px 16px', font: 'inherit', color: '#315b73', background: '#fffdf5', border: '1px solid #b7cbd1', borderRadius: 7, cursor: 'pointer'} },
            center.active === 'diy-journal' ? '重新应用手账本' : '应用手账本'),
          center.active === 'diy-journal' && h('button', { type: 'button', disabled: busy,
            onClick: () => selectSkin(null), style: {padding: '8px 16px', font: 'inherit', color: '#315b73', background: '#fffdf5', border: '1px solid #b7cbd1', borderRadius: 7, cursor: 'pointer'} }, '使用官方默认')),
        h('p', { style: {fontSize: 14} }, '在样式菜单中调整照片布局、位置、角度、白边与题字，实时查看各区域效果。'),
        h('button', { type: 'button', disabled: busy, onClick: openMenu,
          style: {background: '#237fab', color: '#fff', border: '1px solid #237fab',
            borderRadius: 7, padding: '10px 20px', font: 'inherit', cursor: busy ? 'wait' : 'pointer'} },
          busy ? '正在打开…' : '打开样式菜单'),
        h('button', { type: 'button', onClick: () => document.dispatchEvent(new Event('diy-journal:replay-intro')),
          style: { marginLeft: 12, padding: '10px 16px', font: 'inherit', color: '#315b73', background: '#fffdf5', border: '1px solid #b7cbd1', borderRadius: 7, cursor: 'pointer' } }, '重播开场动画'),
        h('p', { style: {fontSize: 13, color: '#647f8e'} }, '菜单需要 Python 3.9+，会自动检测。完成后点击“保存并应用”，再刷新 Harness 查看效果。'),
        h('p', { role: 'status', style: {fontSize: 14} }, message),
        url && h('a', { href: url, target: '_blank', rel: 'noopener noreferrer',
          style: {color: '#237fab', textDecoration: 'underline'} }, '点击进入样式菜单')
      );
    }
    return {
      inject: ['slots'],
      apply(ctx) {
        ctx.effect(() => watchSkin(defineSkinHooks));
        ctx.effect(() => watchJournalIntro(window, { manualOnly: true }));
        ctx.effect(() => watchJournalVideos(window));
        ctx.slots.inject('settings.section', () => ctx.slots.register({
          name: 'settings.section', id: 'diy-journal', order: 10000,
          label: () => 'DIY 手账本'
        }, JournalSettings));
      }
    };
  }
});
