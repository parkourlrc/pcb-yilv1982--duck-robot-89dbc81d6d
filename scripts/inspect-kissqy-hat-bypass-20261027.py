"""只读解析 kissqy EPRO2 的 PCB/封装，核对 DATA 网络并生成参考定位图。"""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import math
import zipfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/schematics/kissqy-hat-reva-reference"
OUT = ROOT / "docs/references/pcb-pad-repair-20261027"
PHOTO = ROOT / "docs/photos/kissqy-hat-r33-bypass-reference-20261027.png"
NETS = {"DXL_DATA_INT", "DXL_DATA_CLAMPED", "DXL_DATA"}
FOCUS_REFS = {"R31", "R32", "R33", "TH1", "D4", "U5", "U6", "U7"}


def parse(path):
    docs = {}
    current = None
    tombstones = 0
    with zipfile.ZipFile(path) as archive:
        data = archive.read("HAT_REVA_SCH.epru")
        for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
            if "||" not in line:
                continue
            header, body = line.split("||", 1)
            header = json.loads(header)
            body = body[:-1] if body.endswith("|") else body
            if header["type"] == "DOCHEAD":
                meta = json.loads(body)
                current = (meta["docType"], meta["uuid"])
                docs.setdefault(current, {"meta": meta, "records": {}})
                continue
            if current is None:
                continue
            records = docs[current]["records"]
            identity = header.get("id", str(number))
            if not body or body == "|":
                records.pop(identity, None)
                tombstones += 1
                continue
            records[identity] = {"line": number, "header": header, "data": json.loads(body)}
        preview = archive.read("IMAGE/9d00f144890fd6bb.webp")
    pcb = docs[("PCB", "9d00f144890fd6bb")]
    rows = list(pcb["records"].values())
    attrs = defaultdict(dict)
    for row in rows:
        if row["header"]["type"] == "ATTR":
            d = row["data"]
            attrs[d["parentId"]][d["key"]] = d["value"]
    comps = {r["header"]["id"]: r for r in rows if r["header"]["type"] == "COMPONENT"}
    nets = {}
    for row in rows:
        if row["header"]["type"] == "PAD_NET":
            key = json.loads(row["header"]["id"])
            nets[(key[1], key[3])] = (key[2], row["data"]["padNet"], row["line"])
    pads, components = [], []
    for cid, row in comps.items():
        c = row["data"]
        ref = attrs[cid].get("Designator", "")
        fp = attrs[cid].get("Footprint")
        if not fp:
            continue
        components.append({"ref": ref, "x": c["x"], "y": c["y"], "angle": c["angle"],
                           "value": c.get("attrs", {}).get("Value"), "layer": c["layerId"]})
        angle = math.radians(c["angle"])
        for record in docs[("FOOTPRINT", fp)]["records"].values():
            if record["header"]["type"] != "PAD":
                continue
            d = record["data"]
            num, net, net_line = nets.get((cid, record["header"]["id"]), (d["num"], "", None))
            x = c["x"] + d["centerX"] * math.cos(angle) - d["centerY"] * math.sin(angle)
            y = c["y"] + d["centerX"] * math.sin(angle) + d["centerY"] * math.cos(angle)
            pads.append({"ref": ref, "pin": num, "net": net, "x": round(x, 4), "y": round(y, 4),
                         "layer": c["layerId"], "angle": c["angle"] + d.get("padAngle", 0),
                         "shape": d["defaultPad"], "source_line": net_line,
                         "footprint": fp, "footprint_pad_id": record["header"]["id"]})
    lines = [dict(r["data"], source_line=r["line"]) for r in rows if r["header"]["type"] == "LINE"]
    return {"source": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "epru_sha256": hashlib.sha256(data).hexdigest(), "units": "mil", "view": "top; x right, y up",
            "tombstones_processed": tombstones, "components": components, "pads": pads, "lines": lines}, preview


def by_pin(board, ref, pin):
    return next(p for p in board["pads"] if p["ref"] == ref and p["pin"] == pin)


