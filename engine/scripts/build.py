"""Build folder-driven DIY art without reading or changing any other skin.

Python 3.9+ standard library only. No automatic seed restoration, no network.
"""
from pathlib import Path
import argparse, base64, hashlib, html, json, os, re, shutil, struct, subprocess, sys, tempfile
import xml.etree.ElementTree as ET
import styles, video_media
from image_dimensions import image_size

ROOT = Path(__file__).resolve().parents[1]
MIMES = {'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp',
         '.gif':'image/gif','.bmp':'image/bmp','.svg':'image/svg+xml','.mp4':'video/mp4'}
SEL = 'body:is([data-ds-dark-theme],:not([data-ds-dark-theme])) '
SETTINGS = SEL+'[data-shortcut-modal="settings"].wCInkW_panel'

def safe_child(base, relative):
    path=(base/relative).resolve()
    if path != base.resolve() and base.resolve() not in path.parents:
        raise ValueError('Path escapes the DIY package: '+str(relative))
    return path

def picture_files(directory):
    # No recursive search: an Archive subfolder is a safe place for unused alternatives.
    candidates=sorted((p for p in directory.iterdir() if p.is_file() and not p.name.startswith('.') and p.suffix.lower() in MIMES),key=lambda p:(p.name.casefold(),p.name))
    selection=directory/'图片选择.json'
    if selection.exists():
        data=json.loads(selection.read_text(encoding='utf-8'))
        if data.get('mode')=='selected':
            by_name={p.name:p for p in candidates}
            return [by_name[item['file']] for item in data.get('pictures',[])[:2] if item and item.get('file') in by_name]
    return candidates


def picture_labels(directory):
    selection=directory/'图片选择.json';labels={}
    if selection.exists():
        data=json.loads(selection.read_text(encoding='utf-8'))
        labels={item['file']:item.get('name',item['file']) for item in data.get('pictures',[]) if item}
    return [labels.get(p.name,p.name) for p in picture_files(directory)[:2]]

def pictures(directory, limit=2):
    return [load_picture(p) for p in picture_files(directory)[:limit]]

def first_picture(directory):
    items=pictures(directory,1)
    return items[0] if items else None

def load_picture(picture):
    if picture.is_symlink():raise ValueError('Please use an image file, not a link: '+str(picture))
    if picture.suffix.lower()=='.mp4':return video_media.load(picture)
    data=picture.read_bytes();ext=picture.suffix.lower()
    signatures={'.png':data.startswith(b'\x89PNG\r\n\x1a\n'),'.jpg':data.startswith(b'\xff\xd8'),'.jpeg':data.startswith(b'\xff\xd8'),'.webp':data[:4]==b'RIFF' and data[8:12]==b'WEBP','.gif':data[:6] in (b'GIF87a',b'GIF89a'),'.bmp':data[:2]==b'BM'}
    if ext in signatures and not signatures[ext]:raise ValueError('Invalid image header: '+str(picture))
    if ext=='.svg':
        doc=ET.fromstring(data)
        if doc.tag.split('}')[-1]!='svg':raise ValueError('Not an SVG: '+str(picture))
        for element in doc.iter():
            if element.tag.split('}')[-1] in ('script','foreignObject'):raise ValueError('SVG must be a self-contained image: '+str(picture))
            for key,value in element.attrib.items():
                if key.lower().startswith('on') or (key.split('}')[-1]=='href' and not value.startswith(('#','data:image/'))):
                    raise ValueError('External links or scripts in SVG: '+str(picture))
        if re.search(rb'@import|url\(\s*[\"\x27]?(?:https?:|file:|//)',data,re.I):raise ValueError('External SVG styles are unsupported')
    if not data:raise ValueError('Empty image: '+str(picture))
    return {'path':picture, 'data':data,'uri':'data:'+MIMES[ext]+';base64,'+base64.b64encode(data).decode('ascii')}

def visibility(present):return 'visible' if present else 'hidden'

