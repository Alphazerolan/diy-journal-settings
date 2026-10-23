"""Read-only scene previews using the installed skin CSS and synthetic UI content."""
import base64, html, json, re
from urllib.parse import quote
import build, styles, video_media

LABELS=['账号与余额','通用设置','模型','内置插件','Agent 预设','已归档会话','Web 插件','皮肤','宠物','创意工坊','使用统计']

def row(title,value):
    return '<div class="scene-row"><span>'+html.escape(title)+'</span><span class="scene-value">'+html.escape(value)+'</span></div>'

def content(root,key):
    if key!='account':return json.loads((root/'templates/scenes/settings-pages.json').read_text(encoding='utf-8'))[key]
    data={
      'account':('账户与余额',[('演示账户','已登录'),('充值余额','¥0.00'),('赠送余额','¥0.00')]),
      'general':('通用设置',[('语言','简体中文'),('主题','浅色'),('发送消息','Enter'),('界面缩放','100%')]),
      'models':('模型',[('默认模型','DeepSeek'),('思考强度','标准'),('上下文窗口','跟随模型默认值')]),
      'plugins':('内置插件',[('文件与工作区','已启用'),('终端工具','已启用'),('网页工具','已启用')]),
      'presets':('Agent 预设',[('标准模式','当前使用'),('编程助手','工作区内修改'),('新建预设','＋ 添加')]),
      'archive':('已归档会话',[('整理项目笔记','已归档　·　预览'),('阅读文档','已归档　·　取消归档')]),
      'web':('Web 插件',[('服务状态','运行中'),('远程访问','仅本机'),('局域网访问','未开启')]),
      'skins':('皮肤',[('DIY手账本','当前使用'),('默认皮肤','切换'),('管理皮肤','打开目录')]),
      'pets':('宠物',[('桌面宠物','已启用'),('显示大小','标准'),('互动效果','已开启')]),
      'workshop':('创意工坊',[('皮肤与主题','浏览作品'),('插件','浏览插件'),('我的收藏','查看')]),
      'usage':('使用统计',[('今日消费','¥0.00'),('调用次数','0'),('Token 用量','0')])}
    title,rows=data[key]
    if key=='account':
        return '<div class="_8RVnMG_section"><div class="_8RVnMG_card"><div class="_8RVnMG_identity"><div class="_8RVnMG_avatar">♙</div><div class="_8RVnMG_identityCopy"><span class="_8RVnMG_name">演示账户</span><span class="_8RVnMG_status">已登录 DeepSeek</span></div></div></div><div class="_8RVnMG_balanceCard">'+''.join(row(*r) for r in rows[1:])+'</div></div>'
    return '<section class="scene-content"><h2>'+title+'</h2>'+''.join(row(*r) for r in rows)+'</section>'