def trace_connection(board, start, end, net):
    """核对本任务端点的同层线段连接；坐标四舍五入容差为0.01mil。"""
    def key(x, y):
        return round(x, 2), round(y, 2)
    graph = defaultdict(set)
    for ln in board["lines"]:
        if ln["netName"] == net and ln["layerId"] == 1:
            a, b = key(ln["startX"], ln["startY"]), key(ln["endX"], ln["endY"])
            graph[a].add(b)
            graph[b].add(a)
    todo = [key(start["x"], start["y"])]
    seen = set(todo)
    while todo:
        node = todo.pop()
        for nxt in graph[node] - seen:
            seen.add(nxt)
            todo.append(nxt)
    return key(end["x"], end["y"]) in seen


def font(n):
    return ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", n)


def render(board):
    im = Image.new("RGB", (1580, 1160), "#f2f5f8")
    d = ImageDraw.Draw(im)
    d.text((34, 22), "kissqy HAT REVA：跨过 DATA 串阻 R33 的两个候选点", font=font(31), fill="#152b40")
    d.text((34, 72), "仅适用本参考工程 · 不等同用户白色 HAT V1.2 · 此版 R31 是上拉，不能照位号短接", font=font(23), fill="#a02c27")
    preview = Image.open(SOURCE / "pcb-preview-2026-10-07.webp").convert("RGB")
    preview = preview.crop((0, 210, 1920, 1150))
    preview.thumbnail((645, 350))
    im.paste(preview, (30, 137))
    d.text((34, 490), "A：R32 第 2 焊盘（图中下端）", font=font(27), fill="#1267b1")
    d.text((34, 535), "DXL_DATA_INT：R33 内部数据侧", font=font(23), fill="#243d52")
    d.text((34, 599), "B：TH1 第 1 焊盘（图中下端）", font=font(27), fill="#b74609")
    d.text((34, 644), "DXL_DATA_CLAMPED：R33 保护侧", font=font(23), fill="#243d52")
    for i, text in enumerate([
        "连接 A、B：等效跨过 R33，保留 TH1。",
        "R33 在这两版工程中本来已是 0Ω。",
        "R32 上端是 3.3V，不能接成该端。",
        "TH1 上端通外部 DATA，会绕过 TH1。",
    ]):
        d.text((34, 722 + i * 44), text, font=font(23), fill="#273d4e")
    d.text((34, 944), "原件：2026-10-07 EPRO2 内嵌预览", font=font(20), fill="#526273")
    d.text((34, 976), "10-07 / 10-15 两版候选焊盘及走线相同", font=font(20), fill="#526273")

    # 右侧完全从PCB坐标和封装重绘；不对照片猜测针号，不绘制未经确认的实际飞线路径。
    left, top, scale = 715, 182, 1.75
    xmin, ymax = 585, -465
    def pt(x, y):
        return left + (x-xmin)*scale, top + (ymax-y)*scale
    d.rounded_rectangle((700, 131, 1545, 1080), radius=12, fill="#14262a")
    d.text((718, 145), "PCB 顶视局部（按实际焊盘 / 走线坐标重绘）", font=font(22), fill="white")
    colors = {"DXL_DATA_INT": "#3baff5", "DXL_DATA_CLAMPED": "#ffad55", "DXL_DATA": "#a374eb"}
    for ln in board["lines"]:
        if ln["netName"] not in NETS or ln["layerId"] != 1:
            continue
        a, b = pt(ln["startX"], ln["startY"]), pt(ln["endX"], ln["endY"])
        if all(705 < x < 1540 and 190 < y < 980 for x,y in [a,b]):
            d.line((a,b), fill=colors[ln["netName"]], width=max(3, round(ln["width"]*scale)))
    for p in board["pads"]:
        if p["ref"] not in FOCUS_REFS:
            continue
        x, y = pt(p["x"], p["y"])
        w,h=p["shape"]["width"]*scale,p["shape"]["height"]*scale
        angle=math.radians(p["angle"])
        corners=[(x+a*math.cos(angle)+b*math.sin(angle),y-a*math.sin(angle)+b*math.cos(angle))
                 for a,b in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]
        d.polygon(corners, fill=colors.get(p["net"], "#748687"), outline="#dce7e7", width=2)
        text=p["pin"]
        d.text((x-7,y-13),text,font=font(19),fill="#102028")
    for c in board["components"]:
        if c["ref"] not in FOCUS_REFS:
            continue
        x,y=pt(c["x"],c["y"])
        # 把位号置于器件中心；另用左/右说明避免覆盖选中焊盘。
        d.text((x-22,y-12),c["ref"],font=font(19),fill="#fff6b6",stroke_width=2,stroke_fill="#14262a")
    for ref,pin,label,col,dx,dy in [("R32","2","A","#64c5ff",32,20),("TH1","1","B","#ffb363",-58,18)]:
        p=by_pin(board,ref,pin);x,y=pt(p["x"],p["y"])
        d.ellipse((x-40,y-39,x+40,y+39),outline=col,width=5)
        d.text((x+dx,y+dy),label,font=font(34),fill=col,stroke_width=2,stroke_fill="#14262a")
    d.text((729, 1000), "蓝：内部 DATA    橙：钳位侧    紫：接口 DATA", font=font(19), fill="#e4ecef")
    d.text((729, 1034), "顶视：40P 排针在上、舵机接口在左；不指定飞线路径", font=font(19), fill="#e4ecef")
    d.text((34, 1110), "2026-10-27 · 原工程未改写 · 候选点已核网络与线段连续性；用户实物位置及损伤范围仍待确认", font=font(21), fill="#43576b")
    im.save(PHOTO)


