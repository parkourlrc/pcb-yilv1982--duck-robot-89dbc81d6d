import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


base = Path(__file__).resolve().parent / "head-imu-update"
base.mkdir(exist_ok=True)
repository = "kissqy/Microduck-kissqy"
manifest = []


def fetch(name, url):
    record = {"file": name, "url": url, "observed_at": datetime.now().astimezone().isoformat()}
    try:
        with urlopen(Request(url, headers={"User-Agent": "duck-robot-hat-review"}), timeout=35) as response:
            content = response.read()
        (base / name).write_bytes(content)
        record.update(success=True, bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
        return content
    except Exception as error:
        record.update(success=False, error=str(error))
        return None
    finally:
        manifest.append(record)
        (base / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


head_bytes = fetch("head.json", f"https://api.github.com/repos/{repository}/commits/main")
if head_bytes is None:
    raise SystemExit("Could not retrieve current main")
head = json.loads(head_bytes)
commit = head["sha"]
tree_bytes = fetch("tree.json", f"https://api.github.com/repos/{repository}/git/trees/{commit}?recursive=1")
tree = json.loads(tree_bytes)["tree"] if tree_bytes else []
paths = [entry["path"] for entry in tree if entry["type"] == "blob" and any(word in entry["path"].lower() for word in ("hat", "imu", "gyro"))]
fetch("hardware-readme.md", f"https://raw.githubusercontent.com/{repository}/{commit}/hardware/README.md")
fetch("hat-timeline.md", f"https://raw.githubusercontent.com/{repository}/{commit}/hardware/HAT-TIMELINE.md")
fetch("hardware-commits.json", f"https://api.github.com/repos/{repository}/commits?path=hardware&per_page=12")
fetch("branches.json", f"https://api.github.com/repos/{repository}/branches?per_page=100")
fetch("releases.json", f"https://api.github.com/repos/{repository}/releases?per_page=5")
for local_name, source_path in (
    ("head-sensor-code.rs", "microduck-hd1910/firmware/tof/src/imu.rs"),
    ("assembly-head-clearance.js", "docs/assembly-head-clearance.js"),
    ("hat-20261015.epro2", "hardware/ProPrj_HAT_REVA_SCH_2026-10-15.epro2"),
    ("hat-20261007.epro2", "hardware/ProPrj_HAT_REVA_SCH_2026-10-07.epro2"),
):
    fetch(local_name, f"https://raw.githubusercontent.com/{repository}/{commit}/{quote(source_path)}")
print(json.dumps({"sha": commit, "commit_date": head["commit"]["committer"]["date"], "message": head["commit"]["message"], "relevant_paths": paths}, ensure_ascii=False, indent=2))
