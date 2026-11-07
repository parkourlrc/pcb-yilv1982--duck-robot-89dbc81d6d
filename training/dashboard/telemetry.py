from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone


def collect(include_processes=False):
    import psutil
    memory = psutil.virtual_memory()
    disk = psutil.disk_io_counters()
    network = psutil.net_io_counters()
    values = {'cpu_percent': psutil.cpu_percent(interval=.15), 'memory_used_bytes': memory.used,
              'memory_available_bytes': memory.available, 'disk_read_bytes': disk.read_bytes if disk else None,
              'disk_write_bytes': disk.write_bytes if disk else None, 'network_rx_bytes': network.bytes_recv,
              'network_tx_bytes': network.bytes_sent}
    units = {key: ('%' if key.endswith('percent') else 'bytes') for key in values}
    for key, unit in [('gpu_util_percent', '%'), ('gpu_memory_used_bytes', 'bytes'), ('temperature_c', '°C'), ('power_w', 'W')]:
        values[key], units[key] = None, unit
    gpu_error = None
    try:
        process = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=3, check=True)
        rows = [row.split(',') for row in process.stdout.strip().splitlines()]
        if rows and len(rows[0]) == 4:
            for index, key in enumerate(('gpu_util_percent', 'gpu_memory_used_bytes', 'temperature_c', 'power_w')):
                try:
                    number = float(rows[0][index].strip())
                    values[key] = number * 1024 * 1024 if key == 'gpu_memory_used_bytes' else number
                except ValueError:
                    pass
        else:
            gpu_error = 'invalid_response'
    except FileNotFoundError:
        pass
    except subprocess.TimeoutExpired:
        gpu_error = 'query_timeout'
    except (OSError, subprocess.SubprocessError):
        gpu_error = 'query_failed'
    result = {'sample_utc': datetime.now(timezone.utc).isoformat(), 'monotonic_s': time.monotonic(),
            'scope': 'host_total', 'gpu_scope': 'device_0', 'memory_kind': 'device_reported_not_additive',
            'metrics': {key: {'value': value, 'unit': units[key], 'status': 'ok' if value is not None else 'unsupported'} for key, value in values.items()}}
    if gpu_error:
        for key in ('gpu_util_percent', 'gpu_memory_used_bytes', 'temperature_c', 'power_w'):
            result['metrics'][key].update(status='error', reason=gpu_error)
    if include_processes:
        processes = []
        for process in psutil.process_iter(['pid', 'cmdline', 'memory_info']):
            try:
                command = ' '.join(process.info['cmdline'] or [])
                if 'mjlab_duck.train_locomotion' in command or 'dashboard/replay_worker.py' in command:
                    processes.append({'pid': process.pid, 'kind': 'training' if 'mjlab_duck.train_locomotion' in command else 'replay', 'memory_rss_bytes': process.info['memory_info'].rss, 'gpu_memory_status': 'unsupported'})
            except psutil.Error:
                continue
        result['processes'] = processes
    return result


def rates(sample, previous):
    duration = sample['monotonic_s'] - previous['monotonic_s'] if previous else 0
    for counter in ('disk_read_bytes', 'disk_write_bytes', 'network_rx_bytes', 'network_tx_bytes'):
        current = sample['metrics'][counter]['value']
        old = previous['metrics'].get(counter, {}).get('value') if previous else None
        value = (current - old) / duration if duration > 0 and current is not None and old is not None and current >= old else None
        sample['metrics'][counter + '_s'] = {'value': value, 'unit': 'bytes/s', 'status': 'ok' if value is not None else 'no_baseline'}
    return sample


if __name__ == '__main__':
    print(json.dumps(collect(), allow_nan=False))
