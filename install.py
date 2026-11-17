"""Install a portable local editor; do not modify application binaries or other skins."""
from pathlib import Path
import argparse,base64,datetime,json,os,re,shutil,sys,hashlib
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
START='# DIY-JOURNAL-SETTINGS-ENTRY'
END='# END-DIY-JOURNAL-SETTINGS-ENTRY'
PREPARE_STATE='.diy-journal-prepare-state.json'

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(text,encoding='utf-8');tmp.replace(path)

def prepare(home,skin_dir=None):
    skin=skin_dir or home/'skins/diy-journal';work=home/'diy-journal-editor'
    if not (skin/'skin.json').is_file() or json.loads((skin/'skin.json').read_text(encoding='utf-8')).get('id')!='diy-journal':
        raise ValueError('Install the DIY Journal skin before the editor.')
    def plain(path):
        if any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in (path,*path.parents)):
            raise ValueError('Linked skin/workspace paths are unsupported.')
    plain(skin);plain(work)
    state_path=work/PREPARE_STATE
    plain(state_path);plain(state_path.with_suffix(state_path.suffix+'.tmp'))
    previous={}
    if state_path.exists():
        state=json.loads(state_path.read_text(encoding='utf-8'))
        if (not isinstance(state,dict) or state.get('schema')!=1 or
            not isinstance(state.get('files'),dict) or
            any(not isinstance(k,str) or not isinstance(v,str) or not re.fullmatch('[a-f0-9]{64}',v)
                for k,v in state['files'].items())):
            raise ValueError('Invalid DIY editor prepare state; no files were changed.')
        previous=state['files']
    # Resolve precedence before copying: engine wins when both sources ship the
    # same relative path. Existing asset/photo files always remain user-owned.
    desired={}
    for source,folder in (('skin',skin),('engine',ROOT/'engine')):
        plain(folder)
        for current,dirs,names in os.walk(folder,followlinks=False):
            for name in dirs:plain(Path(current)/name)
            dirs[:]=sorted(name for name in dirs if name!='__pycache__')
            for name in sorted(names):
                p=Path(current)/name;plain(p)
                if not p.is_file():continue
                rel=p.relative_to(folder)
                if source=='skin' and rel.parts[0] not in ('assets','skin.json','skin.css','patches.css','hooks.mjs','NOTICE','README.md','README.zh.md','LICENSE','intro-settings.json'):continue
                if rel.as_posix()==PREPARE_STATE:raise ValueError('Reserved editor state path in bundle.')
                dest=work/rel;plain(dest)
                desired[rel.as_posix()]={'source':source,'path':p}
    # Font-format adaptation is part of the effective shipped bytes. Never
    # rewrite a preserved custom template merely to change its font URLs.
    base=desired.get('templates/base.css')
    if base is not None:
        text=base['path'].read_bytes()
        for stem in ('LXGWWenKai-Medium','LongCang-Regular-v215'):
            font=work/'assets'/f'{stem}.woff2';plain(font)
            if font.is_file() or f'assets/{stem}.woff2' in desired:
                text=text.replace(f'url(assets/{stem}.ttf) format("truetype")'.encode(),
                                  f'url(assets/{stem}.woff2) format("woff2")'.encode())
        base['data']=text
    shipped={};sources={};created=set()
    for rel,item in desired.items():
        dest=work/rel;protected=Path(rel).parts[0] in ('DIY图片','assets')
        # Existing protected files need neither source bytes nor hashes. In
        # particular, do not load the packaged photo/font trees into memory.
        if protected and dest.exists():continue
        data=item['data'] if 'data' in item else item['path'].read_bytes()
        # State contains only shipped managed code/config, never personal
        # photos, generated photo assets, or a scan of the existing workspace.
        if not protected:
            digest=hashlib.sha256(data).hexdigest()
            shipped[rel]=digest;sources[rel]=item['source']
        if dest.exists():
            actual=hashlib.sha256(dest.read_bytes()).hexdigest()
            if actual==digest:continue
            if actual!=previous.get(rel):continue
        if not dest.exists():created.add(rel)
        dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    for slot in json.loads((work/'slots.json').read_text(encoding='utf-8')):
        folder=work/'DIY图片'/slot['folder'];marker=folder/'.initialized'
        plain(folder);plain(marker)
        if marker.exists():continue
        selection=folder/'图片选择.json'
        plain(selection)
        # A previously saved empty selection may be intentional. Only seed a
        # missing selection or a placeholder newly copied during this prepare.
        if selection.exists() and selection.relative_to(work).as_posix() not in created:
            marker.touch();continue
        current=json.loads(selection.read_text(encoding='utf-8')) if selection.exists() else {}
        if any(current.get('pictures',[])):
            marker.touch();continue
        svg=skin/'assets/diy-generated'/f"{slot['id']}.svg"
        chosen=[]
        if svg.exists():
            doc=ET.fromstring(svg.read_bytes())
            for el in doc.iter():
                if el.tag.split('}')[-1]!='image':continue
                ref=el.get('data-diy-video')
                if ref:
                    if not re.fullmatch(r'diy-media/[a-f0-9]{64}\.mp4',ref):raise ValueError('Invalid video reference')
                    source=skin/'assets'/ref;meta=source.with_name('.'+source.name+'.json');plain(source);plain(meta)
                    raw=source.read_bytes()
                    if hashlib.sha256(raw).hexdigest()+'.mp4'!=source.name:raise ValueError('Invalid video checksum')
                    filename=f'bundled-{len(chosen)+1}.mp4'
                    (folder/filename).write_bytes(raw);shutil.copy2(meta,folder/('.'+filename+'.json'))
                    chosen.append({'file':filename,'name':filename})
                    if len(chosen)==2:break
                    continue
                uri=el.get('href',el.get('{http://www.w3.org/1999/xlink}href',''))
                m=re.fullmatch(r'data:image/(png|jpeg|webp|gif|bmp|svg\+xml);base64,(.+)',uri,re.S)
                if not m:continue
                raw=base64.b64decode(m[2],validate=True);ext={'jpeg':'jpg','svg+xml':'svg'}.get(m[1],m[1])
                filename=f'bundled-{len(chosen)+1}.{ext}'
                (folder/filename).write_bytes(raw)
                chosen.append({'file':filename,'name':filename})
                if len(chosen)==2:break
        write(selection,json.dumps({'mode':'selected','pictures':(chosen+[None,None])[:2]},ensure_ascii=False,indent=2)+'\n')
        marker.touch()
    write(state_path,json.dumps({'schema':1,'sourcePriority':['skin','engine'],
                               'files':shipped,'sources':sources},ensure_ascii=False,indent=2)+'\n')
    return work

