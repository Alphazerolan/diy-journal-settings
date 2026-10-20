"""Local-only style picker. Saves known folder configs, then uses the existing builder."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import argparse, base64, json, secrets, time, webbrowser, threading, hashlib
from collections import OrderedDict
import build, styles, scene_preview, mimetypes, photo_import

ROOT=build.ROOT


class SceneAssets:
    """Bounded, local, in-memory assets; keep large photos out of CSS declarations."""
    def __init__(self,token,limit=128*1024*1024):
        self.token=token;self.limit=limit;self.items=OrderedDict();self.size=0;self.lock=threading.Lock()

    def put(self,svg):
        data=svg.encode('utf-8')
        if len(data)>self.limit:raise ValueError('场景图片过大，请缩小图片后重试。')
        key=hashlib.sha256(data).hexdigest()+'.svg'
        with self.lock:
            if key not in self.items:self.items[key]=data;self.size+=len(data)
            self.items.move_to_end(key)
            while len(self.items)>32 or self.size>self.limit:
                _,old=self.items.popitem(last=False);self.size-=len(old)
        return '/scene-preview/'+self.token+'/'+key

    def get(self,key):
        with self.lock:
            data=self.items.get(key)
            if data is not None:self.items.move_to_end(key)
            return data

def save_choices(values, apply=True):
    slots=json.loads((ROOT/'slots.json').read_text(encoding='utf-8'))
    choices=styles.catalog(ROOT);ids={s['id'] for s in slots}
    if not isinstance(values,dict) or set(values)!=ids:raise ValueError('请为全部 14 个区域选择样式。')
    allowed={s['id'] for s in choices}
    selections={};colors={};swaps={};patterns={};adjustments={};borders={};fronts={}
    for s in slots:
        v=values[s['id']]
        fronts[s['id']]=styles.validate_front(v.get('frontPhoto',styles.read_front(ROOT,s))) if isinstance(v,dict) else styles.read_front(ROOT,s)
        borders[s['id']]=styles.validate_borders(v.get('photoBorders',styles.read_borders(ROOT,s))) if isinstance(v,dict) else styles.read_borders(ROOT,s)
        swaps[s['id']]=styles.validate_swap(v.get('swapPhotos',styles.read_swap(ROOT,s))) if isinstance(v,dict) else styles.read_swap(ROOT,s)
        adjustments[s['id']]=styles.validate_adjustments(v.get('photoAdjustments',styles.read_adjustments(ROOT,s))) if isinstance(v,dict) else styles.read_adjustments(ROOT,s)
        selections[s['id']]=v.get('style') if isinstance(v,dict) else v
        colors[s['id']]=styles.validate_colors(ROOT,v.get('tapeColors')) if isinstance(v,dict) else styles.read_colors(ROOT,s)
        patterns[s['id']]=styles.validate_patterns(ROOT,v.get('tapePatterns',styles.read_patterns(ROOT,s))) if isinstance(v,dict) else styles.read_patterns(ROOT,s)
    if any(type(v) is not int or v not in allowed for v in selections.values()):raise ValueError('未知样式编号。')
    for s in slots:
        if selections[s['id']] not in {x['id'] for x in styles.available(ROOT,s)}:raise ValueError(s['folder']+' 不支持此样式。')
    # Validate all photos before changing any saved choices.
    for s in slots:
        if selections[s['id']]!=0:build.pictures(ROOT/'DIY图片'/s['folder'],2 if selections[s['id']]==8 else 1)
    originals={};paths=[]
    try:
        for s in slots:
            p=ROOT/'DIY图片'/s['folder']/styles.CONFIG_NAME
            originals[p]=p.read_bytes() if p.exists() else None;paths.append(p)
            tmp=p.with_suffix('.json.tmp')
            tmp.write_text(json.dumps(styles.config(selections[s['id']],styles.available(ROOT,s,choices),colors[s['id']],swaps[s['id']],patterns[s['id']],adjustments[s['id']],borders[s['id']],fronts[s['id']]),ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(p)
        build.build()
    except Exception:
        for p in paths:
            if originals[p] is None:p.unlink(missing_ok=True)
            else:p.write_bytes(originals[p])
        raise
    if apply:
        try:build.install()
        except Exception as e:
            return {'ok':False,'saved':True,'message':'样式已保存并生成，但应用失败。请检查皮肤目录权限，然后重新点击保存并应用。'+str(e)}
    return {'ok':True,'message':'已保存并应用到 DIY手账本。请刷新 Harness 或重新选择该皮肤。' if apply else '样式已保存并生成。'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    token=secrets.token_urlsafe(32);activity=[time.monotonic()];closed=[False];save_lock=threading.Lock()
    scene_assets=SceneAssets(token)
    slots=json.loads((ROOT/'slots.json').read_text(encoding='utf-8'));slot_map={s['id']:s for s in slots}
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            # An idle browser preconnection must not occupy the server indefinitely.
            self.connection.settimeout(15)
        def log_message(self,*args):pass
        def reply(self,status,data,mime='application/json; charset=utf-8'):
            if not isinstance(data,bytes):data=json.dumps(data,ensure_ascii=False).encode('utf-8')
            self.send_response(status);self.send_header('Content-Type',mime)
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; frame-src 'self' blob:; font-src 'self' data:; frame-ancestors 'none'; base-uri 'none'")
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def authorized(self):
            return self.headers.get('Host')==host and secrets.compare_digest(self.headers.get('X-DIY-Token',''),token) and self.headers.get('Origin',origin)==origin
        def do_GET(self):
            path=urlparse(self.path)
            if self.headers.get('Host')!=host:return self.reply(403,{'message':'无效本地地址。'})
            if path.path=='/':return self.reply(200,(ROOT/'scripts/style-menu.html').read_bytes(),'text/html; charset=utf-8')
            if path.path=='/menu.js':return self.reply(200,(ROOT/'scripts/style-menu.js').read_bytes(),'text/javascript; charset=utf-8')
            if path.path.startswith('/scene-preview/'):
                parts=path.path.split('/',3)
                if len(parts)!=4 or not secrets.compare_digest(parts[2],token):return self.reply(403,{'message':'无效预览资源'})
                data=scene_assets.get(parts[3])
                if data is None:return self.reply(404,{'message':'场景图片已过期，请刷新场景。'})
                return self.reply(200,data,'image/svg+xml')
            if path.path.startswith('/scene-assets/'):
                parts=path.path.split('/',3)
                if len(parts)!=4 or not secrets.compare_digest(parts[2],token):return self.reply(403,{'message':'无效预览资源'})
                from urllib.parse import unquote
                try:
                    asset=build.safe_child(ROOT/'assets',unquote(parts[3]))
                    if not asset.is_file() or asset.suffix.lower() not in set(build.MIMES)|{'.woff','.woff2','.ttf','.otf'}:raise ValueError()
                    return self.reply(200,asset.read_bytes(),mimetypes.guess_type(asset.name)[0] or 'application/octet-stream')
                except (ValueError,OSError):return self.reply(404,{'message':'预览资源不存在'})
            if not self.authorized():return self.reply(403,{'message':'菜单已失效，请重新双击启动样式菜单。'})
            activity[0]=time.monotonic()
            try:
                if path.path=='/api/ping':return self.reply(200,{'ok':True})
                if path.path=='/api/state':
                    regions=[]
                    for s in slots:
                        picfiles=build.picture_files(ROOT/'DIY图片'/s['folder'])
                        regions.append({'id':s['id'],'name':s['folder'],'style':styles.read_choice(ROOT,s),'tapeColors':styles.read_colors(ROOT,s),'tapePatterns':styles.read_patterns(ROOT,s),'photoAdjustments':styles.read_adjustments(ROOT,s),'photoBorders':styles.read_borders(ROOT,s),'frontPhoto':styles.read_front(ROOT,s),
                                        'canvasSize':[s['width'],s['height']],
                                        'layoutGeometry':{str(x['id']):styles.layout_geometry(ROOT,s,x['id']) for x in styles.available(ROOT,s)},
                                        'photos':build.picture_labels(ROOT/'DIY图片'/s['folder']),'swapPhotos':styles.read_swap(ROOT,s),
                                        'allowedStyles':[x['id'] for x in styles.available(ROOT,s)],
                                        'tapeCounts':{str(x['id']):styles.tape_count(ROOT,s,x['id']) for x in styles.available(ROOT,s)},'photo':build.picture_labels(ROOT/'DIY图片'/s['folder'])[0] if picfiles else None})
                    return self.reply(200,{'regions':regions,'styles':styles.catalog(ROOT),'colors':styles.palettes(ROOT),'patterns':styles.patterns(ROOT)})
                if path.path=='/api/preview':
                    q=parse_qs(path.query);s=slot_map[q['slot'][0]];style_id=int(q['style'][0])
                    if style_id not in {x['id'] for x in styles.available(ROOT,s)}:raise ValueError('该区域不支持此样式')
                    pics=[] if style_id==0 else build.pictures(ROOT/'DIY图片'/s['folder'],2 if style_id==8 else 1)
                    pic=pics[0] if pics else None
                    swap_value=q.get('swap',[str(int(styles.read_swap(ROOT,s)))])[0]
                    if swap_value not in ('0','1'):raise ValueError('无效照片顺序')
                    colors=styles.validate_colors(ROOT,[q['color1'][0],q['color2'][0]]) if 'color1' in q and 'color2' in q else styles.read_colors(ROOT,s)
                    patterns=styles.validate_patterns(ROOT,[q['pattern1'][0],q['pattern2'][0]]) if 'pattern1' in q and 'pattern2' in q else styles.read_patterns(ROOT,s)
                    adjustments=styles.validate_adjustments(json.loads(q['adjustments'][0])) if 'adjustments' in q else styles.read_adjustments(ROOT,s)
                    borders=styles.validate_borders(json.loads(q['borders'][0])) if 'borders' in q else styles.read_borders(ROOT,s)
                    front=styles.validate_front(q.get('front',[styles.read_front(ROOT,s)])[0])
                    svg=styles.render(ROOT,s,style_id,pic['uri'] if pic else styles.sample_uri(),colors,pics[1]['uri'] if len(pics)>1 else None,swap_value=='1',patterns,adjustments,borders,front)
                    return self.reply(200,svg.encode('utf-8'),'image/svg+xml')
                return self.reply(404,{'message':'页面不存在。'})
            except Exception as e:return self.reply(400,{'message':str(e)})
        def do_POST(self):
            if not self.authorized():return self.reply(403,{'message':'请求未通过本地菜单校验。'})
            activity[0]=time.monotonic()
            try:
                length=int(self.headers.get('Content-Length','0'))
                limit=photo_import.MAX_IMAGE_BYTES*4//3+4096 if self.path=='/api/photo' else 16384
                if not 0<length<=limit:raise ValueError('请求大小错误')
                if self.headers.get('Content-Type')!='application/json':raise ValueError('请求格式错误')
                payload=json.loads(self.rfile.read(length))
                if self.path=='/api/photo':
                    if not isinstance(payload,dict) or payload.get('slot') not in slot_map:raise ValueError('无效图片区域。')
                    with save_lock:photos=photo_import.select(ROOT,slot_map[payload['slot']],payload)
                    return self.reply(200,{'photos':photos,'photo':photos[0] if photos else None})
                if self.path=='/api/scene':
                    result=scene_preview.render(ROOT,payload,token,scene_assets.put)
                    return self.reply(200,result.encode('utf-8'),'text/html; charset=utf-8')
                if self.path=='/api/save':
                    with save_lock:result=save_choices(payload)
                    return self.reply(200,result)
                if self.path=='/api/close':
                    closed[0]=True;return self.reply(200,{'ok':True})
                return self.reply(404,{'message':'页面不存在。'})
            except Exception as e:return self.reply(400,{'message':str(e)})
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.timeout=1
    host='127.0.0.1:'+str(server.server_port);origin='http://'+host;url=origin+'/#'+token
    print(url,flush=True)
    if not args.no_browser:webbrowser.open(url)
    try:
        while not closed[0] and time.monotonic()-activity[0]<1200:server.handle_request()
    finally:server.server_close()

if __name__=='__main__':main()
