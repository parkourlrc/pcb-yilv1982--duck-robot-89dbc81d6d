"""Compute target differences and prepare an uninstalled zero-only proposal."""
import ast
import difflib
import hashlib
import json
import math
from pathlib import Path
import re
import tomllib

here = Path(__file__).resolve().parent
repo = here.parents[2]
snapshot = json.loads((here/'studio-home-targets-snapshot-final-20261101.json').read_text(encoding='utf-8-sig'))
sources = snapshot['sources']
for entry in sources.values():
    assert hashlib.sha256(entry['text'].encode()).hexdigest() == entry['sha256']
cal = tomllib.loads(snapshot['calibration_file']['text'])
live = snapshot['calibration_status']['result']['calibration']
assert live['joints'] == cal['joints'], 'Compare the actual loaded joint calibration'
assert not snapshot['poses'], 'Saved pose selection would require separate comparison'
assert not snapshot['state']['servo-directions.json']['exists']
centered = json.loads(snapshot['state']['servo-centered.json']['text'])
assert set(centered) == {str(j['id']) for j in cal['joints']}

def assignment(tree, name):
    return next(n.value for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))

official = assignment(ast.parse(sources['studio/servo_ops.py']['text']), 'OFFICIAL')
stand = next(v for k,v in zip(official.keys,official.values) if ast.literal_eval(k)=='stand')
stand_rad = ast.literal_eval(stand.elts[1])
home_rad = ast.literal_eval(assignment(ast.parse(sources['studio/commit.py']['text']), 'HOME_RAD'))
firmware = repo/'training/logs/b-feetech-walk-20261024/controller-preparation-20261031/controller-source/fanhao375-Microduck-kissqy-27d7921/microduck-hd1910/firmware'
model = (firmware/'duck-control/src/model.rs').read_text(encoding='utf-8')
match = re.search(r'pub const DEFAULT_POSITION:.*?=\s*\{\s*\[(.*?)\]', model, re.S)
native_home = [float(v.strip()) for v in match.group(1).split(',') if v.strip()]
assert native_home == [home_rad[j['name']] for j in cal['joints']]
rows=[]
for j in cal['joints']:
    jid, direction, angle = j['id'], j['direction'], home_rad[j['name']]
    assert direction == -1
    native_target = math.floor(j['zero_raw'] + direction*angle*4096/math.tau + 0.5)
    row = {'id':jid,'name':j['name'],'robotd_zero_raw':j['zero_raw'],'direction':direction,
           'home_rad':angle,'robotd_target_raw':native_target,'proposed_zero_raw':2048,
           'proposed_robotd_target_raw':math.floor(2048+direction*angle*4096/math.tau+0.5)}
    if jid in stand_rad:
        assert stand_rad[jid] == angle
        servo_target=round(2048+direction*stand_rad[jid]*4096/math.tau)
        row.update(servo_target_raw=servo_target,raw_delta=native_target-servo_target,
                   model_angle_delta_deg=direction*(native_target-servo_target)*360/4096)
        assert row['proposed_robotd_target_raw']==servo_target
    else:
        row.update(servo_target_raw=None,note='Servo stand does not command mouth; robotd HOME includes it')
    rows.append(row)

current=snapshot['calibration_file']['text']
pattern=r'(?P<key>"?zero_raw"?\s*=\s*)\d+'
proposal,count=re.subn(pattern,lambda m:m['key']+'2048',current)
assert count==15
expected=json.loads(json.dumps(cal))
for j in expected['joints']:j['zero_raw']=2048
assert tomllib.loads(proposal)==expected,'Only encoder zeros may change'
out=here/'studio-home-zero-alignment-proposed.toml'
out.write_text(proposal,encoding='utf-8')
(here/'studio-home-zero-alignment-proposed.diff').write_text(''.join(difflib.unified_diff(
    current.splitlines(True),proposal.splitlines(True),fromfile='current/hd1910-calibration.toml',
    tofile='proposed/hd1910-calibration.toml')),encoding='utf-8')
result={'date':'2026-11-01','evidence':'Live files and calibration-status; numerical targets, not observed joint angles',
        'runtime_file_joints_match':True,'centered_ids':sorted(int(v) for v in centered),
        'saved_poses':0,'directions_match':True,'common_home_angles_match':True,
        'rows':rows,'proposed_common_targets_equal':True,'proposal_installed':False,
        'preserved_fields':'All except 15 zero_raw values; calibrated and motion flags are unchanged'}
(here/'studio-home-target-comparison-20261101.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