def rules(slots, occupied, selections=None):
    selections=selections or {s['id']:styles.read_choice(ROOT,s) for s in slots}
    out=['/* DIY image slots. Empty photo areas collapse completely. */']
    for s in slots:
        key=s['id'];show=visibility(occupied[key]);url=f'url("assets/diy-generated/{key}.svg")'
        if not occupied[key]:
            if s['navIndex']:
                targets=[SETTINGS+f':has(> nav .wCInkW_navCell:nth-child({s["navIndex"]})[aria-current="true"]) .wCInkW_options::after']
            elif key=='home':
                targets=[SEL+'[data-conversation-region="chat"]'+pseudo for pseudo in ('::before','::after')]
            elif key=='settings-sidebar':
                targets=[SETTINGS+'>nav::after']
            else:
                targets=[SEL+'._2H3hWW_root:not(._2H3hWW_collapsed) ._2H3hWW_footArea::before']
            out.append(','.join(targets)+'{content:none!important;display:none!important;width:0!important;height:0!important;min-height:0!important;min-width:0!important;flex:0 0 0!important;aspect-ratio:auto!important;margin:0!important;padding:0!important;border:0!important;background:none!important;box-shadow:none!important;}')
            continue
        if s['navIndex']:
            selector=SETTINGS+f':has(> nav .wCInkW_navCell:nth-child({s["navIndex"]})[aria-current="true"]) .wCInkW_options::after'
            margin='auto 0 0' if key in ('account','usage') else '22px 0 4px'
            out.append(selector+'{content:""!important;display:block!important;position:relative!important;inset:auto!important;box-sizing:border-box!important;'
                       f'width:100%!important;max-width:{s["maxWidth"]}px!important;height:auto!important;min-height:0!important;aspect-ratio:{s["width"]}/{s["height"]}!important;'
                       'flex:0 0 auto!important;align-self:center!important;'+f'margin:{margin}!important;background:{url} center/contain no-repeat!important;visibility:{show}!important;'
                       'border:0!important;box-shadow:none!important;transform:none!important;pointer-events:none!important;}')
        elif key=='home':
            if selections[key]==2:
                # Style 2 keeps the original photo's frame, tilt and cover crop.
                out.append(SEL+'[data-conversation-region="chat"]::before{background-image:var(--sj-photo-veil),url("assets/diy-generated/home-source.svg")!important;visibility:'+show+'!important;}')
                out.append(SEL+'[data-conversation-region="chat"]::after{background-image:url("assets/diy-generated/home-tape-1.svg"),url("assets/diy-generated/home-tape-2.svg")!important;visibility:'+show+'!important;}')
            else:
                # Frame and tape are already contained in the selected SVG layout.
                out.append(SEL+'[data-conversation-region="chat"]::before{content:""!important;display:block!important;position:absolute!important;inset:20px!important;width:auto!important;height:auto!important;'
                           'background:var(--sj-photo-veil),url("assets/diy-generated/home.svg") center/100% 100% no-repeat!important;background-size:100% 100%,100% 100%!important;'
                           'border:0!important;border-radius:0!important;transform:none!important;box-shadow:none!important;visibility:visible!important;pointer-events:none!important;}')
                out.append(SEL+'[data-conversation-region="chat"]::after{content:none!important;display:none!important;}')
                out.append(SEL+'[data-conversation-region="chat"]:has(> .Dc7zOa_headerBlank)::before{inset:90px 20px 28px!important;}')
        elif key=='settings-sidebar':
            out.append(SETTINGS+'>nav::after{background:'+url+' center bottom/contain no-repeat!important;visibility:'+show+'!important;filter:none!important;}')
        elif key=='main-sidebar':
            # Allocate the footer photo bay only while this folder contains an image.
            out.append(SEL+'._2H3hWW_root:not(._2H3hWW_collapsed) ._2H3hWW_footArea::before{content:""!important;display:block!important;position:relative!important;inset:auto!important;'
                       'box-sizing:border-box;width:calc(100% - 6px)!important;min-width:0!important;max-width:calc(100% - 6px)!important;height:clamp(78px,11vh,120px)!important;min-height:0!important;'
                       'flex:0 0 auto!important;margin:4px 3px 0!important;align-self:center!important;'+f'background:{url} center/contain no-repeat!important;visibility:{show}!important;'
                       'border:0!important;box-shadow:none!important;transform:none!important;pointer-events:none!important;}')
    # Decorative paper is a paint layer, never a photo slot or a layout spacer.
    # Keep both palettes on disk; only the color palette is used for an empty home folder.
    if not occupied['home']:
        chat=SEL+'[data-conversation-region="chat"]'
        out.append(chat+'{--diy-art-top:18px;--diy-paper-veil:linear-gradient(transparent,transparent);background-color:var(--sj-paper)!important;'
                   'background-image:var(--diy-paper-veil),url("assets/diy-backgrounds/color.webp"),repeating-linear-gradient(0deg,transparent 0 35px,var(--sj-line) 35px 36px),url("assets/journal-paper-v80.svg")!important;'
                   'background-size:100% 100%,calc(100% - 28px) calc(100% - var(--diy-art-top) - 18px),100% 36px,160px 160px!important;'
                   'background-position:center,center bottom 18px,center,center!important;background-repeat:no-repeat,no-repeat,repeat,repeat!important;}')
        out.append(chat+':has(> .Dc7zOa_headerBlank){--diy-art-top:90px;}')
        out.append('body[data-ds-dark-theme] [data-conversation-region="chat"]{--diy-paper-veil:linear-gradient(#242f3b55,#242f3b55);}')
        out.append('@media(max-width:700px){'+chat+'{background-size:100% 100%,auto calc(100% - var(--diy-art-top) - 18px),100% 36px,160px 160px!important;}'+chat+':has(> .Dc7zOa_headerBlank){--diy-art-top:72px;}}')
        out.append('@media(forced-colors:active){'+chat+'{background:Canvas!important;}}')
    # Header art is independent of photo occupancy; do not replace the Explore banner.
    out.append(SEL+'.Dc7zOa_headerBlank{min-height:72px!important;}')
    out.append(SEL+'.Dc7zOa_headerBlank::before{content:""!important;left:18px!important;top:0!important;width:470px!important;max-width:calc(100% - 80px)!important;height:68px!important;padding:0!important;background:url("assets/diy-title.svg") left center/contain no-repeat!important;filter:none!important;pointer-events:none!important;}')
    out.append('body[data-ds-dark-theme] .Dc7zOa_headerBlank::before{filter:brightness(1.8) saturate(.7)!important;}')
    out.append('@media(max-width:700px){'+SEL+'.Dc7zOa_headerBlank{min-height:56px!important;}'+SEL+'.Dc7zOa_headerBlank::before{left:12px!important;max-width:calc(100% - 64px)!important;height:52px!important;}}')
    # Preserve the original Explore headline artwork and native Preview badge positioning.
    out.append(SEL+'.Hqq-bq_headline::before{background-image:url("assets/journal-hero-sticker-v86.webp")!important;}')
    return '\n'.join(out)+'\n'


