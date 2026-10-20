"""Reusable SVG photo layouts and per-folder choices; no external dependencies."""
import json, base64, copy, math, re
import xml.etree.ElementTree as ET
import photo_frame, home_canvas

CONFIG_NAME='样式.json'

def catalog(root):
    return json.loads((root/'styles.json').read_text(encoding='utf-8'))

def available(root,slot,choices=None):
    choices=choices or catalog(root)
    current=read_choice(root,slot,choices)
    return [s for s in choices if s['id']!=2 and (not s.get('retired') or s['id']==current) and not (s['id']==8 and slot['id'] in ('settings-sidebar','main-sidebar')) and (s['id']!=10 or slot['id']=='settings-sidebar')]

def config(style_id, choices, tape_colors=None, swap_photos=False, tape_patterns=None, photo_adjustments=None, photo_borders=None, front_photo='right'):
    return {'版本':8,'前景照片':validate_front(front_photo),'当前样式':style_id,'白边设置':validate_borders(photo_borders if photo_borders is not None else default_borders()),'调换双照片':validate_swap(swap_photos),'胶带颜色':tape_colors or ['blue','orange'],'胶带纹样':tape_patterns or default_patterns(style_id),'照片调整':validate_adjustments(photo_adjustments if photo_adjustments is not None else default_adjustments()),'说明':'照片布局、胶带纹样与颜色独立选择。照片调整的 x/y 为相对画布的百分比偏移，angle 为角度，null 跟随布局；scale 为缩放百分比，100 为原大小。无照片时隐藏照片、白边和胶带。',
            '可选样式':{str(s['id']):s['name'] for s in choices}}

def default_adjustments():return [{'x':0,'y':0,'angle':None,'scale':100} for _ in range(2)]

def default_borders():return [{'width':'narrow','write':False,'text':''} for _ in range(2)]

def validate_borders(values):
    if not isinstance(values,list) or len(values)!=2:raise ValueError('白边设置需要两组配置。')
    for item in values:
        if not isinstance(item,dict) or set(item)!={'width','write','text'}:raise ValueError('白边设置字段无效。')
        if item['width'] not in ('narrow','wide') or type(item['write']) is not bool:raise ValueError('白边样式无效。')
        if not isinstance(item['text'],str) or len(item['text'])>40 or any(ord(c)<32 for c in item['text']):raise ValueError('题字限 40 字以内，不能包含换行或控制字符。')
    return copy.deepcopy(values)

def read_borders(root,slot):
    p=root/'DIY图片'/slot['folder']/CONFIG_NAME
    value=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
    return validate_borders(value.get('白边设置',default_borders()))

def validate_adjustments(values):
    if not isinstance(values,list) or len(values)!=2:raise ValueError('照片调整需要两组设置。')
    for item in values:
        if not isinstance(item,dict) or set(item) not in ({'x','y','angle'},{'x','y','angle','scale'}):raise ValueError('照片调整字段无效。')
        for key,limit in (('x',50),('y',50),('angle',30)):
            value=item[key]
            if key=='angle' and value is None:continue
            if type(value) not in (int,float) or not math.isfinite(value) or abs(value)>limit:raise ValueError('照片位置或角度超出范围。')
        scale=item.get('scale',100)
        if type(scale) not in (int,float) or not math.isfinite(scale) or not 25<=scale<=250:raise ValueError('照片缩放范围为 25%–250%。')
    result=copy.deepcopy(values)
    for item in result:item.setdefault('scale',100)
    return result

def read_adjustments(root,slot):
    p=root/'DIY图片'/slot['folder']/CONFIG_NAME
    value=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
    return validate_adjustments(value.get('照片调整',default_adjustments()))

def layout_geometry(root,slot,style_id):
    if style_id in (0,1,10):return {'width':slot['width'],'height':slot['height'],'angles':[0]}
    choice=next(s for s in catalog(root) if s['id']==style_id)
    doc=ET.fromstring((root/choice['template']).read_text(encoding='utf-8'))
    _,_,w,h=map(float,doc.get('viewBox').split());ns='{http://www.w3.org/2000/svg}'
    parents={c:p for p in doc.iter() for c in p};angles=[]
    for image in doc.iter(ns+'image'):
        match=re.search(r'rotate\(([-+\d.]+)',parents[image].get('transform',''))
        angles.append(float(match[1]) if match else 0)
    return {'width':w,'height':h,'angles':angles}

def patterns(root):return json.loads((root/'tape-patterns.json').read_text(encoding='utf-8'))

def default_patterns(style_id):
    pattern={4:'stripe',5:'dots',7:'stripe',9:'dots'}.get(style_id,'gingham')
    return [pattern,pattern]

