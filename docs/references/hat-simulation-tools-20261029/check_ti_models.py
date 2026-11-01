import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parent
TOOLS = Path(os.environ['LOCALAPPDATA']) / 'duck-robot-tools'
MODELS = TOOLS / 'models' / 'ti'
ENGINE = TOOLS / 'ngspice-47' / 'Spice64' / 'bin' / 'ngspice_con.exe'
CASES = {
    'SCEM639': ('SCEM639/SN74LVC1G125.cir', 'output input enable vcc 0'),
    'SCEM579': ('SCEM579/SN74LVC1G125_PSPICE_AIO/sn74lvc1g125.lib', 'enable input 0 output vcc'),
}


def main():
    results = []
    for name, (relative, pins) in CASES.items():
        model = MODELS / relative
        deck = ROOT / f'{name}_compatibility.cir'
        log = ROOT / f'{name}_compatibility.log'
        deck.write_text(f'''TI model compatibility check only - not HAT validation
.include "{model.as_posix()}"
Vcc vcc 0 3.3
Vin input 0 PULSE(0 3.3 50n 1n 1n 100n 400n)
Ven enable 0 PULSE(0 3.3 1u 1n 1n 5u 10u)
Xbuf {pins} SN74LVC1G125
Rload output 0 10k
Cload output 0 15p
.tran 0.2n 2u
.meas tran enabled_high FIND v(output) AT=100n
.meas tran enabled_low FIND v(output) AT=300n
.meas tran disabled_pulldown FIND v(output) AT=1.9u
.end
''', encoding='utf-8')
        run = subprocess.run([str(ENGINE), '-n', '-D', 'ngbehavior=ps', '-b', '-o', str(log), str(deck)], capture_output=True, text=True, timeout=45)
        output = log.read_text(errors='replace') if log.exists() else run.stdout + run.stderr
        measurements = {key: float(value) for key, value in re.findall(r'^(enabled_high|enabled_low|disabled_pulldown)\s*=\s*([+\-\d.eE]+)', output, re.M)}
        passed = run.returncode == 0 and len(measurements) == 3 and measurements['enabled_high'] > 2.5 and abs(measurements['enabled_low']) < 0.4 and abs(measurements['disabled_pulldown']) < 0.1
        results.append({'model': name, 'model_sha256': hashlib.sha256(model.read_bytes()).hexdigest(), 'subcircuit_pin_order': pins, 'exit_code': run.returncode, 'measurements_V': measurements, 'compatibility_smoke_pass': passed, 'scope': '3.3V typical, 10k pulldown, 15pF load; no HAT signoff'})
    manifest = [{'file': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size} for path in MODELS.iterdir() if path.is_file()]
    report = {'engine': str(ENGINE), 'mode': 'PSpice compatibility (-D ngbehavior=ps)', 'downloads': manifest, 'results': results}
    (ROOT / 'model-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
