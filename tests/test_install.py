from pathlib import Path
import importlib.util,json,tempfile,unittest,base64

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installer',ROOT/'install.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class InstallTests(unittest.TestCase):
    def test_install_upgrade_uninstall_preserves_user_data(self):
        original=installer.ROOT
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);plugin=base/'plugin';plugin.mkdir()
            import shutil
            shutil.copytree(ROOT/'engine',plugin/'engine');installer.ROOT=plugin
            home=base/'home';skin=home/'skins/diy-journal';skin.mkdir(parents=True)
            (skin/'skin.json').write_text('{"id":"diy-journal"}')
            art=skin/'assets/diy-generated';art.mkdir(parents=True)
            # Only extraction is tested here; rendering is covered by a real package smoke test.
            uri=base64.b64encode(b'sample-image-bytes').decode()
            (art/'home.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="data:image/png;base64,'+uri+'"/></svg>')
            patch=home/'profiles/desktop/cordis.patch.yml';patch.parent.mkdir(parents=True)
            patch.write_text('# keep unrelated plugin\n- keep: other-plugin\n')
            try:
                work=installer.prepare(home);installer.register(home)
                self.assertEqual(patch.read_text().count(installer.START),1)
                self.assertIn('other-plugin',patch.read_text())
                folder=work/'DIY图片/主界面'
                self.assertEqual((folder/'bundled-1.png').read_bytes(),b'sample-image-bytes')
                (folder/'图片选择.json').write_text('{"mode":"selected","pictures":[null,null]}')
                (folder/'personal.png').write_bytes(b'keep')
                installer.prepare(home);installer.register(home)
                self.assertEqual(json.loads((folder/'图片选择.json').read_text())['pictures'],[None,None])
                self.assertEqual((folder/'personal.png').read_bytes(),b'keep')
                self.assertEqual(patch.read_text().count(installer.START),1)
                installer.register(home,True)
                self.assertNotIn(installer.START,patch.read_text())
                self.assertIn('other-plugin',patch.read_text())
                self.assertTrue((folder/'personal.png').exists())
                self.assertTrue(list((home/'diy-journal-editor-backups').rglob('cordis.patch.yml')))
            finally:installer.ROOT=original

if __name__=='__main__':unittest.main()
