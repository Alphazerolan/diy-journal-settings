"""Import a locally selected photo without changing or removing existing images."""
from pathlib import Path
import base64,json,uuid,os,re,hashlib
import xml.etree.ElementTree as ET
import build

MAX_IMAGE_BYTES=20*1024*1024


def plain(path):
    for p in (path,*path.parents):
        if p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()):
            raise ValueError('图片路径不能是链接。')


def restore(root,slot,source):
    """Recover embedded photos from the applied skin or immutable bundled presets."""
    if source not in ('current','preset'):raise ValueError('无效的恢复来源。')
    if not re.fullmatch(r'[a-z0-9-]+',slot['id']):raise ValueError('无效图片区域。')
    if source=='current':
        skin=Path(os.environ.get('DIY_JOURNAL_SKIN_DIR') or str(Path(os.environ.get('DSH_HOME',str(Path.home()/'.dsh')))/'skins/diy-journal'))
    else:
        value=os.environ.get('DIY_JOURNAL_BUNDLED_SKIN_DIR')
        if not value:raise ValueError('预设图片来源不可用，请从 DSH 设置中重新打开样式菜单。')
        skin=Path(value)
    asset=skin/'assets/diy-generated'/f"{slot['id']}.svg"
    plain(skin/'skin.json');plain(asset)
    if json.loads((skin/'skin.json').read_text(encoding='utf-8')).get('id')!='diy-journal':raise ValueError('恢复来源不是 DIY 手账本。')
    if not asset.is_file() or asset.stat().st_size>64*1024*1024:raise ValueError('未找到有效的皮肤图片。')
    doc=ET.fromstring(asset.read_bytes());parents={c:p for p in doc.iter() for c in p}
    images=[]
    for el in doc.iter():
        if el.tag.split('}')[-1]!='image' or el.get('data-diy-tape'):continue
        uri=el.get('href',el.get('{http://www.w3.org/1999/xlink}href',''))
        if not uri:continue
        m=re.fullmatch(r'data:image/(png|jpeg|webp|gif|bmp|svg\+xml);base64,([A-Za-z0-9+/=\s]+)',uri)
        if not m:raise ValueError('皮肤图片不是可恢复的内嵌图片。')
        order=el.get('data-diy-photo');parent=el
        while order is None and parent in parents:
            parent=parents[parent];order=parent.get('data-diy-adjustment')
        raw=base64.b64decode(re.sub(r'\s+','',m[2]),validate=True)
        if not raw or len(raw)>MAX_IMAGE_BYTES:raise ValueError('皮肤中的单张图片超过 20 MB 或为空。')
        ext={'jpeg':'jpg','svg+xml':'svg'}.get(m[1],m[1])
        images.append((int(order) if order else len(images)+1,raw,ext))
    images.sort(key=lambda x:x[0]);images=images[:1 if slot['id'].endswith('sidebar') else 2]
    folder=build.safe_child(root/'DIY图片',slot['folder']);plain(folder)
    manifest=folder/'图片选择.json';plain(manifest)
    entries=[];created=[]
    try:
        for i,(_,raw,ext) in enumerate(images):
            filename=f'恢复-{source}-{hashlib.sha256(raw).hexdigest()[:20]}.{ext}'
            target=folder/filename;plain(target)
            if target.exists():
                if target.read_bytes()!=raw:raise ValueError('已有恢复图片内容不匹配。')
            else:target.write_bytes(raw);created.append(target)
            build.load_picture(target)
            w,h=build.image_size(raw,'.'+ext)
            if w<=0 or h<=0:raise ValueError('无法识别恢复图片尺寸。')
            entries.append({'file':filename,'name':('皮肤现用' if source=='current' else '鲸鱼娘预设')+f'-{i+1}.{ext}'})
        write_selection(manifest,{'mode':'selected','pictures':(entries+[None,None])[:2]})
    except Exception:
        for p in created:p.unlink(missing_ok=True)
        raise
    return build.picture_labels(folder)


def open_folder(root,slot,opener=None):
    """Open only a known photo region, without changing its photo selection."""
    base=root/'DIY图片'
    raw=base/slot['folder']
    plain(raw)
    folder=build.safe_child(base,slot['folder'])
    if not folder.is_dir():raise ValueError('图片文件夹不存在。')
    if opener is not None:opener(str(folder))
    elif os.name=='nt':os.startfile(str(folder))
    else:
        import subprocess,sys
        subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(folder)],
                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return {'ok':True,'message':'已打开当前区域的图片文件夹。放入新图片后，可点击“选择图片”选用；当前选图不会改变。'}


def select(root,slot,payload):
    folder=build.safe_child(root/'DIY图片',slot['folder'])
    manifest=folder/'图片选择.json'
    if manifest.is_symlink():raise ValueError('图片选择文件不能是链接。')
    if payload.get('mode')=='folder':
        data=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
        data['mode']='folder'
        write_selection(manifest,data)
        return build.picture_labels(folder)
    index=payload.get('index');name=payload.get('name');encoded=payload.get('data')
    if type(index) is not int or index not in (0,1) or (index==1 and slot['id'].endswith('sidebar')):raise ValueError('无效照片位置。')
    if not isinstance(name,str) or not name or len(name)>255:raise ValueError('无效图片名称。')
    ext=Path(name).suffix.lower()
    if ext not in build.MIMES:raise ValueError('请选择 PNG、JPG、WebP、GIF、BMP 或 SVG 图片。')
    if not isinstance(encoded,str) or len(encoded)>MAX_IMAGE_BYTES*4//3+4:raise ValueError('单张图片不能超过 20 MB。')
    try:raw=base64.b64decode(encoded,validate=True)
    except ValueError:raise ValueError('图片内容无法读取。')
    if not raw or len(raw)>MAX_IMAGE_BYTES:raise ValueError('图片为空或超过 20 MB。')
    current=build.picture_files(folder)[:2];labels=build.picture_labels(folder)
    if index==1 and not current:raise ValueError('请先选择第一张图片。')
    entries=[{'file':p.name,'name':labels[i]} for i,p in enumerate(current)]
    while len(entries)<2:entries.append(None)
    identity=uuid.uuid4().hex
    temp=folder/('.import-'+identity+ext);destination=folder/('自选-'+identity+ext)
    try:
        temp.write_bytes(raw)
        build.load_picture(temp)
        w,h=build.image_size(raw,ext)
        if w<=0 or h<=0:raise ValueError('无法识别图片尺寸。')
        os.replace(temp,destination)
        entries[index]={'file':destination.name,'name':name}
        write_selection(manifest,{'mode':'selected','pictures':entries})
    except Exception:
        temp.unlink(missing_ok=True);destination.unlink(missing_ok=True)
        raise
    return build.picture_labels(folder)


def write_selection(path,data):
    temp=path.with_name('.selection-'+uuid.uuid4().hex+'.tmp')
    try:
        temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)
