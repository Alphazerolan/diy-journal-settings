"""Fluid home photo canvas: percentage geometry, undistorted cover images."""
import html
import photo_caption


def render(uris, style_id, colors, patterns, palettes, adjustments, angles, borders=None):
    palette={p['id']:p for p in palettes}
    borders=borders or [{'width':'narrow','write':False,'text':''} for _ in range(2)]
    defs=[]
    for i,(color,kind) in enumerate(zip(colors,patterns)):
        p=palette[color]
        detail={
            'solid':'',
            'gingham':f'<path d="M0 2.5h10M2.5 0v10" stroke="{p["ink"]}" stroke-width="5" opacity=".5"/>',
            'dots':f'<circle cx="5" cy="5" r="1.3" fill="{p["ink"]}"/>',
            'stripe':f'<path d="M-5 5 5-5M0 10 10 0M5 15 15 5" stroke="{p["ink"]}" stroke-width="3" opacity=".65"/>'
        }[kind]
        defs.append(f'<pattern id="home-tape-{i}" width="10" height="10" patternUnits="userSpaceOnUse"><rect width="10" height="10" fill="{p["base"]}"/>{detail}</pattern>')
    defs.append('<pattern id="home-backing" width="18" height="18" patternUnits="userSpaceOnUse"><rect width="18" height="18" fill="#dce8e6"/><path d="M0 0H18M0 0V18" stroke="#9ebdc6" opacity=".4"/></pattern>')
    parts=[]
    dual=style_id==8
    for i,uri in enumerate(uris):
        x,y,w,h=(4+i*48,7,44,86) if dual else (2.5,3,95,94)
        cx,cy=x+w/2,y+h/2
        a=adjustments[i];angle=angles[i] if a['angle'] is None else a['angle']
        transform=f'translate({a["x"]}%,{a["y"]}%) rotate({angle}deg) scale({a["scale"]/100})'
        parts.append(f'<g data-diy-adjustment="{i+1}" style="transform-box:view-box;transform-origin:{cx}% {cy}%;transform:{transform}">')
        if style_id==6:
            parts.append(f'<rect x="{x-1}%" y="{y-1}%" width="{w+2}%" height="{h+2}%" fill="url(#home-backing)" stroke="#a6bdc5"/>')
        option=borders[i];wide=option['width']=='wide';bottom=12 if wide else 0
        edge='2%' if wide else '1.2%'
        parts.append(f'<rect x="{x}%" y="{y}%" width="{w}%" height="{h}%" fill="#fffdf5"/>')
        parts.append(f'<image data-diy-photo="{i+1}" x="{x}%" y="{y}%" width="{w}%" height="{h-bottom}%" href="{html.escape(uri,quote=True)}" preserveAspectRatio="xMidYMid slice"/>')
        parts.append(f'<rect data-diy-frame="{i+1}" x="{x}%" y="{y}%" width="{w}%" height="{h}%" fill="none" stroke="#fffdf5" stroke-width="{edge}"/>')
        if wide and option['write'] and option['text'].strip():
            size=1.3/(a['scale']/100)
            rows=photo_caption.lines(option['text'],(w-4)*.65/size)
            parts.append(f'<text data-diy-caption="{i+1}" x="{cx}%" y="{y+h-bottom/2}%" text-anchor="middle" dominant-baseline="central" fill="#28506d" font-family="KaiTi, STKaiti, cursive" font-size="{size}%" aria-label="{html.escape(option["text"],quote=True)}">')
            for line_number,line in enumerate(rows):
                dy=-(len(rows)-1)*.575 if line_number==0 else 1.15
                parts.append(f'<tspan x="{cx}%" dy="{dy}em">{html.escape(line)}</tspan>')
            parts.append('</text>')
        single=style_id in (1,4,5,6)
        anchors=[(cx-7,y-3,0)] if single else [(x-1,y-3,-15),(x+w-13,y+h-3,-15)]
        for j,(tx,ty,tilt) in enumerate(anchors):
            group=i if dual else j
            parts.append(f'<svg x="{tx}%" y="{ty}%" width="14%" height="6%" viewBox="0 0 120 36" overflow="visible" preserveAspectRatio="xMidYMid meet"><path data-diy-tape="{group+1}" data-diy-pattern="{patterns[group]}" d="M2 4 118 2 115 9 119 15 115 22 118 31 2 33 5 25 1 18 5 11Z" fill="url(#home-tape-{group})" opacity=".92" transform="rotate({tilt} 60 18)"/></svg>')
        parts.append('</g>')
    # Deliberately no viewBox or fixed intrinsic ratio: both dimensions come from
    # the containing region. Root viewport clips only at the available area.
    return '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" overflow="hidden" data-diy-fluid-home="true"><defs>'+''.join(defs)+'</defs>'+''.join(parts)+'</svg>'
