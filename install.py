"""Install a portable local editor; do not modify application binaries or other skins."""
from pathlib import Path
import argparse,base64,datetime,json,os,re,shutil,sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
START='# DIY-JOURNAL-SETTINGS-ENTRY'
END='# END-DIY-JOURNAL-SETTINGS-ENTRY'

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(text,encoding='utf-8');tmp.replace(path)

def prepare(home):
    skin=home/'skins/diy-journal';work=home/'diy-journal-editor'
    if not (skin/'skin.json').is_file() or json.loads((skin/'skin.json').read_text(encoding='utf-8')).get('id')!='diy-journal':
        raise ValueError('Install the DIY Journal skin before the editor.')
    if skin.is_symlink() or work.is_symlink():raise ValueError('Linked skin/workspace directories are unsupported.')
    for folder in (skin,ROOT/'engine'):
        for p in folder.rglob('*'):
            if not p.is_file() or '__pycache__' in p.parts:continue
            rel=p.relative_to(folder)
            if folder==skin and rel.parts[0] not in ('assets','skin.json','skin.css','patches.css','hooks.mjs','NOTICE','README.md','README.zh.md','LICENSE'):continue
            if p.is_symlink():raise ValueError('Linked files are unsupported.')
            dest=work/rel
            # Existing photos and layout choices survive plugin upgrades.
            if dest.exists() and (rel.parts[0]=='DIY图片' or (folder==skin and rel.parts[0]=='assets')):continue
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    # Match the installed skin's font format, including compact releases.
    base_css=work/'templates/base.css'
    if base_css.is_file():
        text=base_css.read_text(encoding='utf-8')
        for stem in ('LXGWWenKai-Medium','LongCang-Regular-v215'):
            if (work/'assets'/f'{stem}.woff2').is_file():
                text=text.replace(f'url(assets/{stem}.ttf) format("truetype")',
                                  f'url(assets/{stem}.woff2) format("woff2")')
        write(base_css,text)
    for slot in json.loads((work/'slots.json').read_text(encoding='utf-8')):
        folder=work/'DIY图片'/slot['folder'];marker=folder/'.initialized'
        if marker.exists():continue
        selection=folder/'图片选择.json'
        current=json.loads(selection.read_text(encoding='utf-8')) if selection.exists() else {}
        if any(current.get('pictures',[])):
            marker.touch();continue
        svg=skin/'assets/diy-generated'/f"{slot['id']}.svg"
        chosen=[]
        if svg.exists():
            doc=ET.fromstring(svg.read_bytes())
            for el in doc.iter():
                if el.tag.split('}')[-1]!='image':continue
                uri=el.get('href',el.get('{http://www.w3.org/1999/xlink}href',''))
                m=re.fullmatch(r'data:image/(png|jpeg|webp);base64,(.+)',uri,re.S)
                if not m:continue
                raw=base64.b64decode(m[2],validate=True);ext={'jpeg':'jpg'}.get(m[1],m[1])
                filename=f'bundled-{len(chosen)+1}.{ext}'
                (folder/filename).write_bytes(raw)
                chosen.append({'file':filename,'name':filename})
                if len(chosen)==2:break
        write(selection,json.dumps({'mode':'selected','pictures':(chosen+[None,None])[:2]},ensure_ascii=False,indent=2)+'\n')
        marker.touch()
    write(ROOT/'runtime.json',json.dumps({'python':sys.executable,'workspace':str(work),'dshHome':str(home)},indent=2)+'\n')
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
    args=parser.parse_args();home=args.dsh_home.resolve()
    if args.uninstall:register(home,True);print('Editor entry removed. Personal photos and skin preserved. Restart Harness.');return
    work=prepare(home)
    if not args.prepare_only:register(home)
    print('Editor prepared: '+str(work))
    print('Restart Harness, then open Settings > DIY Journal.')

if __name__=='__main__':main()
