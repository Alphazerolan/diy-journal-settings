"""Keep legacy selectors while supporting the verified DSH rc.3 CSS modules.

Only explicit, reviewed module mappings are expanded. Do not guess from a
suffix at runtime: unrelated components often share names such as root/card.
"""
import json
import re
from pathlib import Path

MODULES = json.loads(Path(__file__).with_name('dsh_rc3_classes.json').read_text(encoding='utf-8'))
_CLASS = r'\.([_a-zA-Z0-9-]{6,7})_([a-zA-Z][\w-]*)'
_TOKEN = re.compile(r':is\(\.[\w-]+,\.[\w-]+\)|' + _CLASS)

def settings_target(slot):
    """Plugin pages may move into Web Extensions; locate their content seat."""
    plugin = {'web': 'web-ui-settings', 'skins': 'skin-center', 'pets': 'pet',
              'workshop': 'dsh-web-ui-market', 'usage': 'usage'}.get(slot['id'])
    if plugin:
        target = ':has([data-dsh-plugin="' + plugin + '"])'
        if slot['id'] == 'web':
            target += ':not(:has([data-dsh-plugin="skin-center"], [data-dsh-plugin="pet"], [data-dsh-plugin="dsh-web-ui-market"], [data-dsh-plugin="usage"]))'
        return target
    return f':has(> nav .wCInkW_navCell:nth-child({slot["navIndex"]})[aria-current="true"])'

def selectors(text):
    """Expand known class selectors without increasing CSS specificity.

    Existing aliases pass through unchanged, so rebuilding is idempotent.
    This accepts CSS or querySelector strings, not arbitrary HTML markup.
    """
    def replace(match):
        if match.group(0).startswith(':is('):
            pair = match.group(0)[4:-1].split(',')
            left = re.fullmatch(_CLASS, pair[0])
            if left and pair[1] == '.' + MODULES.get(left.group(1), '') + '_' + left.group(2):
                return match.group(0)
            # A native two-class list is not necessarily an existing alias.
            return ':is(' + ','.join(selectors(item) for item in pair) + ')'
        prefix, suffix = match.group(1), match.group(2)
        if prefix not in MODULES:
            return match.group(0)
        return ':is(.' + prefix + '_' + suffix + ',.' + MODULES[prefix] + '_' + suffix + ')'
    return _TOKEN.sub(replace, text)
