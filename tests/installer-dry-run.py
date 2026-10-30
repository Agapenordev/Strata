#!/usr/bin/env python3
"""Exercise ./install on a temporary HOME.

Every command (sudo, zypper, systemctl, ...) is recorded instead of run, and
the Tumbleweed and hardware checks are faked, so this is safe on any machine.
    python3 tests/installer-dry-run.py
"""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types

ROOT = Path(__file__).resolve().parents[1]
home = Path(tempfile.mkdtemp(prefix='strata-home-'))
os.environ['HOME'] = str(home)
for var in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'SSH_CONNECTION'):
    os.environ.pop(var, None)

loader = importlib.machinery.SourceFileLoader('strata_install', str(ROOT / 'install'))
spec = importlib.util.spec_from_loader('strata_install', loader)
si = importlib.util.module_from_spec(spec)
loader.exec_module(si)
si.STATE = home / '.local/state/strata-tumbleweed'

commands = []
repos = []


def fake_run(args, capture=False, check=True):
    args = list(map(str, args))
    commands.append(args)
    joined = ' '.join(args)
    out = ''
    if args[:2] == ['niri', '--version']:
        out = 'niri 26.04 (fake)'
    elif args[:2] == ['qs', '--version']:
        out = 'quickshell 0.3.2'
    elif 'list-configs' in args:
        out = 'Config | Subvolume\n-------+----------\nroot   | /\n'
    if 'zypper addrepo' in joined:
        repos.append(si.QUICKSHELL_REPO_URL)
    if 'openSUSE-repos-Tumbleweed-NVIDIA' in joined:
        repos.append('https://download.nvidia.com/opensuse/tumbleweed')
    return subprocess.CompletedProcess(args, 0, out, '')


si.run = fake_run
si.preflight = lambda chosen: None
si.repo_urls = lambda: list(repos)
si.repo_aliases = lambda: [si.QUICKSHELL_REPO_ALIAS, 'repo-oss', 'repo-non-oss']
si.render_device = lambda: '/dev/dri/by-path/pci-0000:01:00.0-render'
si.power_manager_conflict = lambda: ''
real_exists = Path.exists
Path.exists = lambda self: True if str(self) in ('/etc/pam.d/swaylock',) else real_exists(self)

args = types.SimpleNamespace(ac_profile='performance')
everything = {group.id for group in si.GROUPS}

# A home whose files differ

(home / '.config/niri').mkdir(parents=True)
(home / '.config/niri/config.kdl').write_text('// old config\n')
(home / '.config/dolphinrc').write_text('[Personal]\nKeep=yes\n')

# Everything

si.install(everything, args)
stamp = sorted(p.name for p in (si.STATE / 'backups').iterdir())[-1]

niri = ROOT / 'home/.config/niri'
for part in sorted(niri.rglob('*.kdl')):
    name = part.relative_to(niri)
    installed = (home / '.config/niri' / name).read_text()
    if str(name) == 'local.kdl':
        assert installed.startswith(part.read_text()), 'local.kdl lost its template'
        assert 'render-drm-device "/dev/dri/by-path/pci-0000:01:00.0-render"' in installed, 'GPU not written'
    else:
        assert installed == part.read_text(), f'niri {name} not installed'
for shared in ('display.kdl', 'input.kdl', 'binds/apps.kdl'):
    text = (niri / shared).read_text()
    assert "01:00.0" not in text and 'layout "fr"' not in text and 'Mullvad' not in text, f'{shared} is not generic'

assert (home / '.local/bin/nvidia-run').is_file()
assert (home / '.local/bin/strata-power').is_file()
assert 'STRATA_AC_PROFILE=performance' in (home / '.config/systemd/user/strata-power.service.d/profile.conf').read_text()
assert (home / '.zshrc').is_file() and (home / '.config/starship.toml').is_file()
assert (home / '.config/mimeapps.list').is_file()
assert (home / '.local/share/color-schemes/Strata.colors').is_file()
assert 'theme=Strata' in (home / '.config/Kvantum/kvantum.kvconfig').read_text()
assert 'Keep=yes' in (home / '.config/dolphinrc').read_text()
assert (home / '.local/bin/rishot').is_file()