def main():
    boards=[]
    for day in ["07", "15"]:
        path=SOURCE / f"ProPrj_HAT_REVA_SCH_2026-10-{day}.epro2"
        board,preview=parse(path)
        (SOURCE/f"pcb-preview-2026-10-{day}.webp").write_bytes(preview)
        a,b=by_pin(board,"R32","2"),by_pin(board,"TH1","1")
        r1,r2=by_pin(board,"R33","1"),by_pin(board,"R33","2")
        checks={"a_net_matches_r33_1":a["net"]==r1["net"]=="DXL_DATA_INT",
                "b_net_matches_r33_2":b["net"]==r2["net"]=="DXL_DATA_CLAMPED",
                "a_to_r33_1_copper":trace_connection(board,a,r1,a["net"]),
                "b_to_r33_2_copper":trace_connection(board,b,r2,b["net"]),
                "a_other_pad_is_3v3":by_pin(board,"R32","1")["net"]=="3V3",
                "b_other_pad_is_external_data":by_pin(board,"TH1","2")["net"]=="DXL_DATA",
                "r31_is_rx_pullup":{by_pin(board,"R31",p)["net"] for p in ["1","2"]}=={"3V3","TTL_RX_RAW"}}
        if not all(checks.values()):
            raise ValueError(checks)
        board["checks"]=checks
        board["candidate_a"]=a
        board["candidate_b"]=b
        board["distance_mm"]=math.hypot(a["x"]-b["x"],a["y"]-b["y"])*0.0254
        boards.append(board)
    render(boards[0])
    evidence={"date":"2026-10-27", "source_commit":"7c5fba929e668aab4fa86f608fb7586c0e9718b2",
              "scope":"kissqy参考工程候选点；不是白色HAT V1.2已核准维修点", "versions":[]}
    for b in boards:
        out={k:b[k] for k in ["source","sha256","epru_sha256","units","view","tombstones_processed","checks","candidate_a","candidate_b","distance_mm"]}
        out["relevant_components"]=[c for c in b["components"] if c["ref"] in FOCUS_REFS]
        out["relevant_pads"]=[p for p in b["pads"] if p["net"] in NETS or p["ref"] in ["R31","R32","TH1"]]
        out["relevant_lines"]=[ln for ln in b["lines"] if ln["netName"] in NETS]
        evidence["versions"].append(out)
    same=all(by_pin(boards[0],ref,pin)[k]==by_pin(boards[1],ref,pin)[k]
             for ref,pin in [("R32","2"),("TH1","1"),("R33","1"),("R33","2")]
             for k in ["net","x","y","angle","shape"])
    evidence["two_versions_candidate_geometry_equal"]=same
    evidence["figure"]={"path":PHOTO.relative_to(ROOT).as_posix(),"sha256":hashlib.sha256(PHOTO.read_bytes()).hexdigest()}
    (OUT/"kissqy-bypass-evidence-20261027.json").write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"same_geometry":same,"checks":[b["checks"] for b in boards],"figure":str(PHOTO)},ensure_ascii=False))


if __name__=="__main__":
    main()
