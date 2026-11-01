#!/usr/bin/env python3
"""Read current service, RPC and kernel UART state without opening the UART."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import time


def command(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=10)
    return {'returncode': p.returncode, 'stdout': p.stdout, 'stderr': p.stderr}


def status():
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(3)
        s.connect('/run/robotd.sock')
        s.sendall(b'{"jsonrpc":"2.0","id":1,"method":"robot.busStatus","params":{}}\n')
        with s.makefile('rb') as f:
            return json.loads(f.readline())


def snapshot():
    return {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status': status(), 'uart_driver': Path('/proc/tty/driver/serial').read_text()}


def main():
    r = {'scope': 'Read-only OS and existing robotd RPC; no UART open, no motion or service change',
         'kernel': command(['uname', '-a']),
         'services': command(['systemctl', 'show', 'robotd', 'microduck-studio',
                              '-p', 'MainPID', '-p', 'ActiveState', '-p', 'ExecStart']),
         'robotd_sha256': hashlib.sha256(Path('/usr/local/bin/robotd').read_bytes()).hexdigest(),
         'uart_holders': [], 'sysfs': {}, 'snapshots': []}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    if os.readlink(fd) == '/dev/ttyS2':
                        r['uart_holders'].append({'pid': int(proc.name), 'fd': int(fd.name),
                            'cmdline': (proc/'cmdline').read_bytes().replace(b'\x00', b' ').decode()})
                except FileNotFoundError:
                    pass
        except FileNotFoundError:
            pass
    tty = Path('/sys/class/tty/ttyS2')
    for name in ['uartclk', 'type', 'line', 'xmit_fifo_size', 'flags', 'io_type', 'port', 'irq']:
        p = tty / name
        r['sysfs'][name] = p.read_text() if p.exists() else None
    node = tty / 'device/of_node'
    for name in ['compatible', 'clock-frequency', 'dmas', 'dma-names', 'reg-io-width', 'reg-shift']:
        p = node / name
        r['sysfs']['dt_' + name] = p.read_bytes().hex() if p.exists() else None
    r['snapshots'].append(snapshot())
    time.sleep(10)
    r['snapshots'].append(snapshot())
    r['recent_journal'] = command(['journalctl', '-u', 'robotd', '--since', '-10min',
                                   '-o', 'short-iso-precise', '--no-pager'])
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
