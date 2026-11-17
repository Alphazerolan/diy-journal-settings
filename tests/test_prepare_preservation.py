"""Isolated prepare tests. Never reads or writes the user's DSH installation."""
from pathlib import Path
import base64, hashlib, importlib.util, json, os, sys, tempfile, unittest
from unittest.mock import patch

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('candidate_install',HERE/'install.py')
candidate=importlib.util.module_from_spec(spec);spec.loader.exec_module(candidate)

def put(root,rel,data):
    p=root/rel;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(data if isinstance(data,bytes) else data.encode('utf-8'))
    return p

def hashes(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and not p.is_symlink()}

class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='prepare-test-',dir=HERE)
        self.root=Path(self.tmp.name).resolve()
        # Verify the cleanup target before TemporaryDirectory recursively removes it.
        assert self.root.is_relative_to(HERE.resolve()) and self.root!=HERE.resolve()
        self.addCleanup(self.tmp.cleanup)
        self.bundle=self.root/'bundle';self.engine=self.bundle/'engine'
        self.home=self.root/'home';self.skin=self.home/'skins/diy-journal'
        self.work=self.home/'diy-journal-editor'
        self.previous_root=candidate.ROOT;candidate.ROOT=self.bundle
        self.addCleanup(setattr,candidate,'ROOT',self.previous_root)
        put(self.skin,'skin.json',json.dumps({'id':'diy-journal','version':'test'}))
        put(self.skin,'skin.css','skin source')
        put(self.skin,'patches.css','skin patches')
        put(self.skin,'assets/diy-generated/main-sidebar.svg','<svg xmlns="http://www.w3.org/2000/svg"/>')
        put(self.engine,'slots.json',json.dumps([{'id':'main-sidebar','folder':'测试照片'}]))
        put(self.engine,'scripts/build.py','build v1')
        put(self.engine,'scripts/helper.py','helper v1')
        put(self.engine,'templates/base.css','base v1')
        put(self.engine,'skin.css','engine source')
        put(self.engine,'DIY图片/测试照片/样式.json','default layout')

    def prepare(self):return candidate.prepare(self.home,self.skin)
    def read(self,rel):return (self.work/rel).read_bytes()
    def state(self):return json.loads(self.read(candidate.PREPARE_STATE))

    def test_first_install_engine_precedence_and_missing_files(self):
        self.assertEqual(self.prepare(),self.work)
        self.assertEqual(self.read('scripts/build.py'),b'build v1')
        self.assertEqual(self.read('templates/base.css'),b'base v1')
        self.assertEqual(self.read('skin.css'),b'engine source')
        self.assertTrue((self.work/'DIY图片/测试照片/.initialized').is_file())
        self.assertEqual(self.state()['sources']['skin.css'],'engine')
        self.assertEqual(self.state()['files']['skin.css'],hashlib.sha256(b'engine source').hexdigest())

    def test_repeated_prepare_is_idempotent(self):
        self.prepare();first=hashes(self.work);self.prepare()
        self.assertEqual(hashes(self.work),first)

    def test_missing_managed_file_is_restored_after_initial_prepare(self):
        self.prepare();(self.work/'scripts/helper.py').unlink();self.prepare()
        self.assertEqual(self.read('scripts/helper.py'),b'helper v1')

    def test_unknown_local_code_templates_and_css_preserved_without_state(self):
        for rel in ('scripts/build.py','templates/base.css','skin.css','patches.css'):
            put(self.work,rel,'local '+rel)
        put(self.work,'scripts/private.py','private local extension')
        preserved=hashes(self.work);self.prepare()
        for rel,digest in preserved.items():self.assertEqual(hashes(self.work)[rel],digest)
        self.assertEqual(self.read('scripts/helper.py'),b'helper v1')
        self.assertNotIn('scripts/private.py',self.state()['files'])

    def test_upgrade_only_replaces_previous_shipped_bytes(self):
        self.prepare();put(self.work,'scripts/helper.py','locally edited helper')
        put(self.work,'patches.css','local patches')
        put(self.engine,'scripts/build.py','build v2')
        put(self.engine,'scripts/helper.py','helper v2')
        put(self.engine,'templates/base.css','base v2')
        put(self.engine,'scripts/dsh_compat.py','new compat helper')
        put(self.skin,'patches.css','patches v2')
        self.prepare()
        self.assertEqual(self.read('scripts/build.py'),b'build v2')
        self.assertEqual(self.read('templates/base.css'),b'base v2')
        self.assertEqual(self.read('scripts/helper.py'),b'locally edited helper')
        self.assertEqual(self.read('patches.css'),b'local patches')
        self.assertEqual(self.read('scripts/dsh_compat.py'),b'new compat helper')
        self.prepare();self.assertEqual(self.read('scripts/helper.py'),b'locally edited helper')

    def test_personal_photos_choices_layouts_and_assets_never_overwritten_or_tracked(self):
        personal={
            'DIY图片/测试照片/photo.png':b'personal photo bytes',
            'DIY图片/测试照片/样式.json':'{"当前样式":3,"照片调整":[{"x":7,"scale":110}]}',
            'DIY图片/测试照片/图片选择.json':'{"pictures":[{"file":"photo.png"}]}',
            'DIY图片/测试照片/.initialized':'',
            'assets/diy-generated/main-sidebar.svg':'personal rendered image',
        }
        for rel,data in personal.items():put(self.work,rel,data)
        original=hashes(self.work);self.prepare()
        put(self.engine,'DIY图片/测试照片/样式.json','bundle v2 layout')
        put(self.skin,'assets/diy-generated/main-sidebar.svg','bundle v2 image')
        self.prepare()
        for rel,digest in original.items():self.assertEqual(hashes(self.work)[rel],digest)
        self.assertFalse(any(k.startswith(('DIY图片/','assets/')) for k in self.state()['files']))
        self.assertFalse(any(k.startswith(('DIY图片/','assets/')) for k in self.state()['sources']))

    def test_existing_protected_source_assets_are_not_read_into_memory(self):
        put(self.work,'assets/diy-generated/main-sidebar.svg','personal rendered image')
        put(self.work,'DIY图片/测试照片/样式.json','personal layout')
        put(self.work,'DIY图片/测试照片/.initialized','')
        blocked={self.skin/'assets/diy-generated/main-sidebar.svg',self.engine/'DIY图片/测试照片/样式.json'}
        original_read=Path.read_bytes
        def guarded(p):
            if p in blocked:raise AssertionError('Existing protected source bytes should not be loaded')
            return original_read(p)
        with patch.object(Path,'read_bytes',guarded):self.prepare()
        self.assertEqual(self.read('assets/diy-generated/main-sidebar.svg'),b'personal rendered image')

    def test_normalized_font_template_remains_upgradeable(self):
        font='url(assets/LXGWWenKai-Medium.ttf) format("truetype")'
        put(self.engine,'templates/base.css','v1 '+font)
        put(self.skin,'assets/LXGWWenKai-Medium.woff2',b'woff2 fixture')
        self.prepare()
        self.assertIn(b'woff2',self.read('templates/base.css'))
        self.assertEqual(self.state()['files']['templates/base.css'],hashlib.sha256(self.read('templates/base.css')).hexdigest())
        put(self.engine,'templates/base.css','v2 '+font);self.prepare()
        self.assertTrue(self.read('templates/base.css').startswith(b'v2 '))
        self.assertIn(b'woff2',self.read('templates/base.css'))

    def test_existing_photo_selection_survives_without_initialization_marker(self):
        selection='{"pictures":[{"file":"photo.png"}]}'
        put(self.work,'DIY图片/测试照片/photo.png',b'personal photo')
        put(self.work,'DIY图片/测试照片/图片选择.json',selection)
        put(self.work,'DIY图片/测试照片/样式.json','personal layout')
        self.prepare()
        self.assertEqual(self.read('DIY图片/测试照片/图片选择.json'),selection.encode())
        self.assertEqual(self.read('DIY图片/测试照片/样式.json'),b'personal layout')
        self.assertEqual(self.read('DIY图片/测试照片/photo.png'),b'personal photo')
        self.assertTrue((self.work/'DIY图片/测试照片/.initialized').exists())

    def test_existing_empty_selection_survives_without_initialization_marker(self):
        selection='{"mode":"selected", "pictures":[null,null]}\n'
        put(self.work,'DIY图片/测试照片/图片选择.json',selection)
        self.prepare()
        self.assertEqual(self.read('DIY图片/测试照片/图片选择.json'),selection.encode())
        self.assertTrue((self.work/'DIY图片/测试照片/.initialized').exists())

    def test_fresh_placeholder_selection_still_seeds_bundled_photo(self):
        put(self.engine,'DIY图片/测试照片/图片选择.json','{"pictures":[null,null]}')
        uri='data:image/png;base64,'+base64.b64encode(b'packaged photo fixture').decode()
        put(self.skin,'assets/diy-generated/main-sidebar.svg',f'<svg xmlns="http://www.w3.org/2000/svg"><image href="{uri}"/></svg>')
        self.prepare()
        selection=json.loads(self.read('DIY图片/测试照片/图片选择.json'))
        self.assertEqual(selection['pictures'][0]['file'],'bundled-1.png')
        self.assertEqual(self.read('DIY图片/测试照片/bundled-1.png'),b'packaged photo fixture')

    def test_unknown_custom_font_template_is_not_normalized(self):
        custom=b'local url(assets/LXGWWenKai-Medium.ttf) format("truetype")'
        put(self.work,'templates/base.css',custom)
        put(self.skin,'assets/LXGWWenKai-Medium.woff2',b'woff2 fixture')
        self.prepare();self.assertEqual(self.read('templates/base.css'),custom)

    def link(self,link,target,is_dir=False):
        link.parent.mkdir(parents=True,exist_ok=True)
        try:os.symlink(target,link,target_is_directory=is_dir)
        except OSError as exc:self.skipTest('Symlink privilege unavailable (error '+str(getattr(exc,'winerror',exc.errno))+')')

    def test_linked_workspace_file_is_rejected_before_copy(self):
        target=put(self.root,'outside-safe-fixture.py','keep target')
        self.link(self.work/'scripts/build.py',target)
        with self.assertRaisesRegex(ValueError,'Linked'):self.prepare()
        self.assertEqual(target.read_bytes(),b'keep target')

    def test_linked_source_directory_is_rejected_before_copy(self):
        target=self.root/'external-safe-fixture';put(target,'file.py','keep source')
        self.link(self.engine/'extra',target,is_dir=True)
        with self.assertRaisesRegex(ValueError,'Linked'):self.prepare()
        self.assertFalse((self.work/'scripts/build.py').exists())

    def test_invalid_state_does_not_overwrite_workspace(self):
        put(self.work,candidate.PREPARE_STATE,'{"schema":1,"files":{"scripts/build.py":"bad"}}')
        put(self.work,'scripts/build.py','keep local')
        first=hashes(self.work)
        with self.assertRaisesRegex(ValueError,'Invalid DIY'):self.prepare()
        self.assertEqual(hashes(self.work),first)

if __name__=='__main__':unittest.main(verbosity=2)
