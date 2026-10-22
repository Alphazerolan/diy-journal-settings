from pathlib import Path
import unittest,tempfile,sys,os,json,base64,struct,zlib
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'engine/scripts'))
import photo_import

def png(color):
    def chunk(t,data):return struct.pack('>I',len(data))+t+data+struct.pack('>I',zlib.crc32(t+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b'\0'+bytes(color)))+chunk(b'IEND',b'')

def image(raw,number=1):
    return '<g data-diy-adjustment="'+str(number)+'"><image href="data:image/png;base64,'+base64.b64encode(raw).decode()+'"/></g>'

class PhotoActionsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.work=self.root/'work';self.folder=self.work/'DIY图片/主界面';self.folder.mkdir(parents=True)
        self.slot={'id':'home','folder':'主界面'};self.red=png((255,0,0,255));self.blue=png((0,0,255,255))
        self.current=self.root/'current';self.preset=self.root/'preset'
        for p in [self.current,self.preset]:
            (p/'assets/diy-generated').mkdir(parents=True);(p/'skin.json').write_text('{"id":"diy-journal"}')
        self.env=patch.dict(os.environ,{'DIY_JOURNAL_SKIN_DIR':str(self.current),'DIY_JOURNAL_BUNDLED_SKIN_DIR':str(self.preset)});self.env.start();self.addCleanup(self.env.stop)
    def put(self,base,content):
        (base/'assets/diy-generated/home.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg">'+content+'</svg>')
    def selected(self):
        return json.loads((self.folder/'图片选择.json').read_text(encoding='utf-8'))['pictures']
    def test_current_and_preset_are_distinct_and_keep_existing_photos(self):
        self.put(self.current,image(self.red));self.put(self.preset,image(self.blue));(self.folder/'personal.png').write_bytes(self.red)
        photo_import.restore(self.work,self.slot,'current');self.assertEqual((self.folder/self.selected()[0]['file']).read_bytes(),self.red)
        photo_import.restore(self.work,self.slot,'preset');self.assertEqual((self.folder/self.selected()[0]['file']).read_bytes(),self.blue)
        self.assertEqual((self.folder/'personal.png').read_bytes(),self.red)
    def test_front_layer_does_not_reverse_photo_order(self):
        self.put(self.current,image(self.blue,2)+image(self.red,1)+'<image data-diy-tape="1" href="data:image/svg+xml;base64,AA=="/>')
        photo_import.restore(self.work,self.slot,'current')
        self.assertEqual([(self.folder/p['file']).read_bytes() for p in self.selected()],[self.red,self.blue])
    def test_empty_current_skin_restores_empty_selection(self):
        self.put(self.current,'');self.assertEqual(photo_import.restore(self.work,self.slot,'current'),[]);self.assertEqual(self.selected(),[None,None])
    def test_invalid_source_does_not_replace_selection(self):
        self.put(self.current,image(self.red));photo_import.restore(self.work,self.slot,'current');before=self.selected()
        self.put(self.current,'<image href="https://example.com/photo.png"/>')
        with self.assertRaises(ValueError):photo_import.restore(self.work,self.slot,'current')
        self.assertEqual(self.selected(),before)
        with self.assertRaises(ValueError):photo_import.restore(self.work,self.slot,'unknown')
    def test_open_folder_does_not_change_selection_and_rejects_escape(self):
        self.put(self.current,image(self.red));photo_import.restore(self.work,self.slot,'current');before=self.selected();opened=[]
        photo_import.open_folder(self.work,self.slot,opened.append)
        self.assertEqual(opened,[str(self.folder.resolve())]);self.assertEqual(self.selected(),before)
        with self.assertRaises(ValueError):photo_import.open_folder(self.work,{'folder':'../../outside'},opened.append)

if __name__=='__main__':unittest.main()
