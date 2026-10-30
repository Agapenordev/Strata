#!/usr/bin/env python3
"""Isolated theme regressions; no application launches or personal-file writes."""
import configparser
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='strata-theme-test-') as directory:
    for key, suffix in [('XDG_CONFIG_HOME', 'config'), ('XDG_DATA_HOME', 'data'),
                        ('XDG_STATE_HOME', 'state'), ('XDG_CACHE_HOME', 'cache')]:
        os.environ[key] = str(Path(directory) / suffix)
    scripts = ROOT / 'home/.config/quickshell/scripts'
    sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location('theme', scripts / 'theme_manager.py')
    theme = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(theme)
    palettes = (ROOT / 'home/.config/quickshell/theme/Palettes.qml').read_text()
    samples = []
    for name, body in re.findall(r'id: "([^"]+)".*?colors: \{(.*?)\}', palettes, re.S):
        samples.append((name, dict(re.findall(r'(\w+):\s*"([^"]+)"', body))))
    samples.append(('adaptive-fallback', theme.build_palette(None)))
    for name, colors in samples:
        assert theme.luminance(*theme.hex_to_rgb(colors['background'])) < theme.GTK_LIGHT_ABOVE, name
    template = ROOT / 'home/.local/share/strata/kvantum'
    config_template = (template / 'Strata.kvconfig').read_text()
    svg_template = (template / 'Strata.svg').read_text()
    for name, colors in samples:
        parser = configparser.RawConfigParser()
        parser.read_string(theme.build_qt_colors(colors))
        for group in ('active_colors', 'inactive_colors', 'disabled_colors'):
            values = [v.strip() for v in parser['ColorScheme'][group].split(',')]
            assert len(values) == 22, (name, group)
            assert all(re.fullmatch(r'#ff[0-9a-fA-F]{6}', v) for v in values)
        active = parser['ColorScheme']['active_colors'].split(', ')
        assert active[7].lower() == '#ff' + colors['text'][1:].lower()
        assert active[13].lower() == '#ff' + colors['accentText'][1:].lower()
        kde = configparser.RawConfigParser()
        kde.read_string(theme.build_kde_scheme(colors))
        assert kde['General']['Name'] == 'Strata'
        assert kde.has_section('Colors:View')
        assert kde['Fonts']['General'].startswith('Inter,10,')
        assert kde['Fonts']['Fixed'].startswith('JetBrains Mono,11,')
        kate = json.loads(theme.build_kate_theme(colors))
        assert kate['metadata']['name'] == 'Strata'
        assert kate['editor-colors']['BackgroundColor'] != '#ffffff'
        assert kate['text-styles']['Normal']['text-color'] == colors['text']
        kvantum_config, kvantum_svg = theme.build_kvantum_theme(colors, config_template, svg_template)
        assert f'highlight.color={colors["accent"]}' in kvantum_config
        assert f'highlight.text.color={colors["accentText"]}' in kvantum_config
        assert colors['accent'].lower() in kvantum_svg.lower()
        assert '#5294e2' not in kvantum_svg.lower()
        print('PASS palette', name)
    original_which = theme.shutil.which
    original_run = theme.subprocess.run
    theme.shutil.which = lambda program: '/usr/bin/magick' if program == 'magick' else None
    class ImageResult:
        returncode = 0
        stdout = bytes((230, 47, 7, 32, 16, 24))
        stderr = b''
    theme.subprocess.run = lambda *args, **kwargs: ImageResult()
    assert theme.sample_colors('wallpaper') == ['#e62f07', '#201018']
    theme.subprocess.run = original_run
    theme.shutil.which = original_which
    print('PASS raw ImageMagick palette extraction')
    theme.shutil.which = lambda program: '/usr/bin/kvantummanager' if program == 'kvantummanager' else original_which(program)
    spec.loader.exec_module(theme)
    assert 'style=kvantum' in theme.build_qt6ct_config()
    theme.shutil.which = original_which
    theme.KVANTUM_TEMPLATE_DIR = str(template)
    Path(theme.KVANTUM_CONFIG_FILE).parent.mkdir(parents=True)
    Path(theme.KVANTUM_CONFIG_FILE).write_text('[General]\ntheme=Other\n[Personal]\nKeep=yes\n')
    assert theme.write_kvantum_theme(samples[0][1])
    selected = configparser.RawConfigParser()
    selected.read(theme.KVANTUM_CONFIG_FILE)
    assert selected['General']['theme'] == 'Strata'
    assert selected['Personal']['Keep'] == 'yes'
    assert Path(theme.KVANTUM_THEME_DIR, 'Strata.svg').is_file()
    print('PASS Kvantum generation and preference merge')
    Path(theme.KATE_CONFIG_FILE).parent.mkdir(parents=True, exist_ok=True)
    Path(theme.KATE_CONFIG_FILE).write_text('[General]\nKeep=yes\n[KTextEditor Renderer]\nColor Theme=Breeze Light\n')
    theme.write_kate_theme(samples[0][1])
    kate_config = configparser.RawConfigParser()
    kate_config.read(theme.KATE_CONFIG_FILE)
    assert kate_config['General']['Keep'] == 'yes'
    assert kate_config['KTextEditor Renderer']['Color Theme'] == 'Strata'
    assert kate_config['KTextEditor Renderer']['Auto Color Theme Selection'] == 'false'
    assert kate_config['KTextEditor Renderer']['Text Font'].startswith('JetBrains Mono,11,')
    assert Path(theme.KATE_THEME_FILE).is_file()
    theme.write_rishot_theme(samples[0][1])
    assert json.loads(Path(theme.RISHOT_PALETTE_FILE).read_text())['accent'] == samples[0][1]['accent']
    print('PASS Kate and Rishot generation and preference merge')
    for path in theme.KDE_APP_CONFIG_FILES:
        config_path = Path(path)
        config_path.write_text('[General]\nKeep=yes\n[UiSettings]\nColorScheme=BreezeLight\n')
    theme.write_kde_app_colors()
    for path in theme.KDE_APP_CONFIG_FILES:
        config = configparser.RawConfigParser()
        config.read(path)
        assert config['General']['Keep'] == 'yes'
        assert config['UiSettings']['ColorScheme'] == 'Strata'
    print('PASS KDE application scheme and preference merge')
    record_spec = importlib.util.spec_from_file_location('record', scripts / 'record.py')
    record = importlib.util.module_from_spec(record_spec)
    record_spec.loader.exec_module(record)
    record.shutil.which = lambda program: '/usr/bin/ffmpeg' if program == 'ffmpeg' else None
    for codecs, expected in [('libx264 libopenh264 mpeg4', 'libx264'),
                             ('libopenh264 mpeg4', 'libopenh264'),
                             ('mpeg4', 'mpeg4'), ('', 'mpeg4')]:
        class EncoderResult:
            stdout = '\n'.join(f' V..... {codec}' for codec in codecs.split())
        record.run = lambda *args, **kwargs: EncoderResult()
        assert record.mp4_codec() == expected
    print('PASS recording codec fallback selection')
    theme.write_libreoffice_dark()
    theme.write_libreoffice_dark()
    office = theme.ET.parse(theme.LIBREOFFICE_CONFIG_FILE)
    oor = '{http://openoffice.org/2001/registry}'
    appearance = [item for item in office.getroot().findall(oor + 'item')
                  if item.get(oor + 'path') == '/org.openoffice.Office.Common/Appearance']
    assert len(appearance) == 3
    values = {item.find(oor + 'prop').get(oor + 'name'): item.find(oor + 'prop').find('value').text
              for item in appearance}
    assert values == {'LibreOfficeTheme': '1', 'ApplicationAppearance': '2',
                      'UseOnlyWhiteDocBackground': 'false'}
    print('PASS LibreOffice dark-mode generation')
    # Concurrent independent state writers must not erase one another.
    for _ in range(8):
        theme.save_state({'activeTheme': 'adaptive', 'currentWallpaper': 'before'})
        code = 'import sys;sys.path.insert(0,sys.argv[1]);import theme_manager as t;t.save_state(__import__("json").loads(sys.argv[2]))'
        children = [subprocess.Popen([sys.executable, '-c', code, str(scripts), json.dumps(update)])
                    for update in [{'activeTheme': 'tokyo_night'}, {'currentWallpaper': 'after'}]]
        assert all(p.wait() == 0 for p in children)
        state = theme.load_state()
        assert state['activeTheme'] == 'tokyo_night' and state['currentWallpaper'] == 'after'
    print('PASS atomic concurrent persistence')
