"""Import a locally selected photo without changing or removing existing images."""
from pathlib import Path
import base64,json,uuid,os
import build

MAX_IMAGE_BYTES=20*1024*1024


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