def build():
    manifest=json.loads((ROOT/'skin.json').read_text(encoding='utf-8'))
    if manifest.get('id')!='diy-journal':raise ValueError('This script only builds the diy-journal skin')
    slots=json.loads((ROOT/'slots.json').read_text(encoding='utf-8'))
    outputs={};occupied={};report=[];video_slots=[];selections={};choices=styles.catalog(ROOT)
    for s in slots:
        folder=safe_child(ROOT/'DIY图片',s['folder']);folder.mkdir(exist_ok=True)
        key=s['id'];selections[key]=styles.read_choice(ROOT,s,choices)
        pics=[] if selections[key]==0 else pictures(folder,2 if selections[key]==8 else 1)
        selected=pics[0] if pics else None;occupied[key]=bool(selected)
        swap=styles.read_swap(ROOT,s)
        config_file=folder/styles.CONFIG_NAME
        tape_colors=styles.read_colors(ROOT,s)
        tape_patterns=styles.read_patterns(ROOT,s)
        adjustments=styles.read_adjustments(ROOT,s)
        borders=styles.read_borders(ROOT,s)
        front=styles.read_front(ROOT,s)
        outputs[str(config_file.relative_to(ROOT))]=json.dumps(styles.config(selections[key],styles.available(ROOT,s,choices),tape_colors,swap,tape_patterns,adjustments,borders,front),ensure_ascii=False,indent=2)+'\n'
        if selected:
            result=styles.render(ROOT,s,selections[key],selected['uri'],tape_colors,pics[1]['uri'] if len(pics)>1 else None,swap,tape_patterns,adjustments,borders,front)
        else:
            result=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s["width"]} {s["height"]}"/>'
        result=video_media.decorate(result,pics,ROOT)
        if any(p.get('video') for p in pics):video_slots.append(video_media.entry(s))
        outputs[f'assets/diy-generated/{key}.svg']=result
        if key=='home':
            for i,color in enumerate(tape_colors,1):outputs[f'assets/diy-generated/home-tape-{i}.svg']=styles.home_tape(ROOT,color)
            if selected:
                w,h=(selected['width'],selected['height']) if selected.get('video') else image_size(selected['data'],selected['path'].suffix.lower())
                outputs['assets/diy-generated/home-source.svg']=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><image width="100%" height="100%" href="{selected["uri"]}"/></svg>'
            else:outputs['assets/diy-generated/home-source.svg']=result
        report.append({'id':key,'region':s['folder'],'style':selections[key],'tapeColors':tape_colors,'tapePatterns':tape_patterns,'photoAdjustments':adjustments,'photoBorders':borders,'frontPhoto':front,'selected':selected['path'].name if selected else None,'sha256':hashlib.sha256(selected['data']).hexdigest() if selected else None,'photoCanvasSize':[s['width'],s['height']],'collapsed':not bool(selected),'photos':[p['path'].name for p in pics],'swapPhotos':swap})
    outputs['assets/diy-generated/videos.json']=json.dumps(video_slots,ensure_ascii=False)
    css=rules(slots,occupied,selections)
    outputs['patches.css']=(ROOT/'templates/base.css').read_text(encoding='utf-8')+'\n'+css
    outputs['generated/slots.css']=css
    outputs['generated/empty-slots.css']=rules(slots,{s['id']:False for s in slots},selections)
    outputs['generated/build-report.json']=json.dumps(report,ensure_ascii=False,indent=2)
    cards=[]
    for s in slots:
        name=html.escape(s['folder']);key=s['id']
        photo=f'<div class="bay" style="aspect-ratio:{s["width"]}/{s["height"]}"><img src="../assets/diy-generated/{key}.svg"></div>' if occupied[key] else '<small>无图片 · 图片区已收起</small>'
        style_name=next(x['name'] for x in choices if x['id']==selections[key])
        cards.append(f'<section><h2>{name}</h2><p>样式 {selections[key]} · {html.escape(style_name)}</p>{photo}</section>')
    outputs['generated/index.html']='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DIY 手账本 · 图片区域预览</title><style>*{box-sizing:border-box}body{margin:0;padding:28px;color:#315b73;background:repeating-linear-gradient(0deg,transparent 0 23px,#a5cbd426 23px 24px),#e8f3f7;font:15px "Microsoft YaHei",sans-serif}header{max-width:1120px;margin:0 auto 28px}header img{width:310px}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;max-width:1120px;margin:auto}section{border:1px solid #d7ceb5;border-radius:7px;padding:18px;background:#fffbef;box-shadow:0 3px 7px #647b8219}h2{font-size:17px;margin:0 0 15px}small{color:#7390a0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}.bay{margin-top:10px;background:repeating-linear-gradient(90deg,transparent 0 20px,#b5b08916 20px 21px);width:100%;position:relative}.bay img{width:100%;height:100%;display:block;object-fit:contain}@media(max-width:700px){main{grid-template-columns:1fr}body{padding:15px}}</style><header><img src="cover.svg" alt="手账本"><h1>图片区域 · 有图 / 留空对照</h1><p>14 个文件夹独立换图。留空保留位置，不显示胶带或白边。设置页只保留照片与粘贴结构。</p></header><main>'''+''.join(cards)+'</main></html>'
    outputs['generated/index.html']=outputs['generated/index.html'].replace('src="cover.svg"','src="../assets/diy-title.svg"')
    outputs['generated/index.html']=outputs['generated/index.html'].replace('图片区域 · 有图 / 留空对照','图片区域 · 当前状态').replace('留空保留位置，不显示胶带或白边。','无图片时收起图片区，不预留位置，不显示胶带或白边。')
    # The live skin server serves only assets/ and preview/ paths, never generated/.
    for relative in re.findall(r'url\([\"\x27]?([^\)\"\x27]+)', outputs['patches.css']):
        if relative.startswith('generated/'):
            raise ValueError('Unservable skin image path: '+relative)
    # Validate everything before replacing generated files. A bad first file never silently falls back.
    for name,content in outputs.items():
        if name.endswith('.svg'):ET.fromstring(content)
    for name,content in outputs.items():
        target=safe_child(ROOT,name);target.parent.mkdir(parents=True,exist_ok=True)
        temporary=target.with_suffix(target.suffix+'.tmp');temporary.write_text(content,encoding='utf-8');os.replace(temporary,target)
    print('Built %d regions: %d with images, %d empty.'%(len(slots),sum(occupied.values()),len(slots)-sum(occupied.values())))

