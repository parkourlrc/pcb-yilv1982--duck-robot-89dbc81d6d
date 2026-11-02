"""Build a local, portable CAM-review archive without internal paths or production authorization."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile

import pipeline


QUESTIONS = [
    ("M01", "板材/板厚/层叠", "65x30mm，普通4层，CAD标称1.6mm", "提供实际材料、各层厚度及成品公差"),
    ("M02", "各层铜厚", "外层1oz、内层1oz意向；现有铜损模型采用35um", "确认各层成品铜厚，不静默改为0.5oz内层"),
    ("M03", "codec唯一小机械孔", "0.35mm铜盘/0.15mm CAD孔/0.1mm名义环宽", "确认板厚、钻孔/孔位公差、工艺钻径与成品孔定义的联合接受条件"),
    ("M04", "填孔盖铜", "5个U301热孔+1个U701.7孔，详见via-process-requirements.csv", "逐孔确认填料、盖铜、平整度，不以普通盖油替代"),
    ("M05", "U701联合land", "0.875x0.25mm矩形与0.35mm via圆盘联合，Mask扩展0", "检查land/孔/阻焊/钢网的联合可制造性"),
    ("M06", "C307不贴装", "铜与阻焊保留，两个F.Paste开口已排除", "确认不装C307且相应位置不印锡膏"),
    ("M07", "双面装配/拼板", "52 SMT+6 THT，双面各3 fiducial", "反馈供料与贴装范围、夹持/工艺边/拼板、钢网及回流方案"),
    ("M08", "BOM供料与替代", "按MPN/Manufacturer提供，库存和采购匹配未确认", "逐项确认可供/缺料；任何替代先反馈，不能仅按相同封装替换"),
    ("M09", "坐标/面别", "Gerber/钻孔/坐标同原点；底面装配图镜像，CSV不再镜像", "提供对齐和旋转预览，核J101/J502及IC pin1"),
    ("M10", "装配高度", "H1/H2排母侧圆柱头外径不大于4.5mm，无垫圈/六角柱", "核实际堆叠、对插高度、螺钉长度和插接空间"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision-tag", default="")
    arguments = parser.parse_args()
    if arguments.revision_tag and not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", arguments.revision_tag):
        parser.error("revision-tag must contain 1-32 lowercase letters, digits or hyphens")
    checkpoint = pipeline.current_checkpoint()
    binding = checkpoint["review_binding"]
    root = pipeline.BASE.parents[1]
    output = root / binding["production_package"]
    evidence = (root / binding["checkpoint"]).parent
    audit = json.loads((evidence / "final-audit.json").read_text(encoding="utf-8"))
    if not audit.get("stencil_policy", {}).get("accepted") or audit["pcb_sha256"] != checkpoint["pcb_sha256"]:
        raise RuntimeError("Complete BOM/stencil audit must pass before bundling")
    failure_fields = ("cad_field_mismatches", "native_position_mismatches", "design_hash_mismatches", "output_hash_mismatches", "unexpected_output_files", "broken_current_links")
    if any(audit[field] for field in failure_fields) or audit["git_diff_check_exit"]:
        raise RuntimeError("Artifact audit contains unresolved failures")
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    package_name = "HAT-A1-CAM-review-" + checkpoint["pcb_sha256"][:12]
    if arguments.revision_tag:
        package_name += "-" + arguments.revision_tag
    folder = pipeline.BASE / "release-review" / package_name
    folder.mkdir(parents=True, exist_ok=False)
    fabrication = folder / "fabrication"
    fabrication.mkdir()
    allowed = {".gtl", ".gbl", ".g1", ".g2", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".gtp", ".gbp", ".drl", ".csv", ".svg"}
    copied = []
    for name, expected in manifest["outputs"].items():
        path = Path(name)
        if path.name != name or path.suffix not in allowed:
            raise RuntimeError("Unreviewed archive member: " + name)
        source = output / name
        if pipeline.digest(source) != expected:
            raise RuntimeError("Output changed before packaging: " + name)
        shutil.copy2(source, fabrication / name)
        copied.append(name)
    brief = (evidence / "manufacturing-brief.md").read_text(encoding="utf-8")
    brief = re.sub(r"\[本版生产审查包\]\([^)]*\)", "[生产文件](fabrication/)", brief)
    (folder / "MANUFACTURING-BRIEF.md").write_text(brief, encoding="utf-8")
    with (folder / "CAM-QUESTIONS.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["ID", "审核项", "设计意向", "所需反馈", "状态"])
        writer.writerows([*row, "待确认"] for row in QUESTIONS)
    readme = f"""# HAT Rev A.1 CAM与装配评审资料（未生产放行）