def render(root,payload,token,asset_url=None):
    viewport=payload.get('viewport',[1200,840])
    if viewport not in ([1200,840],[1920,1080]):raise ValueError('无效预览窗口尺寸')
    slots=json.loads((root/'slots.json').read_text(encoding='utf-8'));mapping={s['id']:s for s in slots}
    active=payload.get('active');values=payload.get('choices')
    if active not in mapping or not isinstance(values,dict) or set(values)!=set(mapping):raise ValueError('无效预览区域或样式配置')
    selections={};occupied={};overrides={};video_slots=[]
    for s in slots:
        v=values[s['id']]
        if not isinstance(v,dict) or type(v.get('style')) is not int or v['style'] not in {x['id'] for x in styles.available(root,s)}:raise ValueError('无效区域样式')
        styles.validate_colors(root,v.get('tapeColors'));styles.validate_swap(v.get('swapPhotos',False))
        styles.validate_patterns(root,v.get('tapePatterns',styles.read_patterns(root,s)))
        styles.validate_adjustments(v.get('photoAdjustments',styles.read_adjustments(root,s)))
        styles.validate_borders(v.get('photoBorders',styles.read_borders(root,s)))
        styles.validate_front(v.get('frontPhoto',styles.read_front(root,s)))
        selections[s['id']]=v['style'];occupied[s['id']]=v['style']!=0 and bool(build.picture_files(root/'DIY图片'/s['folder']))
    main=active in ('home','main-sidebar')
    settings_page=payload.get('settingsPage','general') if active=='settings-sidebar' else active
    if not main and (settings_page not in mapping or not mapping[settings_page]['navIndex']):raise ValueError('无效设置页')
    relevant=['home','main-sidebar'] if main else [settings_page,'settings-sidebar']
    for key in relevant:
        if not occupied[key]:continue
        s=mapping[key];v=values[key];pics=build.pictures(root/'DIY图片'/s['folder'],2 if v['style']==8 else 1)
        svg=styles.render(root,s,v['style'],pics[0]['uri'],v['tapeColors'],pics[1]['uri'] if len(pics)>1 else None,v.get('swapPhotos',False),v.get('tapePatterns',styles.read_patterns(root,s)),v.get('photoAdjustments',styles.read_adjustments(root,s)),v.get('photoBorders',styles.read_borders(root,s)),v.get('frontPhoto',styles.read_front(root,s)))
        svg=video_media.decorate(svg,pics,root)
        if any(p.get('video') for p in pics):video_slots.append(dict(video_media.entry(s),svg=svg))
        overrides['assets/diy-generated/'+key+'.svg']=asset_url(svg) if asset_url else 'data:image/svg+xml;base64,'+base64.b64encode(svg.encode()).decode()
    prefix='/scene-assets/'+token+'/'
    def urls(css, dynamic=False):
        def convert(m):
            path=m.group(1).strip(' "\'')
            if path.startswith('assets/'):
                url=overrides.get(path) if dynamic else None
                return 'url("'+(url or prefix+quote(path[7:]))+'")'
            if path.startswith(('data:','#')):return m.group(0)
            return 'none'
        return re.sub(r'url\(([^)]+)\)',convert,css)
    css=(root/'templates/scenes/native.css').read_text(encoding='utf-8')+'\n'+(root/'skin.css').read_text(encoding='utf-8')+'\n'+(root/'templates/base.css').read_text(encoding='utf-8')
    css=urls(css,True)+'\n'+urls(build.rules(slots,occupied,selections),True)
    if main:
        body=(root/'templates/scenes/home.html').read_text(encoding='utf-8')
        body=re.sub(r'src="assets/([^"]+)"',lambda m:'src="'+prefix+quote(m.group(1))+'"',body)
    else:
        nav=''.join('<button class="wCInkW_navCell" aria-current="'+str(i==mapping[settings_page]['navIndex']-1).lower()+'"><span class="wCInkW_navLabel">'+label+'</span></button>' for i,label in enumerate(LABELS))
        body='<div class="scene-settings"><section class="wCInkW_panel" data-shortcut-modal="settings"><nav class="wCInkW_nav"><div class="wCInkW_navTitle">设置</div><div class="wCInkW_navList">'+nav+'</div></nav><div class="wCInkW_content"><header class="wCInkW_header"><strong>'+LABELS[mapping[settings_page]['navIndex']-1]+'</strong><button class="wCInkW_close">×</button></header><div class="wCInkW_options"><div data-slot="settings.section">'+content(root,settings_page)+'</div></div></div></section></div>'
    body+='<template id="diy-video-config">'+html.escape(json.dumps(video_slots,ensure_ascii=False))+'</template>'
    envelope="""
html,body{width:1200px;height:840px;overflow:hidden;margin:0}*{box-sizing:border-box}body{color:#315e80;font:14px/1.6 'Microsoft YaHei',sans-serif;background:#dceef5}button{font:inherit;color:inherit}a,button,input{pointer-events:none}body>.titlebar{height:32px;display:flex;padding:5px 20px;background:#cceefa}body>.titlebar span{margin-left:auto}.app{display:flex;width:1200px;height:808px}.app>aside{width:270px;flex:none;height:808px}.app>aside>._2H3hWW_root{height:100%;display:flex;flex-direction:column}._2H3hWW_regionArea{flex:1;min-height:0;overflow:hidden}._2H3hWW_footArea{margin-top:auto;flex:none}._2H3hWW_footArea::before{grid-column:1/-1}.app>main{flex:1;min-width:0;display:flex;flex-direction:column}.app>main>.Dc7zOa_header{display:none}[data-conversation-region=chat]{position:relative;flex:1;min-height:0}.Dc7zOa_headerBlank{position:relative;z-index:2}.hero-fixture{position:relative;z-index:2;margin:220px auto 0;max-width:690px;padding:0 20px}.scene-settings{width:1200px;height:840px;display:grid;place-items:center;background:#c1d5dd}.scene-settings .wCInkW_panel{position:relative!important;inset:auto!important;width:1000px!important;height:770px!important;max-width:none!important;max-height:none!important;margin:0!important;display:flex!important}.scene-settings .wCInkW_panel>nav{width:220px!important;flex:none!important;display:flex!important;flex-direction:column!important}.wCInkW_navList{display:flex;flex-direction:column}.wCInkW_navCell{display:flex;flex:none}.scene-settings .wCInkW_content{flex:1;min-width:0;display:flex;flex-direction:column}.scene-settings .wCInkW_header{height:62px;flex:none;display:flex;align-items:center;justify-content:space-between;padding:15px 28px}.scene-settings .wCInkW_options{display:flex;flex-direction:column;flex:1;min-height:0;overflow:auto;padding:18px 30px!important}.scene-settings [data-slot='settings.section']{flex:none}.scene-content{padding:18px;background:var(--sj-paper,#fffcf3);border:1px solid #d5ccb7;border-radius:8px}.scene-content h2{font-size:19px;margin:0 0 10px}.scene-row{display:flex;justify-content:space-between;gap:20px;padding:12px 4px;border-bottom:1px solid #bdced455}.scene-row:last-child{border-bottom:0}.scene-value{color:#64859a}.scene-settings .wCInkW_nav::after{flex-shrink:0}.scene-settings .wCInkW_options::after{flex-shrink:0}
"""
    envelope=envelope.replace('1200px',str(viewport[0])+'px').replace('840px',str(viewport[1])+'px').replace('808px',str(viewport[1]-32)+'px')
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width='+str(viewport[0])+'"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src \'self\' data:; media-src \'self\' blob:; connect-src \'self\'; font-src \'self\' data:; form-action \'none\'; base-uri \'none\'"><style>'+css+'\n'+envelope+'</style><body data-dsh-skin-center>'+body+'</body></html>'
