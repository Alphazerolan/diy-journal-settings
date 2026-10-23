from pathlib import Path
import base64,json,sys,tempfile,unittest,os
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine/scripts'))
import build,photo_import,video_media

POSTER='data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAGAAgDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDsaKKK7Dzj/9k='
RAW=b'\x00\x00\x00\x18ftypisom'+b'\x00'*24

class VideoMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.work=self.root/'editor';self.folder=self.work/'DIY图片/主界面';self.folder.mkdir(parents=True)
        self.slot={'id':'home','folder':'主界面'}
        self.payload={'index':0,'name':'clip.mp4','data':base64.b64encode(RAW).decode(),'video':{'width':8,'height':6,'poster':POSTER}}
    def test_import_poster_build_and_restore_video(self):
        photo_import.select(self.work,self.slot,self.payload)
        files=build.picture_files(self.folder);self.assertEqual(len(files),1)
        pic=build.load_picture(files[0]);self.assertEqual(pic['width'],8)
        svg='<svg xmlns="http://www.w3.org/2000/svg"><g data-diy-adjustment="1"><image href="'+pic['uri']+'"/></g></svg>'
        decorated=video_media.decorate(svg,[pic],self.work)
        self.assertIn('data-diy-video=',decorated)
        (self.work/'skin.json').write_text('{"id":"diy-journal"}')
        dest=self.work/'assets/diy-generated';dest.mkdir(parents=True);(dest/'home.svg').write_text(decorated,encoding='utf-8')
        restored=self.root/'restored';(restored/'DIY图片/主界面').mkdir(parents=True)
        with patch.dict(os.environ,{'DIY_JOURNAL_SKIN_DIR':str(self.work)}):photo_import.restore(restored,self.slot,'current')
        copy=build.load_picture(build.picture_files(restored/'DIY图片/主界面')[0])
        self.assertEqual(copy['data'],RAW);self.assertEqual(copy['metadata'],pic['metadata'])
    def test_bad_video_or_missing_metadata_preserves_selection(self):
        photo_import.select(self.work,self.slot,self.payload)
        original=(self.folder/'图片选择.json').read_bytes()
        for change in ({'data':base64.b64encode(b'bad').decode()},{'video':None},{'video':{'width':0,'height':6,'poster':POSTER}}):
            with self.assertRaises(ValueError):photo_import.select(self.work,self.slot,{**self.payload,**change})
            self.assertEqual(original,(self.folder/'图片选择.json').read_bytes())
        self.assertEqual(len(build.picture_files(self.folder)),1)
    def test_recovery_rejects_external_or_traversing_video_paths(self):
        for ref in ('../private.mp4','https://example.com/a.mp4','diy-media/../a.mp4'):
            with self.assertRaises(ValueError):video_media.recover(self.work,ref)
    def test_folder_video_without_poster_has_clear_error(self):
        path=self.folder/'manual.mp4';path.write_bytes(RAW)
        with self.assertRaisesRegex(ValueError,'菜单'):build.load_picture(path)
