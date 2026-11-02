#!/usr/bin/env python3
"""ARCHIVED, DO NOT RUN: one 53-byte goal write enabled all 15 servo torques.

Original experiment retained as evidence; entry point disabled. See research.md.
"""
import array
import datetime
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import time
import serial

sp = importlib.util.spec_from_file_location('traffic', Path(__file__).with_name('imu-traffic-isolation-20261101.py'))
t = importlib.util.module_from_spec(sp)
sp.loader.exec_module(t)
d = t.d
OUT = Path('/home/radxa/duck-runtime-stage-20261031/imu-write-boundary-20261101.json')

def uart(port):
    a = array.array('i', [0]*20)
    fcntl.ioctl(port.fileno(), 0x545D, a, True)  # TIOCGICOUNT
    return {'t_ns': time.monotonic_ns(), 'tx_pending': port.out_waiting, 'rx_pending': port.in_waiting,
            **dict(zip(['cts','dsr','rng','dcd','rx','tx','frame','overrun','parity','brk','buf_overrun'], a))}

def open_port():
    return serial.Serial('/dev/ttyS2', 1000000, timeout=.001, write_timeout=.02, exclusive=True)

def main():
    r = {'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'trials': [],
         'scope': 'No torque writes; repeat unchanged 42/2 or 42/6 targets while confirmed OFF.'}
    stopped = []
    port = None
    try:
        r['before'] = d.status()
        if r['before'].get('torque_state') != 'off' or r['before'].get('motion') is not None:
            raise RuntimeError('Robot not off and idle.')
        if Path('/run/microduck-helper/bus-held').exists():
            raise RuntimeError('Studio holds bus.')
        for u in ['microduck-studio', 'robotd']:
            if d.run(['systemctl','is-active','--quiet',u],False)['returncode'] == 0:
                stopped.append(u)
                d.run(['systemctl','stop',u])
                if u == 'microduck-studio' and d.status().get('torque_state') != 'off':
                    raise RuntimeError('Torque state changed.')
        if d.run(['fuser','/dev/ttyS2'],False)['stdout'].strip():
            raise RuntimeError('UART still held.')
        r['driver_before'] = Path('/proc/tty/driver/serial').read_text()
        for length in [2,6,2,6]:
            port = open_port()
            row = {'length': length, 'torque_before': t.require_off(port), 'before': t.snapshot(port)}
            r['trials'].append(row)
            goals = t.sync_read(port,42,6)
            row['goals_before'] = goals
            if not goals['ok']:
                raise RuntimeError('Goal read failed.')
            params = bytearray([42,length])
            for ident in t.IDS:
                params.append(ident)
                params.extend(bytes.fromhex(goals['replies'][ident])[:length])
            write = t.packet(254,131,params)
            row['write'] = write.hex()
            row['uart_before'] = uart(port)
            port.reset_input_buffer()
            row['write_return'] = port.write(write)
            time.sleep(.02)
            row['uart_after_20ms'] = uart(port)
            row['imu_read'] = d.read(port,56,15,.02)
            row['uart_after_read'] = uart(port)
            row['diagnostic_read'] = d.read(port,124,124,.1)
            row['servo_read'] = t.sync_read(port,40,1)
            row['uart_after_probes'] = uart(port)
            time.sleep(.1)
            row['imu_after_wait'] = d.read(port,56,15,.1)
            row['uart_after_wait'] = uart(port)
            port.close()
            port = open_port()
            row['after_reopen'] = d.read(port,124,124,.1)
            row['torque_after'] = t.require_off(port)
            row['goals_after'] = t.sync_read(port,42,6)
            row['uart_after_reopen'] = uart(port)
            port.close()
            port = None
            print(json.dumps({'bytes':len(write), 'imu_ok':row['imu_read']['ok'],
                'diag_ok':row['diagnostic_read']['ok'], 'servo_ok':row['servo_read']['ok'],
                'reopen_ok':row['after_reopen']['ok'], 'uart_before':row['uart_before'],
                'uart_after_20ms':row['uart_after_20ms'], 'uart_after_probes':row['uart_after_probes'],
                'diag_after':row['after_reopen'].get('diagnostics')}),flush=True)
        r['driver_after'] = Path('/proc/tty/driver/serial').read_text()
    except Exception as e:
        r['error'] = repr(e)
    finally:
        if port:
            port.close()
        r['restored'] = {u:d.run(['systemctl','start',u],False) for u in reversed(stopped)}
        time.sleep(2)
        try:
            r['after'] = d.status()
        except Exception as e:
            r['restore_status_error'] = repr(e)
        r['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        OUT.write_text(json.dumps(r,indent=2))
        os.chown(OUT,1000,1000)
        print(json.dumps({'output':str(OUT),'error':r.get('error'),'after_torque':r.get('after',{}).get('torque_state')}),flush=True)

if __name__ == '__main__':
    raise SystemExit('Archived: goal writes enabled torque; this experiment is disabled.')
