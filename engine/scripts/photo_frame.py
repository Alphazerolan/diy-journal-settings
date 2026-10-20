"""Fit the paper and its tape anchors to each photo without cropping or stretching."""
import base64,math,re
import xml.etree.ElementTree as ET
import photo_caption
from image_dimensions import image_size

NS='{http://www.w3.org/2000/svg}'

def dimensions(uri):
    header,encoded=uri.split(',',1)
    suffix={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp','image/gif':'.gif',
            'image/bmp':'.bmp','image/svg+xml':'.svg'}[header[5:].split(';')[0]]
    if not header.endswith(';base64'):raise ValueError('Photo must use an embedded image')
    w,h=image_size(base64.b64decode(encoded,validate=True),suffix)
    if not all(math.isfinite(n) and n>0 for n in (w,h)):raise ValueError('图片宽高必须为正数。')
    return w,h

def box(element):return tuple(float(element.get(k,'0')) for k in ('x','y','width','height'))

def set_box(element,values):
    for key,value in zip(('x','y','width','height'),values):element.set(key,format(value,'.8g'))

def adapt(template,uris,source,adjustments=None,borders=None,caption_size=16):
    doc=ET.fromstring(template)
    adjustments=adjustments or [{'x':0,'y':0,'angle':None} for _ in range(2)]
    borders=borders or [{'width':'narrow','write':False,'text':''} for _ in range(2)]
    _,_,canvas_w,canvas_h=map(float,doc.get('viewBox').split())
    transforms=[]
    parents={child:parent for parent in doc.iter() for child in parent}
    photos=[e for e in doc.iter(NS+'image') if e.get('href')=='{{IMAGE}}']
    if len(photos)!=len(uris):raise ValueError('照片布局数量不匹配。')
    for index,(photo,uri) in enumerate(zip(photos,uris)):
        parent=parents[photo]
        frame=next(e for e in parent if e.tag==NS+'rect' and not e.get('fill','').startswith('url('))
        ox,oy,ow,oh=box(frame);ix,iy,iw,ih=box(photo)
        border=min(ix-ox,iy-oy)
        if border<=0:raise ValueError('照片模板白边尺寸无效。')
        option=borders[index];wide=option['width']=='wide'
        if wide:border*=1.6
        bottom=border*4 if wide else border
        pw,ph=dimensions(uri)
        scale=min((ow-2*border)/pw,(oh-border-bottom)/ph)
        w,h=pw*scale+2*border,ph*scale+border+bottom
        cx,cy=ox+ow/2,oy+oh/2
        x,y=cx-w/2,cy-h/2
        for rect in parent:
            if rect.tag==NS+'rect' and box(rect)==(ox,oy,ow,oh):set_box(rect,(x,y,w,h))
        frame.set('data-diy-frame',str(index+1));frame.set('data-diy-border',str(border))
        set_box(photo,(x+border,y+border,w-2*border,h-border-bottom))
        photo.set('href',uri);photo.set('preserveAspectRatio','xMidYMid meet')
        if wide and option['write'] and option['text'].strip():
            # Compensate photo zoom so differently sized photos share a readable size.
            size=min(caption_size/(adjustments[index].get('scale',100)/100),bottom/1.15)
            rows=photo_caption.lines(option['text'],(w-4*border)/size,max(1,min(2,int(bottom/(size*1.15)))))
            text=ET.SubElement(parent,NS+'text',{'data-diy-caption':str(index+1),'x':str(cx),'y':str(y+h-bottom/2),'text-anchor':'middle','dominant-baseline':'central','fill':'#28506d','font-family':'KaiTi, STKaiti, cursive','font-size':str(size),'aria-label':option['text']})
            for line_number,line in enumerate(rows):
                ET.SubElement(text,NS+'tspan',{'x':str(cx),'dy':str(-(len(rows)-1)*.575 if line_number==0 else 1.15)+'em'}).text=line
        rotation=re.search(r'rotate\(([-+\d.]+)',parent.get('transform',''))
        angle=float(rotation.group(1)) if rotation else 0
        if rotation:parent.set('transform',f'rotate({angle} {cx} {cy})')
        if source=='usage':
            tapes=[e for e in parent.iter() if e.get('data-diy-tape')]
        else:tapes=[e for e in doc.iter() if e.get('data-diy-tape')]
        tape_scale=min(1,w/ow,h/oh)
        for number,tape in enumerate(tapes):
            if source=='usage':
                # Each photo has two opposite corner tapes, inside its rotating group.
                holder=parents[tape]
                old=holder.get('transform','')
                tilt=re.search(r'rotate\(([-+\d.]+)',old).group(1)
                right=(number==1) if index==0 else (number==0)
                ax=x+w-border if right else x+border
                ay=y+border if number==0 else y+h-border
                holder.set('transform',f'translate({ax} {ay}) scale({tape_scale}) rotate({tilt})')
                continue
            if source in ('center','models','presets'):
                ax,ay=cx,y+border*.2
            else:
                ax=x+w*.13 if number==0 else x+w*.92
                ay=y+border*.2 if number==0 else y+h-border*.2
            # Root-level tapes track the rotated frame edge while retaining their own tilt.
            radians=math.radians(angle)
            ax,ay=cx+(ax-cx)*math.cos(radians)-(ay-cy)*math.sin(radians),cy+(ax-cx)*math.sin(radians)+(ay-cy)*math.cos(radians)
            old=tape.get('transform','')
            pivot=re.search(r'rotate\([-+\d.]+\s+([-+\d.]+)\s+([-+\d.]+)\)',old)
            tx,ty=(float(pivot[1]),float(pivot[2])) if pivot else (ox+ow/2,oy)
            tape.set('transform',f'translate({ax} {ay}) scale({tape_scale}) translate({-tx} {-ty}) '+old)
        if source=='plugins':
            backing=next(e for e in doc if e.tag==NS+'path' and not e.get('data-diy-tape'))
            backing.set('transform',f'translate({x} {y}) scale({w/ow} {h/oh}) translate({-ox} {-oy})')
        setting=adjustments[index];delta=0 if setting['angle'] is None else setting['angle']-angle
        transform=f'translate({setting["x"]*canvas_w/100} {setting["y"]*canvas_h/100}) rotate({delta} {cx} {cy})'
        transform+=f' translate({cx} {cy}) scale({setting.get("scale",100)/100}) translate({-cx} {-cy})'
        transforms.append((parent,transform))
    # Move each entire collage, keeping its white edge, backing and tape together.
    for index,(parent,transform) in enumerate(transforms):
        wrapper=ET.Element(NS+'g',{'data-diy-adjustment':str(index+1),'transform':transform})
        children=[parent] if source=='usage' else [e for e in doc if e.tag!=NS+'defs']
        position=list(doc).index(children[0])
        for child in children:doc.remove(child);wrapper.append(child)
        doc.insert(position,wrapper)
    return ET.tostring(doc,encoding='unicode')
