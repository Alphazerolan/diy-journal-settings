from pathlib import Path
import json, sys, tempfile, unittest, shutil, os
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'engine/scripts'))
import style_menu, build


class IntroSettingsTests(unittest.TestCase):
    def test_save_reload_apply_and_rollback(self):
        with tempfile.TemporaryDirectory() as temp:
            root=(Path(temp)/'editor').resolve()
            shutil.copytree(build.ROOT, root)
            shutil.copytree(Path(__file__).resolve().parents[1]/'skin', root, dirs_exist_ok=True)
            target=Path(temp)/'skin';target.mkdir()
            (target/'skin.json').write_text('{"id":"diy-journal"}')
            slots=json.loads((root/'slots.json').read_text(encoding='utf-8'))
            choices={s['id']:0 for s in slots}
            with patch.object(style_menu,'ROOT',root), patch.object(build,'ROOT',root), patch.dict(os.environ,{'DIY_JOURNAL_SKIN_DIR':str(target)}):
                self.assertTrue(style_menu.read_intro_settings()['introEnabled'])
                style_menu.save_choices(choices,settings={'introEnabled':False})
                self.assertFalse(style_menu.read_intro_settings()['introEnabled'])
                self.assertFalse(json.loads((target/'intro-settings.json').read_text())['introEnabled'])
                with patch.object(build,'build',side_effect=RuntimeError('fixture failure')):
                    with self.assertRaises(RuntimeError):
                        style_menu.save_choices(choices,settings={'introEnabled':True})
                self.assertFalse(style_menu.read_intro_settings()['introEnabled'])
                with self.assertRaises(ValueError):
                    style_menu.save_choices(choices,settings={'introEnabled':'false'})
                # Old clients omit settings; preserve the saved switch.
                style_menu.save_choices(choices)
                self.assertFalse(style_menu.read_intro_settings()['introEnabled'])
                style_menu.save_choices(choices,settings={'introEnabled':True})
                self.assertTrue(json.loads((target/'intro-settings.json').read_text())['introEnabled'])
