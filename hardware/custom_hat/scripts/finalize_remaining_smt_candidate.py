"""Check the exact permitted source changes and prepare a primary-derived workspace."""
import copy
import json
from pathlib import Path
import shutil

import pipeline
from generate_rev_a import parse, first, children


EVIDENCE = pipeline.BASE.parents[1] / 'docs/references/归档扩展板贴片与层叠复核'


def identified(document):
    return {first(node, 'uuid')[1]: node for node in document[1:]
            if isinstance(node, list) and first(node, 'uuid')}


def main():
    checkpoint = pipeline.current_checkpoint()
    polarity = json.loads((EVIDENCE / 'polarity-01/candidate.json').read_text(encoding='utf-8'))
    candidate = pipeline.managed(Path(polarity['project']))
    name = pipeline.STEM + '.kicad_pcb'
    primary_hashes = pipeline.fingerprints(pipeline.PRIMARY)
    candidate_hashes = pipeline.fingerprints(candidate)
    if {key: value for key, value in primary_hashes.items() if key != name} != {
            key: value for key, value in candidate_hashes.items() if key != name}:
        raise RuntimeError('Candidate contains changes outside PCB')
    original_document = parse((pipeline.PRIMARY / name).read_text(encoding='utf-8'))
    candidate_document = parse((candidate / name).read_text(encoding='utf-8'))
    original = identified(original_document)
    updated = identified(candidate_document)
    expected = copy.deepcopy(original)
    moves = {'C305': ['138.5', '108.5'], 'C310': ['147.32', '112.65']}
    reset_ids = {'83669e25-22e2-4b64-9124-63e7934ed8a2', 'b094fe1c-af98-4390-acfb-715dd2e88014'}
    modified = []
    for identifier, node in expected.items():
        if node[0] == 'footprint':
            reference = next(prop[2] for prop in children(node, 'property') if prop[1] == 'Reference')
            if reference in moves:
                first(node, 'at')[1:3] = moves[reference]
                pad = next(pad for pad in children(node, 'pad') if pad[1] == '2')
                first(pad, 'zone_connect')[1] = '1'
                pad.insert(-1, ['thermal_bridge_width', '0.25'])
                pad.insert(-1, ['thermal_gap', '0.2'])
                modified.append(identifier)
        if identifier in reset_ids:
            first(node, 'end')[1:] = ['146.84', '112.65']
            modified.append(identifier)
        if node[0] == 'zone':
            expected[identifier] = [part for part in node if not isinstance(part, list) or part[0] != 'filled_polygon']
    normalized = {identifier: [part for part in node if not isinstance(part, list) or part[0] != 'filled_polygon']
                  if node[0] == 'zone' else node for identifier, node in updated.items()}
    expected_new = {'1b4034f7-9d01-4b4c-9612-f2e08aea1675'} | {mark['uuid'] for mark in polarity['marks']}
    mismatches = [identifier for identifier, node in expected.items() if node != normalized.get(identifier)]
    root_before = [node for node in original_document[1:] if not isinstance(node, list) or not first(node, 'uuid')]
    root_after = [node for node in candidate_document[1:] if not isinstance(node, list) or not first(node, 'uuid')]
    route = normalized['1b4034f7-9d01-4b4c-9612-f2e08aea1675']
    route_ok = all(first(route, key) == [key, *value] for key, value in {
        'start': ['137.025', '108.5'], 'end': ['142.4705', '115.9'], 'width': ['1.2'],
        'layer': ['F.Cu'], 'net': ['+5V']}.items())
    marks_ok = all(normalized[mark['uuid']][0:2] == ['gr_text', mark['text']]
                   and first(normalized[mark['uuid']], 'layer')[1] == 'F.SilkS'
                   and list(map(float, first(normalized[mark['uuid']], 'at')[1:3])) == mark['position_mm']
                   for mark in polarity['marks'])
    result = {'baseline_pcb_sha256': checkpoint['pcb_sha256'], 'candidate_pcb_sha256': pipeline.digest(candidate / name),
              'permitted_modified_objects': modified, 'permitted_added_objects': sorted(expected_new),
              'unexpected_changes': mismatches, 'root_settings_unchanged': root_before == root_after,
              'removed_objects': sorted(original.keys() - updated.keys()),
              'added_objects_match': updated.keys() - original.keys() == expected_new,
              'route_matches': route_ok, 'marks_match': marks_ok, 'non_pcb_files_unchanged': True,
              'zone_definitions_preserved': not any(original.get(identifier, [''])[0] == 'zone' for identifier in mismatches)}
    result['accepted'] = all((not mismatches, root_before == root_after, not result['removed_objects'],
                              result['added_objects_match'], route_ok, marks_ok))
    pipeline.write_json(EVIDENCE / 'source-diff-contract.json', result)
    if not result['accepted']:
        raise RuntimeError('Source change contract failed')
    work = pipeline.prepare(pipeline.PRIMARY)
    shutil.copy2(candidate / name, work / name)
    result['project'] = str(work)
    pipeline.write_json(EVIDENCE / 'final-candidate.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
