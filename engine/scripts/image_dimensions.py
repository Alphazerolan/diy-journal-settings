"""Image dimensions shared by the builder and adaptive photo frames."""
import struct,re,math
import xml.etree.ElementTree as ET

def image_size(data,suffix):
    w,h=raw_image_size(data,suffix)
    if suffix in ('.jpg','.jpeg') and jpeg_orientation(data) in (5,6,7,8):w,h=h,w
    if not all(math.isfinite(n) and n>0 for n in (w,h)):raise ValueError('图片宽高必须为正数。')
    return w,h

def jpeg_orientation(data):
    at=2
    while at+4<=len(data):
        if data[at]!=255:break
        marker=data[at+1];at+=2
        if marker in (0xDA,0xD9):break
        length=int.from_bytes(data[at:at+2],'big')
        if length<2:break
        segment=data[at+2:at+length];at+=length
        if marker!=0xE1 or not segment.startswith(b'Exif\x00\x00'):continue
        tiff=segment[6:];order='little' if tiff[:2]==b'II' else 'big'
        offset=int.from_bytes(tiff[4:8],order)
        if offset+2>len(tiff):continue
        count=int.from_bytes(tiff[offset:offset+2],order)
        for i in range(min(count,(len(tiff)-offset-2)//12)):
            entry=tiff[offset+2+i*12:offset+14+i*12]
            if int.from_bytes(entry[:2],order)==0x112 and int.from_bytes(entry[2:4],order)==3:
                return int.from_bytes(entry[8:10],order)
    return 1

def raw_image_size(data, suffix):
    if suffix=='.png':return struct.unpack('>II',data[16:24])
    if suffix in ('.jpg','.jpeg'):
        at=2
        while at<len(data):
            if data[at]!=255:at+=1;continue
            while at<len(data) and data[at]==255:at+=1
            marker=data[at];at+=1
            if marker in (0xD8,0xD9):continue
            length=int.from_bytes(data[at:at+2],'big')
            if marker in (0xC0,0xC1,0xC2,0xC3,0xC5,0xC6,0xC7,0xC9,0xCA,0xCB,0xCD,0xCE,0xCF):
                h,w=struct.unpack('>HH',data[at+3:at+7]);return w,h
            if length<2:break
            at+=length
    if suffix=='.gif':return struct.unpack('<HH',data[6:10])
    if suffix=='.bmp':return abs(struct.unpack('<i',data[18:22])[0]),abs(struct.unpack('<i',data[22:26])[0])
    if suffix=='.webp':
        kind=data[12:16]
        if kind==b'VP8X':return 1+int.from_bytes(data[24:27],'little'),1+int.from_bytes(data[27:30],'little')
        if kind==b'VP8 ':return int.from_bytes(data[26:28],'little')&0x3fff,int.from_bytes(data[28:30],'little')&0x3fff
        if kind==b'VP8L':
            bits=int.from_bytes(data[21:25],'little');return (bits&0x3fff)+1,((bits>>14)&0x3fff)+1
    if suffix=='.svg':
        doc=ET.fromstring(data)
        def length(value):
            match=re.fullmatch(r'\s*([\d.]+)\s*(px|in|cm|mm|pt|pc)?\s*',value or '')
            return float(match[1])*{'px':1,'in':96,'cm':96/2.54,'mm':96/25.4,'pt':96/72,'pc':16,None:1}[match[2]] if match else None
        width,height=length(doc.get('width')),length(doc.get('height'))
        if width is not None and height is not None:return width,height
        if doc.get('viewBox'):
            _,_,w,h=map(float,doc.get('viewBox').replace(',',' ').split())
            return (width,width*h/w) if width is not None else (height*w/h,height) if height is not None else (w,h)
        return width or 300,height or 150
    raise ValueError('Cannot read image dimensions; please use PNG or JPEG.')
