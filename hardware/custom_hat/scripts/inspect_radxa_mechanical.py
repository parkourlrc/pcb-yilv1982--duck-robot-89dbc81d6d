"""Measure official Radxa surfaces and compare declared HAT component envelopes."""
import argparse
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'.zcode/hat-mechanical-deps'))

from OCP.BRep import BRep_Tool
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.Bnd import Bnd_Box
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_FACE
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS

import pipeline


EVIDENCE = ROOT/'docs/references/归档扩展板机械适配复核'


def clipped_polygon(vertices, bounds):
    output = [list(point) for point in vertices]
    for axis, boundary, minimum in [(0,bounds[0],True),(0,bounds[2],False),(1,bounds[1],True),(1,bounds[3],False)]:
        incoming, output = output, []
        if not incoming:
            break
        previous = incoming[-1]
        previous_in = previous[axis]>=boundary if minimum else previous[axis]<=boundary
        for point in incoming:
            inside = point[axis]>=boundary if minimum else point[axis]<=boundary
            if inside != previous_in:
                fraction = (boundary-previous[axis])/(point[axis]-previous[axis])
                output.append([previous[index]+fraction*(point[index]-previous[index]) for index in range(3)])
            if inside:
                output.append(point)
            previous, previous_in = point, inside
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-envelopes',action='store_true')
    arguments=parser.parse_args()
    checkpoint = pipeline.current_checkpoint()
    source = EVIDENCE/'sources/radxa_zero_3w_3d.stp'
    if not source.is_file():
        bundle_path=source.parent/'radxa-zero3w-step.zip'
        manifest=json.loads((EVIDENCE/'sources-manifest.json').read_text(encoding='utf-8'))
        expected=next(row['sha256'] for row in manifest if row['file']==bundle_path.name)
        if pipeline.digest(bundle_path)!=expected:
            raise RuntimeError('Official STEP archive identity mismatch')
        with zipfile.ZipFile(bundle_path) as bundle:
            source.write_bytes(bundle.read(source.name))
    cache = ROOT/'.zcode/hat-mechanical-deps/radxa-surface-cache.npz'
    source_sha = pipeline.digest(source)
    if cache.exists():
        archive = np.load(cache)
        if str(archive['source_sha256'])!=source_sha:
            raise RuntimeError('STEP cache identity mismatch')
        triangles = archive['triangles']
        header_faces = archive['header_faces']
        valid = bool(archive['valid'])
    else:
        reader = STEPControl_Reader()
        if int(reader.ReadFile(str(source))) != 1:
            raise RuntimeError('Cannot read STEP')
        reader.TransferRoots()
        shape = reader.OneShape()
        valid = BRepCheck_Analyzer(shape).IsValid()
        mesh = BRepMesh_IncrementalMesh(shape,.02,False,.2,True)
        if not mesh.IsDone():
            raise RuntimeError('STEP mesh failed')
        explorer = TopExp_Explorer(shape,TopAbs_FACE)
        triangles, header_faces = [], []
        while explorer.More():
            face = TopoDS.Face_s(explorer.Current())
            box = Bnd_Box()
            BRepBndLib.AddOptimal_s(face,box)
            bounds = box.Get()
            if abs(bounds[2]-8.5)<1e-5 and abs(bounds[5]-8.5)<1e-5 and .2<bounds[3]-bounds[0]<.3 and .2<bounds[4]-bounds[1]<.3:
                header_faces.append([(bounds[0]+bounds[3])/2,(bounds[1]+bounds[4])/2,8.5])
            location = TopLoc_Location()
            tessellation = BRep_Tool.Triangulation_s(face,location)
            if tessellation is not None:
                transform = location.Transformation()
                for triangle_index in range(1,tessellation.NbTriangles()+1):
                    triangle = tessellation.Triangle(triangle_index).Get()
                    points = [tessellation.Node(index).Transformed(transform) for index in triangle]
                    triangles.append([[point.X(),point.Y(),point.Z()] for point in points])
            explorer.Next()
        triangles = np.asarray(triangles)
        header_faces = np.asarray(header_faces)
        np.savez_compressed(cache,triangles=triangles,header_faces=header_faces,source_sha256=source_sha,valid=valid)
    minimum = triangles.min(axis=1)
    maximum = triangles.max(axis=1)
    envelopes = json.loads((EVIDENCE/'hat-envelopes.json').read_text(encoding='utf-8'))
    if envelopes['pcb_sha256']!=checkpoint['pcb_sha256'] and not arguments.historical_envelopes:
        raise RuntimeError('Envelope table belongs to another PCB; use explicit historical mode or regenerate it')
    rows = []
    for item in envelopes['front_components']:
        left, top, right, bottom = item['bounds_pcb_mm']
        bounds = [left-100,130-bottom,right-100,130-top]
        mask=(maximum[:,0]>=bounds[0])&(minimum[:,0]<=bounds[2])&(maximum[:,1]>=bounds[1])&(minimum[:,1]<=bounds[3])&(maximum[:,2]>=0)
        candidates=triangles[mask]
        heights=[]
        for triangle in candidates:
            clipped=clipped_polygon(triangle,bounds)
            heights.extend(point[2] for point in clipped)
        height = max(heights) if heights else 0
        required_gap = height+item['height_mm']
        rows.append({**item,'bounds_radxa_xy_mm':bounds,'radxa_surface_max_z_mm':height,
                     'zero_margin_required_gap_mm':required_gap,'clearance_at_11p05_mm':11.05-required_gap,
                     'clearance_at_13p33_mm':13.33-required_gap})
    result = {'hat_pcb_sha256':envelopes['pcb_sha256'],'current_primary_sha256':checkpoint['pcb_sha256'],'historical_envelopes':envelopes['pcb_sha256']!=checkpoint['pcb_sha256'],'radxa_step_sha256':source_sha,
              'radxa_step_header_date':'2024-04-25','step_brep_valid':valid,'triangle_count':len(triangles),
              'mesh_linear_deflection_mm':.02,'header_pin_top_centers':header_faces.tolist(),
              'transform':'For top-side host header mating F-side HAT socket: Xhost=Xpcb-100; Yhost=130-Ypcb; Zhat_front=board_gap; HAT bodies point downward',
              'socket_body_nominal_mm':8.51,'official_host_header_tip_z_mm':8.5,
              'ssw_insertion_range_mm':[3.68,6.35],'nominal_connector_gap_range_mm':[10.66,13.33],
              'header_plastic_top_z_mm':2.5,'nominal_socket_seated_gap_mm':11.01,
              'front_component_envelopes':rows,
              'limits':['Reference CAD, not user board measurement; exact physical host revision unknown',
                        'Imported STEP is not a valid closed BRep; no solid-Boolean pass is claimed',
                        'Triangular surface plus conservative component boxes screens interpenetration; does not certify mating harness routing',
                        '11.05mm is a comparison using2.54mm header plastic plus8.51mm socket, not a selected standoff',
                        'Vendor insertion and dimensions are nominal; all tolerances and contact engagement still apply']}
    pipeline.write_json(EVIDENCE/'radxa-surface-envelope.json',result)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    from matplotlib.patches import Rectangle
    plt.rcParams['font.sans-serif']=['Microsoft YaHei']
    plt.rcParams['axes.unicode_minus']=False
    figure,axis=plt.subplots(figsize=(13,6.5))
    visible=triangles[maximum[:,2]>=-.01]
    colors=visible[:,:,2].mean(axis=1)
    order=np.argsort(colors)
    collection=PolyCollection(visible[order,:,:2],array=colors[order],cmap='viridis',edgecolors='none',clim=(0,8.5))
    axis.add_collection(collection)
    for row in rows:
        bounds=row['bounds_radxa_xy_mm']
        color='red' if row['clearance_at_11p05_mm']<0 else 'orange'
        axis.add_patch(Rectangle((bounds[0],bounds[1]),bounds[2]-bounds[0],bounds[3]-bounds[1],fill=False,edgecolor=color,linewidth=1.2))
        axis.text((bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2,row['reference'],ha='center',va='center',fontsize=8,color='black',bbox={'facecolor':'white','alpha':.7,'pad':1})
    axis.set(xlim=(-2,67),ylim=(-3,32),aspect='equal',xlabel='Radxa官方坐标 X / mm',ylabel='Radxa官方坐标 Y / mm',
             title='修改前96dcce92：Radxa参考表面高度与HAT F面器件包络\nF面朝向主控；未实装，未包含线束弯曲；红框仅代表11.05mm名义情景不满足')
    figure.colorbar(collection,ax=axis,label='参考表面 Z / mm')
    figure.tight_layout()
    figure.savefig(EVIDENCE/'radxa-hat-projection.png',dpi=150)
    print(json.dumps({'triangles':len(triangles),'valid_brep':valid,'header_tops':len(header_faces),'screen':rows},ensure_ascii=False))


if __name__=='__main__':
    main()
