"""Resume the interrupted placement in a new candidate, preserving the source.

Use KiCad's native DRC after this preparation. This script is not a release gate.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

import pcbnew

from plan_rev_b_solder_access import ROOT, STEM, box, graphic_box, gap, vector


def signature(board):
    return {f.GetReference(): {
        'value': f.GetValue(), 'footprint': f.GetFPID().GetUniStringLibId(),
        'side': f.GetLayer(),
        'pins': sorted((p.GetNumber(), p.GetNetname()) for p in f.Pads()),
    } for f in board.GetFootprints()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', default='placement-r4')
    args = parser.parse_args()
    root = ROOT / 'docs/references/扩展板乙版降本/layout-spacing'
    source = root / 'placement-r3'
    target = root / args.name
    if target.exists():
        raise FileExistsError(target)
    target.mkdir()
    for file in source.iterdir():
        if file.is_dir() and file.name == 'duck.pretty':
            shutil.copytree(file, target / file.name)
        elif file.is_file() and (file.suffix.startswith('.kicad_') or file.name in {'fp-lib-table', 'sym-lib-table', 'net-contract.json'}):
            shutil.copy2(file, target / file.name)
    path = target / (STEM + '.kicad_pcb')
    board = pcbnew.LoadBoard(str(path))
    baseline_path = root / 'baseline-99ecc45d' / path.name
    baseline = pcbnew.LoadBoard(str(baseline_path))
    fps = {f.GetReference(): f for f in board.GetFootprints()}
    baseline_fps = {f.GetReference(): f for f in baseline.GetFootprints()}
    # Repack only the collision group; preserve all other accepted placements.
    desired = {'C712': (143.4, 109.4, 0), 'C711': (141.0, 111.0, 0),
               'R701': (146.4, 109.4, 0), 'TP801': (110.0, 108.0, 0),
               'TP803': (124.0, 107.5, 0)}
    fixed = [f for ref, f in fps.items() if ref not in desired and f.GetLayer() == pcbnew.F_Cu]
    header_pads = [box(p) for p in fps['J101'].Pads()]
    changes = {}
    for ref, (x0, y0, angle0) in desired.items():
        fp = fps[ref]
        candidates = []
        for dx in range(-36, 37):
            for dy in range(-8, 33):
                for angle in (angle0, (angle0 + 90) % 360):
                    candidates.append((dx*dx+dy*dy+(angle != angle0), x0+dx*.25, y0+dy*.25, angle))
        for _, x, y, angle in sorted(candidates):
            fp.SetOrientationDegrees(angle)
            fp.SetPosition(vector(x, y))
            bounds = graphic_box(fp, pcbnew.F_CrtYd)
            if bounds is None or bounds[0] < 100.25 or bounds[1] < 100.25 or bounds[2] > 164.75 or bounds[3] > 129.75:
                continue
            body = graphic_box(fp, pcbnew.F_Fab)
            if not ref.startswith('TP') and (body is None or min(gap(body, p) for p in header_pads) < 3.2):
                continue
            if any(gap(bounds, graphic_box(f, pcbnew.F_CrtYd)) < .05 for f in fixed if graphic_box(f, pcbnew.F_CrtYd)):
                continue
            break
        else:
            raise RuntimeError('No collision-free position for ' + ref)
        changes[ref] = [x, y, angle]
        fixed.append(fp)

    moved = [r for r, f in fps.items() if f.GetPosition() != baseline_fps[r].GetPosition() or f.GetOrientationDegrees() != baseline_fps[r].GetOrientationDegrees()]
    affected_nets = {p.GetNetname() for r in moved for p in fps[r].Pads() if p.GetNetname()}
    # Leave power routing outside the changed placement area for local repair.
    # Other affected nets are rerouted completely to avoid abandoned branches.
    reroute_nets = affected_nets - {'POWER_GND', 'VBATT_2S_IN', '+5V', '+5V_PRE_IDEAL'}
    envelopes = []
    for ref in moved:
        for fp in (fps[ref], baseline_fps[ref]):
            for p in fp.Pads():
                envelopes.append((box(p), p.GetNetname(), p.IsOnLayer(pcbnew.B_Cu)))
    removed = []
    for track in list(board.GetTracks()):
        erase = track.GetNetname() in reroute_nets
        if not erase:
            tb = box(track)
            for pb, net, through in envelopes:
                if (through or track.IsOnLayer(pcbnew.F_Cu)) and gap(tb, pb) < .35:
                    erase = True
                    break
        if erase:
            removed.append({'uuid': track.m_Uuid.AsString(), 'net': track.GetNetname()})
            board.Remove(track)
            track.thisown = False
    # Refill only after obsolete copper is removed.
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    assert signature(board) == signature(baseline), 'Component/pin contract changed'
    for ref in ['J101', 'H1', 'H2', 'H3', 'H4']:
        f, old = fps[ref], baseline_fps[ref]
        assert f.GetPosition() == old.GetPosition() and f.GetOrientationDegrees() == old.GetOrientationDegrees()
    pcbnew.SaveBoard(str(path), board)
    report = {'baseline_sha256': hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
              'pcb_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'repacked': changes, 'moved_from_baseline': moved,
              'rerouted_nets': sorted(reroute_nets), 'removed_tracks': removed,
              'status': 'placement prepared; unconnected copper requires routing and native DRC',
              'source_promoted': False}
    (target / 'preparation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'removed_tracks'}))
    print('Removed tracks:', len(removed))


if __name__ == '__main__':
    main()
