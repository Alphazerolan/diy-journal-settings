window.__ModuleLoader__.load({
  id: '@alphazerolan/dsh-plugin-diy-journal',
  factory: require => {
    const React = require('react');
    const h = React.createElement;
    const prefix = '/api/local-diy-journal';
    function JournalSettings() {
      const [busy, setBusy] = React.useState(false);
      const [message, setMessage] = React.useState('');
      const [url, setUrl] = React.useState('');
      async function openMenu() {
        if (busy) return;
        setBusy(true); setMessage('正在准备样式菜单…'); setUrl('');
        try {
          const state = await fetch(prefix + '/status', { credentials: 'same-origin' });
          const info = await state.json();
          if (!state.ok) throw new Error(info.error || '无法连接菜单入口。');
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
      return h('section', { style: card, 'aria-label': 'DIY 手账本设置' },
        h('div', { style: {fontSize: 28, fontFamily: 'KaiTi, STKaiti, cursive', marginBottom: 8} }, 'DIY 手账本'),
        h('p', null, '选照片、换胶带，拼出你的手账页面。'),
        h('p', { style: {fontSize: 14} }, '在样式菜单中调整照片布局、位置、角度、白边与题字，实时查看各区域效果。'),
        h('button', { type: 'button', disabled: busy, onClick: openMenu,
          style: {background: '#237fab', color: '#fff', border: '1px solid #237fab',
            borderRadius: 7, padding: '10px 20px', font: 'inherit', cursor: busy ? 'wait' : 'pointer'} },
          busy ? '正在打开…' : '打开样式菜单'),
        h('p', { style: {fontSize: 13, color: '#647f8e'} }, '完成后点击“保存并应用”，再刷新 Harness 查看效果。'),
        h('p', { role: 'status', style: {fontSize: 14} }, message),
        url && h('a', { href: url, target: '_blank', rel: 'noopener noreferrer',
          style: {color: '#237fab', textDecoration: 'underline'} }, '点击进入样式菜单')
      );
    }
    return {
      inject: ['slots'],
      apply(ctx) {
        ctx.slots.inject('settings.section', () => ctx.slots.register({
          name: 'settings.section', id: 'diy-journal', order: 10000,
          label: () => 'DIY 手账本'
        }, JournalSettings));
      }
    };
  }
});