def validate_patterns(root,values):
    allowed={p['id'] for p in patterns(root)}
    if not isinstance(values,list) or len(values)!=2 or any(not isinstance(v,str) or v not in allowed for v in values):
        raise ValueError('胶带纹样需填写两个有效纹样编号。')
    return list(values)

def read_patterns(root,slot):
    p=root/'DIY图片'/slot['folder']/CONFIG_NAME
    value=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
    return validate_patterns(root,value['胶带纹样']) if '胶带纹样' in value else default_patterns(read_choice(root,slot))

def validate_swap(value):
    if type(value) is not bool:raise ValueError('调换双照片必须为 true 或 false。')
    return value

def validate_front(value):
    if not isinstance(value,str) or value not in ('left','right'):raise ValueError('前景照片必须选择左侧或右侧。')
    return value

def read_front(root,slot):
    p=root/'DIY图片'/slot['folder']/CONFIG_NAME
    data=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
    return validate_front(data.get('前景照片','right'))

def stack_photos(svg,style_id,front_photo):
    if style_id!=8 or front_photo=='right':return svg
    doc=ET.fromstring(svg)
    # Reorder the entire left collage, including its frame, caption and tapes.
    for parent in doc.iter():
        left=next((e for e in parent if e.get('data-diy-adjustment')=='1'),None)
        if left is not None and any(e.get('data-diy-adjustment')=='2' for e in parent):
            parent.remove(left);parent.append(left);break
    return ET.tostring(doc,encoding='unicode')

def read_swap(root,slot):
    p=root/'DIY图片'/slot['folder']/CONFIG_NAME
    data=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
    return validate_swap(data.get('调换双照片',False))

def palettes(root):return json.loads((root/'tape-colors.json').read_text(encoding='utf-8'))

def validate_colors(root, colors):
    allowed={x['id'] for x in palettes(root)}
    if not isinstance(colors,list) or len(colors)!=2 or any(not isinstance(c,str) or c not in allowed for c in colors):
        raise ValueError('胶带颜色需填写两个有效颜色编号。')
    return list(colors)

def source_name(root,slot,style_id):
    if style_id==1:return 'center'
    if style_id==10:return 'sticker'
    choice=next(s for s in catalog(root) if s['id']==style_id)
    return (slot['template'] if choice['template']=='original' else choice['template']).split('/')[-1].replace('.svg','')

def tape_count(root,slot,style_id):
    if style_id in (0,10):return 0
    return 1 if source_name(root,slot,style_id) in ('center','models','presets','plugins','settings-sidebar') else 2

def read_colors(root,slot):
    p=root/'DIY图片'/slot['folder']/CONFIG_NAME
    value=json.loads(p.read_text(encoding='utf-8-sig')) if p.exists() else {}
    if '胶带颜色' in value:return validate_colors(root,value['胶带颜色'])
    # Migrate old choices using the former design palette instead of resetting their appearance.
    source=source_name(root,slot,read_choice(root,slot))
    return {'models':['green','green'],'presets':['navy','navy'],'archive':['navy','navy'],
            'plugins':['red','red'],'home':['blue','orange'],'usage':['blue','orange'],
            'web':['blue','orange']}.get(source,['blue','blue'])