def install():
    target=Path(os.environ.get('DIY_JOURNAL_SKIN_DIR') or str(Path(os.environ.get('DSH_HOME', str(Path.home()/'.dsh')))/'skins/diy-journal'))
    if target.resolve()==ROOT.resolve():return
    if not (target/'skin.json').is_file() or json.loads((target/'skin.json').read_text(encoding='utf-8')).get('id')!='diy-journal':
        raise ValueError('Install the DIY Journal skin first.')
    allowed=['skin.css','patches.css','hooks.mjs','skin.json','NOTICE','README.md','README.zh.md','LICENSE','intro-settings.json']
    sources=[ROOT/n for n in allowed if (ROOT/n).is_file()]+[p for p in (ROOT/'assets').rglob('*') if p.is_file()]
    for source in sources:
        if source.is_symlink():raise ValueError('Linked files are unsupported')
        dest=safe_child(target,source.relative_to(ROOT));dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    print('Applied DIY Journal assets. Personal images remain in the editor workspace.')

def launch():
    config=ROOT/'启动配置.json'
    path=Path(json.loads(config.read_text(encoding='utf-8'))['application'])
    if not path.is_file():raise ValueError('Edit application path in 启动配置.json before launching.')
    subprocess.Popen([str(path)],cwd=path.parent,close_fds=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');parser.add_argument('--launch',action='store_true');args=parser.parse_args()
    try:
        build()
        if args.install:install()
        if args.launch:launch()
    except Exception as error:
        print('DIY build stopped: '+str(error),file=sys.stderr);sys.exit(1)
