"""MP4 imports use a browser-decoded poster; no ffmpeg dependency at runtime."""
import base64, hashlib, json, re, shutil, threading
from pathlib import Path
import xml.etree.ElementTree as ET
from image_dimensions import image_size

MAX_BYTES=20*1024*1024
NS='{http://www.w3.org/2000/svg}'
PUBLISH_LOCK=threading.Lock()

def sidecar(path):return path.with_name('.'+path.name+'.json')

def validate(raw, metadata):
    if not raw or len(raw)>MAX_BYTES or len(raw)<12 or raw[4:8]!=b'ftyp':
        raise ValueError('请选择有效的 MP4 视频，大小不能超过 20 MB。')
    if not isinstance(metadata,dict):raise ValueError('视频缺少预览信息，请在菜单中重新选择。')
    w,h=metadata.get('width'),metadata.get('height')
    if any(type(x) is not int or not 0<x<=16384 for x in (w,h)):raise ValueError('视频尺寸无效。')
    poster=metadata.get('poster','')
    if not isinstance(poster,str) or len(poster)>3*1024*1024 or not poster.startswith('data:image/jpeg;base64,'):
        raise ValueError('视频封面无效，请重新选择视频。')
    data=base64.b64decode(poster.split(',',1)[1],validate=True)
    if not data.startswith(b'\xff\xd8') or min(image_size(data,'.jpg'))<=0:raise ValueError('视频封面无效。')
    return {'width':w,'height':h,'poster':poster}

def load(path):
    meta_path=sidecar(path)
    if meta_path.is_symlink():raise ValueError('视频预览信息不能是链接。')
    if not meta_path.is_file():raise ValueError('视频需要预览封面，请在样式菜单中点击“选择图片或视频”导入。')
    raw=path.read_bytes();meta=validate(raw,json.loads(meta_path.read_text(encoding='utf-8')))
    digest=hashlib.sha256(raw).hexdigest()
    # A unique image URI also distinguishes videos sharing an identical first frame.
    poster=f'<svg xmlns="http://www.w3.org/2000/svg" width="{meta["width"]}" height="{meta["height"]}" viewBox="0 0 {meta["width"]} {meta["height"]}"><desc>{digest}</desc><image width="100%" height="100%" href="{meta["poster"]}"/></svg>'
    return {'path':path,'data':raw,'uri':'data:image/svg+xml;base64,'+base64.b64encode(poster.encode()).decode(),
            'video':digest+'.mp4','metadata':meta,'width':meta['width'],'height':meta['height']}

def decorate(svg,pictures,root):
    videos={p['uri']:p for p in pictures if p.get('video')}
    if not videos:return svg
    directory=root/'assets/diy-media';directory.mkdir(parents=True,exist_ok=True)
    if directory.is_symlink():raise ValueError('视频目录不能是链接。')
    for p in videos.values():
        target=directory/p['video']
        if target.is_symlink() or sidecar(target).is_symlink():raise ValueError('视频文件不能是链接。')
        with PUBLISH_LOCK:
            if not target.exists():
                temp=target.with_suffix('.mp4.tmp');temp.write_bytes(p['data']);temp.replace(target)
            if not sidecar(target).exists():
                sidecar(target).write_text(json.dumps(p['metadata']),encoding='utf-8')
    doc=ET.fromstring(svg)
    for el in doc.iter(NS+'image'):
        p=videos.get(el.get('href'))
        if p:el.set('data-diy-video','diy-media/'+p['video'])
    return ET.tostring(doc,encoding='unicode')

def entry(slot):
    key=slot['id']
    if key=='home':selector='[data-conversation-region="chat"]';pseudo='before'
    elif key=='main-sidebar':selector='._2H3hWW_root:not(._2H3hWW_collapsed) ._2H3hWW_footArea';pseudo='before'
    elif key=='settings-sidebar':selector='[data-shortcut-modal="settings"].wCInkW_panel>nav';pseudo='after'
    else:
        selector=f'[data-shortcut-modal="settings"].wCInkW_panel:has(>nav .wCInkW_navCell:nth-child({slot["navIndex"]})[aria-current="true"]) .wCInkW_options'
        pseudo='after'
    return {'id':key,'selector':selector,'pseudo':pseudo,'src':'diy-generated/'+key+'.svg'}

def recover(skin,ref):
    if not re.fullmatch(r'diy-media/[a-f0-9]{64}\.mp4',ref):raise ValueError('无效的皮肤视频路径。')
    path=skin/'assets'/ref
    for candidate in (path,*path.parents):
        if candidate.is_symlink() or (hasattr(candidate,'is_junction') and candidate.is_junction()):raise ValueError('视频路径不能是链接。')
    picture=load(path)
    if picture['video']!=path.name:raise ValueError('皮肤视频校验失败。')
    return picture
