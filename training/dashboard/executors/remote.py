from __future__ import annotations

import base64
import json
import shlex
import subprocess
import tarfile
from pathlib import Path


class Executor:
    def __init__(self, node_id, config):
        self.node_id = node_id
        self.config = config

    def ssh_command(self, command):
        if self.config.get('relay_target') and self.config.get('relay_destination'):
            inner = 'ssh -T -o BatchMode=yes -o ConnectTimeout=6 ' + shlex.quote(self.config['relay_destination']) + ' ' + shlex.quote(command)
            return ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6', self.config['relay_target'], inner]
        return ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6', self.config['ssh_target'], command]

    def shell(self, script, timeout=20, input_bytes=None):
        if self.config['kind'] == 'wsl':
            argv = ['wsl.exe']
            if self.config.get('distribution'):
                argv += ['-d', self.config['distribution']]
            argv += ['--exec', 'bash', '-lc', script]
        else:
            argv = self.ssh_command('bash -lc ' + shlex.quote(script))
        process = subprocess.run(argv, input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
        if process.returncode:
            raise RuntimeError(process.stderr.decode(errors='replace').strip() or f'executor exit {process.returncode}')
        return process.stdout.decode(errors='replace')

    def probe(self):
        required = ['work_root', 'python'] if self.config['kind'] == 'wsl' else ['work_root', 'benchmark_root', 'env_file']
        missing = [key for key in required if not self.config.get(key)]
        if missing:
            raise ValueError('节点未配置: ' + ', '.join(missing))
        quote = shlex.quote
        if self.config['kind'] == 'wsl':
            script = f'test -x {quote(self.config["python"])} && {quote(self.config["python"])} -c ' + quote('import torch; assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0))')
        else:
            script = f'test -f {quote(self.config["env_file"])} && test -f {quote(self.config["benchmark_root"] + "/venv/pyvenv.cfg")} && sudo -n docker info --format ' + quote('{{.ServerVersion}}')
        return self.shell(script, timeout=30).strip()

    def prepare(self, snapshot, directory):
        snapshot = Path(snapshot)
        archive = snapshot.parent / 'project.tar'
        with tarfile.open(archive, 'w') as handle:
            handle.add(snapshot, arcname='project')
        script = f'mkdir -p {shlex.quote(directory)} && tar -xf - -C {shlex.quote(directory)}'
        self.shell(script, timeout=120, input_bytes=archive.read_bytes())

    def write_json(self, remote_path, value):
        encoded = base64.b64encode(json.dumps(value).encode()).decode()
        script = 'import base64,os,pathlib; p=pathlib.Path(' + repr(remote_path) + '); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_suffix(".tmp"); t.write_bytes(base64.b64decode(' + repr(encoded) + ')); os.replace(t,p)'
        self.shell('python3 -c ' + shlex.quote(script))

    def launch(self, job, directory):
        self.write_json(directory + '/job.json', job)
        supervisor = directory + '/project/training/dashboard/executors/supervisor.py'
        script = f'nohup python3 {shlex.quote(supervisor)} {shlex.quote(directory + "/job.json")} </dev/null >{shlex.quote(directory + "/supervisor-launch.log")} 2>&1 & supervisor_pid=$!; ' + f'for attempt in $(seq 1 50); do test -f {shlex.quote(directory + "/supervisor.json")} && exit 0; kill -0 "$supervisor_pid" 2>/dev/null || break; sleep 0.1; done; cat {shlex.quote(directory + "/supervisor-launch.log")} >&2; exit 1'
        self.shell(script)

    def read_json(self, remote_path):
        try:
            return json.loads(self.shell('cat ' + shlex.quote(remote_path), timeout=10))
        except (RuntimeError, ValueError):
            return None

    def job_alive(self, directory):
        if self.config['kind'] == 'ssh':
            job_id = directory.rstrip('/').rsplit('/', 1)[-1]
            prefix = 'duck-dashboard-' + job_id + '-'
            containers = self.shell('sudo -n docker ps --filter ' + shlex.quote('name=' + prefix) + ' --format ' + shlex.quote('{{.Names}}')).splitlines()
            if any(name in (prefix + '0', prefix + '1') for name in containers):
                return True
        script = 'import pathlib,json; target=' + repr(directory) + '; matches=[]\nfor path in pathlib.Path("/proc").glob("[0-9]*/cmdline"):\n try:\n  arguments=path.read_bytes().decode(errors="replace").split("\\0")\n  if target+"/job.json" in arguments or target+":/work" in arguments or target+"/run" in arguments: matches.append(path.parent.name)\n except (OSError,PermissionError): pass\nprint(json.dumps(bool(matches)))'
        return json.loads(self.shell('python3 -c ' + shlex.quote(script)))

    def read_jsonl(self, remote_path):
        try:
            text = self.shell('cat ' + shlex.quote(remote_path), timeout=10)
            if text and not text.endswith('\n'):
                return None
            return [json.loads(line) for line in text.splitlines()]
        except (RuntimeError, ValueError, subprocess.TimeoutExpired):
            return None

    def terminate(self, directory, container_name=None):
        if container_name:
            self.shell('sudo -n docker stop -t 15 ' + shlex.quote(container_name), timeout=25)
            return
        script = 'import json,pathlib,os,signal; p=pathlib.Path(' + repr(directory + '/supervisor.json') + '); s=json.loads(p.read_text()); pid=s.get("pid"); command=pathlib.Path("/proc/"+str(pid)+"/cmdline").read_bytes(); assert ' + repr(directory).encode().__repr__() + ' in command; os.kill(pid,signal.SIGTERM)'
        self.shell('python3 -c ' + shlex.quote(script))

    def sample(self):
        source = (Path(__file__).parents[1] / 'telemetry.py').read_bytes()
        encoded = base64.b64encode(source).decode()
        script = 'import base64; exec(compile(base64.b64decode(' + repr(encoded) + '),"telemetry.py","exec"))'
        return json.loads(self.shell('python3 -c ' + shlex.quote(script), timeout=10))

    def sample_wsl(self):
        source = (Path(__file__).parents[1] / 'telemetry.py').read_bytes()
        encoded = base64.b64encode(source).decode()
        script = 'import base64,json; namespace={"__name__":"telemetry"}; exec(compile(base64.b64decode(' + repr(encoded) + '),"telemetry.py","exec"),namespace); print(json.dumps(namespace["collect"](include_processes=True)))'
        return json.loads(self.shell(shlex.quote(self.config['python']) + ' -c ' + shlex.quote(script), timeout=10))

    def cache_checkpoints(self, remote_directory, local_directory):
        script = 'import pathlib,tarfile,sys; root=pathlib.Path(' + repr(remote_directory + '/run/checkpoints') + '); out=tarfile.open(fileobj=sys.stdout.buffer,mode="w|"); [(out.add(p,arcname=str(p.relative_to(root)))) for p in root.rglob("*.pt") if p.is_file()]; out.close()'
        if self.config['kind'] == 'wsl':
            argv = ['wsl.exe'] + (['-d', self.config['distribution']] if self.config.get('distribution') else []) + ['--exec', 'python3', '-c', script]
        else:
            argv = self.ssh_command('python3 -c ' + shlex.quote(script))
        response = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=True)
        import io
        root = Path(local_directory).resolve()
        root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(response.stdout)) as archive:
            for member in archive.getmembers():
                target = (root / member.name).resolve()
                if member.isfile() and target.is_relative_to(root):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    temporary = target.with_suffix('.download')
                    temporary.write_bytes(archive.extractfile(member).read())
                    temporary.replace(target)

    def sync_run(self, remote_directory, local_directory):
        script = 'import pathlib,tarfile,sys; root=pathlib.Path(' + repr(remote_directory) + '); out=tarfile.open(fileobj=sys.stdout.buffer,mode="w|"); [(out.add(p,arcname=str(p.relative_to(root)))) for p in root.rglob("*") if p.is_file() and p.suffix in (".json",".jsonl",".log") and "project" not in p.relative_to(root).parts and p.stat().st_size<50000000]; out.close()'
        if self.config['kind'] == 'wsl':
            argv = ['wsl.exe'] + (['-d', self.config['distribution']] if self.config.get('distribution') else []) + ['--exec', 'python3', '-c', script]
        else:
            argv = self.ssh_command('python3 -c ' + shlex.quote(script))
        response = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True)
        import io
        root = Path(local_directory).resolve()
        root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(response.stdout)) as archive:
            for member in archive.getmembers():
                target = (root / member.name).resolve()
                if not member.isfile() or not target.is_relative_to(root):
                    continue
                source = archive.extractfile(member)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(target.suffix + '.download')
                temporary.write_bytes(source.read())
                temporary.replace(target)
