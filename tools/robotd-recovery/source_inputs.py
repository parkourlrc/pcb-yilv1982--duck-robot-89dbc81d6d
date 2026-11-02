"""固定本地来源；不下载、不连接设备、不读取账户配置。"""
from pathlib import Path
import hashlib
import json
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREP = ROOT / "training/logs/b-feetech-walk-20261024/controller-preparation-20261031"
SNAPSHOT = ROOT / "docs/references/b-feetech-policy-deployment-20261024/webpad-models-snapshot-20261101.json"
ARCHIVES = {
    "firmware": ("controller-source.tar.gz", "45cd22a955f3ff68bfbcb2d4266352d92798b6d1abd87a559fd613fcd52817d1", "fanhao375-Microduck-kissqy-27d7921/microduck-hd1910/firmware/"),
    "studio": ("studio-runtime.tar.gz", "fd4753ba11619607d36852f35080c62dc845fdffd005ef37aac74f61157b55ef", "studio/"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def baseline(component):
    name, expected, prefix = ARCHIVES[component]
    archive = PREP / name
    if sha(archive.read_bytes()) != expected:
        raise ValueError(f"来源压缩包哈希不符：{name}")
    files = {}
    with tarfile.open(archive) as package:
        for member in package:
            if member.isfile() and member.name.startswith(prefix):
                path = member.name[len(prefix):]
                if not path or Path(path).is_absolute() or ".." in Path(path).parts:
                    raise ValueError(f"不安全的来源路径：{path}")
                files[path] = package.extractfile(member).read()
    if component == "studio":
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        for path in ("studio/pad.py", "studio/pad_drive.py", "web/pad.js"):
            files[path] = snapshot["sources"][path]["text"].encode("utf-8")
    return files
