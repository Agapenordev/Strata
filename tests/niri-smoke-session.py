#!/usr/bin/env python3
"""Run shell IPC checks in a self-contained disposable nested Niri."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

root = Path(__file__).resolve().parents[1]
config = root / 'home/.config/quickshell'
if os.environ.get('STRATA_NIRI_SMOKE') != 'nested':
    with tempfile.TemporaryDirectory(prefix='strata-niri-smoke-') as home:
        environment = os.environ.copy()
        environment['HOME'] = home
        # The session may export these; they would point back into the real home.
        for variable in ('XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME'):
            environment.pop(variable, None)
        environment['STRATA_NIRI_SMOKE'] = 'nested'
        environment.pop('NIRI_SOCKET', None)
        result = subprocess.run(
            ['niri', '--config', str(root / 'home/.config/niri/config.kdl'), '--',
             sys.executable, str(Path(__file__).resolve())],
            env=environment, timeout=90)
        passed = Path(home, 'passed').is_file()
        if result.returncode != 0 or not passed:
            for name in ('shell.log', 'ipc.log'):
                path = Path(home, name)
                if path.is_file():
                    sys.stderr.write(path.read_text())
            raise SystemExit(result.returncode or 1)
        print('PASS isolated nested-Niri shell IPC checks')
    raise SystemExit(0)

if not os.environ.get('NIRI_SOCKET'):
    raise RuntimeError('Refusing to run without the nested compositor IPC socket')

log = Path(os.environ['HOME']) / 'shell.log'
with log.open('w') as out:
    shell = subprocess.Popen(['qs', '-p', str(config)], stdout=out, stderr=subprocess.STDOUT)
    try:
        time.sleep(5)
        for target, method, args in [
            ('shortcut-settings', 'press', []), ('shortcut-settings', 'press', []),
            ('panel', 'open', ['launcher']), ('panel', 'close', []),
            ('panel', 'open', ['controls']), ('panel', 'close', []),
            ('panel', 'open', ['packages']), ('panel', 'close', []),
            ('panel', 'open', ['overview']), ('panel', 'open', ['overview']),
            # Every shell target bound in home/.config/niri/binds/shell.kdl.
            ('shortcut-launcher', 'press', []), ('shortcut-launcher', 'press', []),
            ('shortcut-controls', 'press', []), ('shortcut-controls', 'press', []),
            ('shortcut-session', 'press', []), ('panel', 'close', []),
            ('shortcut-clipboard', 'press', []), ('panel', 'close', []),
            ('shortcut-emoji', 'press', []), ('panel', 'close', []),
            ('shortcut-notes', 'press', []), ('panel', 'close', []),
            ('shortcut-game', 'press', []), ('shortcut-game', 'press', []),
            ('settings', 'set', ['dockAutohide', 'false']),
            ('widgets', 'arrange', ['on', '']), ('widgets', 'arrange', ['off', '']),
            ('status', 'get', []),
        ]:
            result = subprocess.run(['qs', '-p', str(config), 'ipc', 'call', target, method, *args],
                                    text=True, capture_output=True, timeout=10)
            with (Path(os.environ['HOME']) / 'ipc.log').open('a') as report:
                report.write(f'{target} {method} {args}: {result.returncode}\n{result.stdout}\n{result.stderr}\n')
            if result.returncode != 0:
                raise RuntimeError(f'{target} {method} {args}: {result.stdout}{result.stderr}')
            time.sleep(0.7)
        Path(os.environ['HOME'], 'passed').touch()
    finally:
        shell.terminate()
        shell.wait(timeout=10)
        subprocess.run(['niri', 'msg', 'action', 'quit', '--skip-confirmation'])