def colorize(root,template,source,colors,tape_patterns):
    colors=validate_colors(root,colors);palette={p['id']:p for p in palettes(root)}
    tape_patterns=validate_patterns(root,tape_patterns)
    doc=ET.fromstring(template);ns='{http://www.w3.org/2000/svg}'
    patterns={p.get('id'):p for p in doc.iter(ns+'pattern') if p.get('id') not in ('grain','paper')}
    defs=doc.find(ns+'defs')
    marks=[e for e in doc.iter() if e.get('fill','').startswith('url(#') and e.get('fill')[5:-1] in patterns]
    for i,mark in enumerate(marks):
        group=(0 if source in ('center','models','presets','plugins','settings-sidebar') else (i//2 if source=='usage' else i))
        group=min(group,1);p=palette[colors[group]];pat=copy.deepcopy(patterns[mark.get('fill')[5:-1]])
        # The first patterned shape in plugins is backing paper, not tape.
        backing=source=='plugins' and i==0
        original=('dots' if pat.find(ns+'circle') is not None else 'stripe' if source in ('models','web') else 'gingham')
        kind=tape_patterns[group]
        if not backing and kind!=original:
            details={'solid':'','gingham':'<path d="M0 2.5h10M2.5 0v10" stroke="#000" stroke-width="5" opacity=".5"/>',
                     'dots':'<circle cx="5" cy="5" r="1.3" fill="#000"/>',
                     'stripe':'<path d="M-5 5 5-5M0 10 10 0M5 15 15 5" stroke="#000" stroke-width="3" opacity=".65"/>'}
            pat=ET.fromstring('<pattern xmlns="http://www.w3.org/2000/svg" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#fff"/>'+details[kind]+'</pattern>')
        pid='diy-tape-'+str(i);pat.set('id',pid)
        for node in pat.iter():
            for attr in ('fill','stroke'):
                if node.get(attr,'').startswith('#'):
                    node.set(attr,p['base'] if attr=='fill' and node.tag==ns+'rect' else p['ink'])
        defs.append(pat);mark.set('fill','url(#'+pid+')')
        if not backing:
            mark.set('data-diy-tape',str(group+1));mark.set('data-diy-pattern',kind)
    return ET.tostring(doc,encoding='unicode')

def home_tape(root,color):
    p=next(p for p in palettes(root) if p['id']==color)
    doc=ET.fromstring((root/'assets/journal-tape-blue-v80.svg').read_text(encoding='utf-8'))
    for e in doc.iter():
        if e.get('fill')=='#83b7df':e.set('fill',p['ink'])
    return ET.tostring(doc,encoding='unicode')

def read_choice(root, slot, choices=None):
    choices=choices or catalog(root)
    p=root/'DIY图片'/slot['folder']/CONFIG_NAME
    if not p.exists():return 1
    try:
        value=json.loads(p.read_text(encoding='utf-8-sig'))['当前样式']
        if type(value) is int and (value==2 or (value==8 and slot['id'] in ('settings-sidebar','main-sidebar'))):return 1
        if type(value) is not int or value not in {s['id'] for s in choices}:raise ValueError('unknown style')
        return value
    except (ValueError,KeyError,TypeError) as e:
        raise ValueError(str(p)+'：当前样式必须是 styles.json 中的样式编号。') from e

def centered(w,h):
    # Center the paper and the photo independently; use the complete image without cropping.
    x,y=w*.09,h*.09;pw,ph=w*.82,h*.82;b=min(w,h)*.025
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">
<defs><filter id="center-shadow" x="-15%" y="-15%" width="130%" height="140%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#284b62" flood-opacity=".18"/></filter>
<pattern id="center-tape" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="#d2edf4" fill-opacity=".94"/><path d="M0 2.5h10M2.5 0v10" stroke="#6db4d2" stroke-width="5" opacity=".5"/></pattern></defs>
<rect x="{x}" y="{y}" width="{pw}" height="{ph}" fill="#fffdf5" stroke="#d8d4c7" filter="url(#center-shadow)"/>
<image x="{x+b}" y="{y+b}" width="{pw-2*b}" height="{ph-2*b}" preserveAspectRatio="xMidYMid meet" href="{{{{IMAGE}}}}"/>
<path d="M{w*.40} {y-b}h{w*.20}l{-b*.4} {b*.6} {b*.4} {b*.6} {-b*.4} {b*.8}h{-w*.20}l{b*.4} {-b*.7} {-b*.4} {-b*.6}Z" fill="url(#center-tape)"/>
</svg>'''

def render(root, slot, style_id, uri, tape_colors=None, second_uri=None, swap_photos=False, tape_patterns=None, photo_adjustments=None, photo_borders=None, front_photo=None):
    if style_id not in {s['id'] for s in available(root,slot)}:raise ValueError('该区域不支持此样式。')
    if style_id==0:return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 560 340"><rect x="120" y="65" width="320" height="210" rx="12" fill="#f6f3e8" stroke="#abc0c8" stroke-dasharray="8 7"/><path d="m225 215 55-60 55 60M240 120l80 100" stroke="#9cb5c0" stroke-width="5" fill="none"/><text x="280" y="305" text-anchor="middle" fill="#52758a" font-size="20">不设置照片</text></svg>'
    tape_colors=tape_colors or read_colors(root,slot)
    tape_patterns=tape_patterns or read_patterns(root,slot)
    adjustments=validate_adjustments(photo_adjustments if photo_adjustments is not None else read_adjustments(root,slot))
    if style_id==10:
        # Preserve the PNG alpha; a sticker has no rectangular photo paper or tape.
        w,h=slot['width'],slot['height'];a=adjustments[0]
        ns='http://www.w3.org/2000/svg'
        canvas=ET.Element('{'+ns+'}svg',{'width':str(w),'height':str(h),'viewBox':f'0 0 {w} {h}'})
        transform=f'translate({w/2+a["x"]*w/100} {h/2+a["y"]*h/100}) rotate({a["angle"] or 0}) scale({a["scale"]/100}) translate({-w/2} {-h/2})'
        group=ET.SubElement(canvas,'{'+ns+'}g',{'data-diy-adjustment':'1','transform':transform})
        ET.SubElement(group,'{'+ns+'}image',{'x':str(w*.05),'y':str(h*.05),'width':str(w*.9),'height':str(h*.9),'preserveAspectRatio':'xMidYMid meet','href':uri})
        return ET.tostring(canvas,encoding='unicode')
    borders=validate_borders(photo_borders if photo_borders is not None else read_borders(root,slot))
    front=validate_front(front_photo if front_photo is not None else read_front(root,slot))
    pair=[uri,second_uri or uri] if style_id==8 else [uri]
    if style_id==8 and validate_swap(swap_photos):pair.reverse()
    if slot['id']=='home':
        return stack_photos(home_canvas.render(pair,style_id,validate_colors(root,tape_colors),validate_patterns(root,tape_patterns),palettes(root),adjustments,layout_geometry(root,slot,style_id)['angles'],borders),style_id,front)
    choice=next(s for s in catalog(root) if s['id']==style_id)
    geometry=layout_geometry(root,slot,style_id)
    layout_scale=min(slot['width']/geometry['width'],slot['height']/geometry['height'])
    caption_size=16*slot['width']/min(slot['width'],slot['maxWidth'])/layout_scale
    if style_id==1:
        template=colorize(root,centered(slot['width'],slot['height']),'center',tape_colors,tape_patterns)
        template=photo_frame.adapt(template,pair,'center',adjustments,borders,caption_size)
    else:
        path=slot['template'] if choice['template']=='original' else choice['template']
        template=(root/path).read_text(encoding='utf-8')
        if source_name(root,slot,style_id)!='home':
            template=colorize(root,template,source_name(root,slot,style_id),tape_colors,tape_patterns)
        else:
            # Mirror the live home style's two tape overlays in the menu preview.
            w,h=slot['width'],slot['height']
            a=base64.b64encode(home_tape(root,tape_colors[0]).encode()).decode()
            b=base64.b64encode(home_tape(root,tape_colors[1]).encode()).decode()
            template=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><rect x="25" y="25" width="{w-50}" height="{h-50}" fill="#fffdf5"/><image x="40" y="40" width="{w-80}" height="{h-95}" preserveAspectRatio="xMidYMid slice" href="{{{{IMAGE}}}}"/><image data-diy-tape="1" width="180" height="85" href="data:image/svg+xml;base64,{a}"/><image data-diy-tape="2" x="{w-180}" y="{h-85}" width="180" height="85" href="data:image/svg+xml;base64,{b}"/></svg>'
        # Fit pre-existing layouts into the destination canvas without stretching their artwork.
        template=photo_frame.adapt(template,pair,source_name(root,slot,style_id),adjustments,borders,caption_size)
        inner=ET.fromstring(template)
        inner.set('x','0');inner.set('y','0');inner.set('width','100%');inner.set('height','100%')
        inner.set('preserveAspectRatio','xMidYMid meet')
        # Only the destination canvas clips the collage; the layout viewport must not.
        inner.set('overflow','visible')
        template=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {slot["width"]} {slot["height"]}">'+ET.tostring(inner,encoding='unicode')+'</svg>'
    # CSS backgrounds can give an SVG a viewport larger than its viewBox.
    # Clip in canvas coordinates, so <img> and background contain paint the same area.
    canvas=ET.fromstring(template)
    canvas.set('width',str(slot['width']));canvas.set('height',str(slot['height']))
    ns='{http://www.w3.org/2000/svg}'
    defs=ET.SubElement(canvas,ns+'defs')
    clip=ET.SubElement(defs,ns+'clipPath',{'id':'diy-canvas-clip','clipPathUnits':'userSpaceOnUse'})
    ET.SubElement(clip,ns+'rect',{'width':str(slot['width']),'height':str(slot['height'])})
    paint=ET.Element(ns+'g',{'clip-path':'url(#diy-canvas-clip)'})
    for child in list(canvas):
        if child.tag!=ns+'defs':canvas.remove(child);paint.append(child)
    canvas.append(paint)
    return stack_photos(ET.tostring(canvas,encoding='unicode'),style_id,front)

def sample_uri():
    # A neutral drawing only for previews, never copied into a user's photo folder.
    art='<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400"><rect width="600" height="400" fill="#dceef3"/><circle cx="445" cy="90" r="42" fill="#f5d891"/><path d="M0 300 160 135 360 330 480 200 600 300V400H0" fill="#9dc4b5"/><path d="M0 340 210 250 390 350 600 265V400H0" fill="#78a5b2"/></svg>'
    return 'data:image/svg+xml;base64,'+base64.b64encode(art.encode()).decode()
