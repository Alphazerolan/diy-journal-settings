import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine' / 'scripts'))
import dsh_compat
import video_media


class DshCompatibilityTests(unittest.TestCase):
    def test_native_two_class_lists_are_expanded(self):
        css = ':is(.hIlkoa_sessionRow,.hIlkoa_searchResultRow)[aria-selected="true"]'
        result = dsh_compat.selectors(css)
        self.assertIn('.wnFoaW_sessionRow', result)
        self.assertIn('.wnFoaW_searchResultRow', result)
        self.assertEqual(result, dsh_compat.selectors(result))

    def test_aliases_preserve_scope_and_specificity(self):
        css = 'body ._2H3hWW_root:not(._2H3hWW_collapsed)::after{content:""}'
        result = dsh_compat.selectors(css)
        self.assertIn(':is(._2H3hWW_root,.wtg9ga_root)', result)
        self.assertIn(':not(:is(._2H3hWW_collapsed,.wtg9ga_collapsed))', result)
        self.assertTrue(result.endswith('::after{content:""}'))
        self.assertEqual(result, dsh_compat.selectors(result))

    def test_unknown_modules_and_assets_are_untouched(self):
        css = '.abcdef_root{background:url(assets/diy-generated/home.svg)}'
        self.assertEqual(css, dsh_compat.selectors(css))

    def test_video_selectors_support_both_hosts(self):
        result = video_media.entry({'id': 'main-sidebar'})
        self.assertIn('._2H3hWW_footArea', result['selector'])
        self.assertIn('.wtg9ga_footArea', result['selector'])
        self.assertEqual(result['pseudo'], 'before')

    def test_editor_template_and_shipped_css_are_compatible(self):
        root = Path(__file__).resolve().parents[1]
        for name in ['skin/patches.css', 'engine/templates/base.css']:
            css = (root / name).read_text(encoding='utf-8')
            for new in ['wtg9ga_root', 'V7pFBG_group', '_5Qcc8a_trigger', 'xMeOpW_body']:
                self.assertIn('.' + new, css, name)


if __name__ == '__main__':
    unittest.main()