flat = [' '.join(c) for c in commands]
for needle in ['snapper create', 'zypper addrepo', 'openSUSE-repos-Tumbleweed-NVIDIA',
               'nvidia-open-driver-G06-signed-kmp-meta', 'nvidia-gl-G06-32bit', 'nvtop',
               '--from home_AvengeMedia_danklinux quickshell', 'niri xwayland-satellite',
               'firewall-cmd --set-default-zone=public', '60-strata-hardening.conf', '60-strata-battery.conf',
               'gamemode mangohud steam', 'swayimg imv mpv vlc', 'zsh starship fastfetch btop',
               'dolphin MozillaFirefox', 'sddm-qt6', 'usr/share/sddm/themes/strata/Main.qml',
               'usr/share/sddm/themes/strata/components/Notch.qml', 'usr/share/fonts/strata/Rubik.ttf',
               'fc-cache -f /usr/share/fonts/strata', 'usr/lib/strata/avatar', 'org.strata.avatar.policy', 'systemctl enable --force sddm.service',
               'systemctl set-default graphical.target', 'power-profiles-daemon.service',
               'systemctl --user enable strata.service strata-power.service',
               'niri validate --config']:
    assert any(needle in c for c in flat), f'missing step: {needle}'
assert flat.index(next(c for c in flat if 'snapper create' in c)) < \
       flat.index(next(c for c in flat if 'zypper addrepo' in c)), 'snapshot must come before repository changes'
sddm = ROOT / 'system/usr/share/sddm/themes/strata'
for path in sddm.rglob('*.qml'):
    assert all(not (0xe000 <= ord(c) <= 0xf8ff or 0xf0000 <= ord(c) <= 0xffffd)
               for c in path.read_text()), f'SDDM depends on an icon-font glyph: {path}'
installed_sddm = {c.split()[-1] for c in flat if c.startswith('sudo install -D')}
for relative in [str(p.relative_to(ROOT / 'system')) for p in sddm.rglob('*') if p.is_file()]:
    assert '/' + relative in installed_sddm, f'SDDM file not installed: {relative}'

# local.kdl is the user's after the first run.
(home / '.config/niri/local.kdl').write_text('// mine\n')
commands.clear()
si.install(everything, args)
assert (home / '.config/niri/local.kdl').read_text() == '// mine\n', 'local.kdl was replaced'

# Undo the first run

si.restore(stamp)
assert (home / '.config/niri/config.kdl').read_text() == '// old config\n', 'restore failed'
assert (home / '.config/dolphinrc').read_text() == '[Personal]\nKeep=yes\n'
print(f'OK: everything installed, local.kdl kept, restored, in {home}')

# The desktop alone

alone = Path(tempfile.mkdtemp(prefix='strata-alone-'))
os.environ['HOME'] = str(alone)
si.STATE = alone / '.local/state/strata-tumbleweed'
real_home = Path.home
Path.home = classmethod(lambda cls: alone)
commands.clear()
si.install(set(), args)
flat = [' '.join(c) for c in commands]
assert (alone / '.config/quickshell/shell.qml').is_file() and (alone / '.config/niri/local.kdl').is_file()
assert 'render-drm-device' not in (alone / '.config/niri/local.kdl').read_text()
for absent in ('.zshrc', '.config/mimeapps.list', '.local/bin/strata-power', '.local/bin/nvidia-run'):
    assert not (alone / absent).exists(), f'{absent} installed without its group'
for needle in ('sddm', 'firewall', 'nvidia', 'steam', 'strata-power', 'swayimg'):
    assert not any(needle in c for c in flat if not c.startswith('niri') and 'cp --parents' not in c), \
        f'desktop-only install ran a {needle} step'
assert any('systemctl --user enable strata.service' == c for c in flat)
Path.home = real_home
print('OK: the desktop alone installs nothing optional')

# Choosing

def chosen_with(**flags):
    namespace = types.SimpleNamespace(yes=True, dry_run=False, with_=None, without=None)
    namespace.__dict__.update(flags)
    return si.choose(namespace)


si.has_nvidia = lambda: False
for group in si.GROUPS:
    if group.id == 'nvidia':
        group.offer = group.suggest = lambda: False
defaults = chosen_with()
assert {'login', 'apps', 'media', 'terminal'} <= defaults and not defaults & {'gaming', 'privacy', 'nvidia'}
assert 'gaming' in chosen_with(with_='gaming') and 'apps' not in chosen_with(without='apps')
for bad in (dict(with_='nonsense'), dict(with_='nvidia')):
    try:
        chosen_with(**bad)
    except RuntimeError:
        pass
    else:
        raise AssertionError(f'{bad} was accepted')
print('OK: groups chosen from flags and suggestions')

# Flatpak Steam and NVIDIA

commands.clear()
si.ok = lambda args: True
si.quiet = lambda args: subprocess.CompletedProcess(args, 0, '580.196.07\n', '')
si.configure_flatpak_nvidia()
flat = [' '.join(c) for c in commands]
assert any('org.freedesktop.Platform.GL.nvidia-580-196-07' in c for c in flat)
assert any('--env=__VK_LAYER_NV_optimus=NVIDIA_only' in c for c in flat)
print('OK: Flatpak Steam NVIDIA runtime and PRIME offload')
