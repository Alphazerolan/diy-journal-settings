"""Exercise the editor preparation and build pipeline with neutral fixtures."""
from pathlib import Path
import hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile, unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'engine/scripts'))
import styles

NEUTRAL='<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400"><rect width="600" height="400" fill="#dbeef3"/><circle cx="420" cy="90" r="42" fill="#f5d891"/><path d="M0 400V300L160 145 360 330 480 200 600 300V400Z" fill="#8cb7a4"/></svg>'

def hashes(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

class ReapplyRoundtripTests(unittest.TestCase):
    def test_two_prepare_build_install_cycles_keep_customization_and_current_layout(self):
        with tempfile.TemporaryDirectory(prefix='diy-roundtrip-') as temporary:
            base=Path(temporary).resolve();bundle=base/'plugin';engine=bundle/'engine'
            engine.mkdir(parents=True)
            for folder in ['scripts','templates']:
                shutil.copytree(ROOT/'engine'/folder,engine/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            for name in ['slots.json','styles.json','tape-colors.json','tape-patterns.json']:
                shutil.copy2(ROOT/'engine'/name,engine/name)
            (engine/'assets').mkdir()
            shutil.copy2(ROOT/'skin/assets/journal-tape-blue-v80.svg',engine/'assets/journal-tape-blue-v80.svg')
            shutil.copy2(ROOT/'install.py',bundle/'install.py')
            home=base/'home';skin=home/'skins/diy-journal';work=home/'diy-journal-editor'
            skin.mkdir(parents=True)
            write_json(skin/'skin.json',{'id':'diy-journal','version':'fixture'})
            (skin/'skin.css').write_text('/* neutral test skin */\n',encoding='utf-8')
            (skin/'hooks.mjs').write_text('export default ()=>({apply(){}});\n',encoding='utf-8')
            (skin/'patches.css').write_bytes((engine/'templates/base.css').read_bytes())
            slots=json.loads((engine/'slots.json').read_text(encoding='utf-8'))
            choices=styles.catalog(engine)
            for slot in slots:
                folder=work/'DIY图片'/slot['folder'];folder.mkdir(parents=True)
                (folder/'fixture.svg').write_text(NEUTRAL,encoding='utf-8')
                write_json(folder/'图片选择.json',{'mode':'selected','pictures':[{'file':'fixture.svg','name':'neutral fixture'},None]})
                (folder/'.initialized').touch()
                selected=10 if slot['id']=='settings-sidebar' else 3 if slot['id'] in ('home','general') else 1
                write_json(folder/'样式.json',{'当前样式':selected})
                write_json(folder/'样式.json',styles.config(selected,styles.available(work,slot,choices),['blue','orange'],False,
                           styles.default_patterns(selected),styles.default_adjustments(),styles.default_borders(),'right'))
            personal=hashes(work/'DIY图片')
            spec=importlib.util.spec_from_file_location('roundtrip_installer',bundle/'install.py')
            installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
            env={**os.environ,'DSH_HOME':str(home),'DIY_JOURNAL_SKIN_DIR':str(skin),
                 'PYTHONIOENCODING':'utf-8','PYTHONDONTWRITEBYTECODE':'1'}
            previous=None
            for cycle in range(2):
                self.assertEqual(installer.prepare(home,skin),work)
                self.assertEqual(hashes(work/'DIY图片'),personal)
                result=subprocess.run([sys.executable,'-X','utf8',str(work/'scripts/build.py'),'--install'],
                                      env=env,capture_output=True,text=True,encoding='utf-8')
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertEqual(hashes(work/'DIY图片'),personal)
                css=(skin/'patches.css').read_text(encoding='utf-8')
                self.assertEqual(hashlib.sha256(css.encode()).hexdigest(),
                                 hashlib.sha256((work/'patches.css').read_text(encoding='utf-8').encode()).hexdigest())
                for marker in ['data-diy-settings-layout="rc1"',
                               ':not([data-diy-settings-layout])',
                               '.AnXs9G_panel > .AnXs9G_options',
                               'padding: 18px 24px 18px 30px',
                               ':is(.wCInkW_options,.AnXs9G_options)',
                               ':is(._2H3hWW_footArea,.wtg9ga_footArea)',
                               'grid-column:1/-1!important;grid-row:1!important;justify-self:stretch!important;']:
                    self.assertTrue(marker in css,'rebuild lost '+marker)
                notes=[line for line in css.splitlines() if '> [data-dsh-usage-foot-card]' in line]
                self.assertEqual(len(notes),2)
                self.assertTrue(all('grid-row:2;' in line for line in notes))
                # Preserve 1.3.x plugin-seat targeting while fixing the footer layout.
                generated=(work/'generated/slots.css').read_text(encoding='utf-8')
                for plugin in ['skin-center','pet','usage','dsh-web-ui-market']:
                    self.assertIn('[data-dsh-plugin="'+plugin+'"]',generated)
                self.assertEqual(hashes(work/'assets/diy-generated'),hashes(skin/'assets/diy-generated'))
                current={'patches':hashlib.sha256(css.encode()).hexdigest(),
                         'artwork':hashes(work/'assets/diy-generated')}
                if previous is not None:self.assertEqual(current,previous)
                previous=current

if __name__=='__main__':unittest.main()
