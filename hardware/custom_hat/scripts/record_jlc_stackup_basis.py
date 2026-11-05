"""Apply the published layer thicknesses to explicitly bounded conductor models."""
import json
import math

import pcbnew
import pipeline


ROOT = pipeline.BASE.parents[1]
EVIDENCE = ROOT / 'docs/references/归档扩展板贴片与层叠复核'


def main():
    checkpoint = pipeline.current_checkpoint()
    thickness = {'F.Cu': 35, 'In1.Cu': 30, 'In2.Cu': 30, 'B.Cu': 35}
    stackup = {'pcb_sha256': checkpoint['pcb_sha256'], 'structure': 'JLC041611-7628',
        'source_url': 'https://tools.jlc.com/jlcTools/#/impedanceDefaultTemplate',
        'retrieved': '2026-11-02', 'filters': {'layers': 4, 'nominal_board_mm': 1.6, 'inner_oz': 1, 'outer_oz': 1},
        'status': 'published_structure_selected_as_design_basis_not_an_order_or_as_built_record',
        'copper_um': thickness, 'dielectrics_mm': [.203, 1.03, .203], 'calculated_stack_mm': 1.566,
        'published_finished_mm': 1.57, 'published_tolerance_percent': 10, 'Dk': None, 'Df': None,
        'evidence_text': 'jlc-four-layer-1oz-visible.txt', 'evidence_image': 'jlc-four-layer-1oz.jpg',
        'limits': ['Actual order and finished copper unverified', 'No inferred Dk/Df or impedance approval',
                   'AP64350 p22 recommends outer2oz and inner GND for thermal performance; this design differs and has no 3.5A thermal rating']}
    pipeline.write_json(EVIDENCE / 'stackup-design-basis.json', stackup)
    board = pcbnew.LoadBoard(str(pipeline.PRIMARY / (pipeline.STEM + '.kicad_pcb')))
    tracks = {item.m_Uuid.AsString(): item for item in board.GetTracks() if item.Type() != pcbnew.PCB_VIA_T}
    historical = ROOT / 'docs/references/扩展板电路仿真工具'
    header = json.loads((historical / 'five-volt-paths-20261031/header-route-contract.json').read_text(encoding='utf-8'))
    input_ids = {'93a89441-6459-41d7-956e-b7dfaa02fade', 'e1c190b7-cc1b-41a3-b0ce-d0889a72426a', 'e223a735-1756-4d40-87cd-cf00410a7e6e'}
    header_ids = {row['id'] for row in header['changes'] if row['after'] is not None}
    header_ids.update(identifier for route in header['trunk_routes'] for identifier in route['added_tracks'])
    groups = {'shared_input_selected_tracks': input_ids, 'five_volt_header_selected_tracks': header_ids,
              'C305_new_branch': {'1b4034f7-9d01-4b4c-9612-f2e08aea1675'}}
    cases = {}
    for name, identifiers in groups.items():
        segments = []
        for identifier in sorted(identifiers):
            item = tracks[identifier]
            layer = board.GetLayerName(item.GetLayer())
            length = math.dist(list(item.GetStart()), list(item.GetEnd())) / 1e6
            width = pcbnew.ToMM(item.GetWidth())
            resistance = .0005 * 35 / thickness[layer] * length / width
            segments.append({'uuid': identifier, 'layer': layer, 'net': item.GetNetname(), 'length_mm': length,
                             'width_mm': width, 'copper_um': thickness[layer], 'r25_ohm': resistance,
                             'old_uniform35um_ohm': .0005 * length / width})
        total = sum(row['r25_ohm'] for row in segments)
        old = sum(row['old_uniform35um_ohm'] for row in segments)
        cases[name] = {'segments': segments, 'selected_segment_sum_ohm': total, 'old_uniform35um_sum_ohm': old,
                       'increase_percent': 100 * (total / old - 1),
                       'scope': 'selected conductor series-sum only; not whole-board equivalent resistance'}
    positions = {}
    for reference in ('C305', 'C310'):
        footprint = board.FindFootprintByReference(reference)
        ground = next(pad for pad in footprint.Pads() if pad.GetNumber() == '2')
        positions[reference] = {'position_mm': [pcbnew.ToMM(value) for value in footprint.GetPosition()],
                               'ground_thermal_gap_mm': pcbnew.ToMM(ground.GetThermalGap()),
                               'thermal_angle_deg': ground.GetThermalSpokeAngle().AsDegrees()}
    pipeline.write_json(EVIDENCE / 'stackup-conductor-model.json', {'pcb_sha256': checkpoint['pcb_sha256'],
        'formula': 'R25 = 0.5mOhm/square *35um/t * length/width; TI SSZP640 p9 approximation',
        'cases': cases, 'capacitors': positions, 'hardware_measured': False, 'current_rating_assigned': False,
        'limits': ['No pad shorting, plane paths, via barrels, connectors, GND return or thermal coupling',
                   'Header group contains a branching graph; series sum is not a solved equivalent',
                   'C305 branch is a ripple-current path; DC resistance alone does not establish transient stability']})
    print(json.dumps({name: {key: value for key, value in case.items() if key != 'segments'} for name, case in cases.items()}))


if __name__ == '__main__':
    main()