def register(home,uninstall=False):
    patch=home/'profiles/desktop/cordis.patch.yml'
    if not patch.is_file():raise ValueError('Harness desktop profile was not found. Start Harness once first.')
    text=patch.read_text(encoding='utf-8');updated=text
    if START in text:
        if END not in text:raise ValueError('Incomplete existing editor registration; no changes made.')
        updated=re.sub(r'(?m)^'+re.escape(START)+r'.*?^'+re.escape(END)+r'\s*\n?', '',text,flags=re.S)
    if not uninstall:
        entry=(ROOT/'index.mjs').as_posix().replace("'","''")
        updated=updated.rstrip()+f"\n\n{START}\n- insert:\n    - id: local-diy-journal-settings\n      name: '{entry}'\n{END}\n"
    if updated==text:return
    backup=home/'diy-journal-editor-backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')/'cordis.patch.yml'
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(patch,backup)
    write(patch,updated)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dsh-home',type=Path,default=Path(os.environ.get('DSH_HOME',str(Path.home()/'.dsh'))))
    parser.add_argument('--uninstall',action='store_true')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--skin-dir',type=Path)
    args=parser.parse_args();home=args.dsh_home.resolve()
    if args.uninstall:register(home,True);print('Editor entry removed. Personal photos and skin preserved. Restart Harness.');return
    work=prepare(home,args.skin_dir)
    if not args.prepare_only:
        raise ValueError('Use the standard DSH plugin installer. Manual profile registration is retired.')
    print('Editor prepared: '+str(work))
    print('Restart Harness, then open Settings > DIY Journal.')

if __name__=='__main__':main()