设计身份：A.1；PCB SHA256：{checkpoint['pcb_sha256']}。
本包在本机准备，未发送；用途是制造/装配可行性评估，不是生产、采购或付款指令。

- fabrication/含同版Gerber、独立PTH/NPTH钻孔、BOM、坐标、装配图及6处POFV要求。
- 58拟装件、52 SMT、6 THT；C307 DNP，当前钢网已排除其两个开口。
- A.1 J502为1=GND、2=3V3、3=SDA、4=SCL，旧Rev A不同。工程文件名保留rev_a系列。
- 板面标识DUCK HAT A.1。底面装配图已镜像，CPL/CAM坐标不再次镜像。
- 未附不明确层叠的默认Gerber Job，也未附临时候选、旧钢网或私有本机运行路径。

请按CAM-QUESTIONS.csv逐项反馈接受、条件接受或需修改，并给出条件/理由。
尤其核0.15mm机械孔、0.1mm名义环宽、6处填孔盖铜及QFN联合land。
当前BOM按MPN给出，料源/库存/贴装服务未确认，不能默许替代器件或直接形成贴装订单。

原生规则、连通与一致性检查通过不等于制造接受或实物功能验证。
整板供电/热/并发负载、保护/线束、实际音频/I2S/TTL/IMU/ToF与装配仍待验证。
需要实物才能完成的验收在制造之后进行，不能提前标为通过。
MANIFEST.json记录包内文件SHA，仅用于身份/完整性核对。
"""
    (folder / "README.md").write_text(readme, encoding="utf-8")
    files = sorted(path for path in folder.rglob("*") if path.is_file())
    for path in files:
        text = path.read_text(encoding="utf-8-sig")
        if re.search(r"[A-Za-z]:[\\/](?:Users|Projects)|/mnt/[a-z]/|AppData|file://", text, re.I):
            raise RuntimeError("Internal path appears in a portable review member: " + path.name)
    portable = {"schema_version": 1, "revision": "A.1", "package_revision": arguments.revision_tag, "pcb_sha256": checkpoint["pcb_sha256"],
                "purpose": "CAM and assembly feasibility review only", "manufacturing_released": False, "hardware_tested": False,
                "files": {path.relative_to(folder).as_posix(): pipeline.digest(path) for path in files}}
    pipeline.write_json(folder / "MANIFEST.json", portable)
    archive = folder.with_suffix(".zip")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(folder).as_posix())
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None or set(bundle.namelist()) != set(portable["files"]) | {"MANIFEST.json"}:
            raise RuntimeError("Review archive integrity check failed")
        for name, expected in portable["files"].items():
            if hashlib.sha256(bundle.read(name)).hexdigest() != expected:
                raise RuntimeError("Review archive hash differs: " + name)
    if pipeline.fingerprints(pipeline.PRIMARY) != checkpoint["design_hashes"]:
        raise RuntimeError("Design changed while preparing the portable archive")
    record = {"created_at": datetime.now(timezone.utc).isoformat(), "revision": "A.1", "package_revision": arguments.revision_tag, "pcb_sha256": checkpoint["pcb_sha256"],
              "archive": archive.relative_to(root).as_posix(), "sha256": pipeline.digest(archive), "size_bytes": archive.stat().st_size,
              "fabrication_files": copied, "portable_file_count": len(portable["files"]) + 1, "all_member_hashes_match": True,
              "internal_paths_in_shared_members": False, "uploaded": False, "fabricator_accepted": False, "production_ready": False}
    pipeline.write_json(evidence / "review-bundle.json", record)
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
