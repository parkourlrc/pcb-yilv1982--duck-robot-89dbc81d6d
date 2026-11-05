import hashlib
import json
import shutil
from pathlib import Path


base = Path(__file__).resolve().parents[1]
source = base / "rev_a"
target = base / "rev_b"
old_stem = "custom_hat_rev_a"
new_stem = "custom_hat_rev_b"
expected = "86654c03b6c1c8f51f7d5a4bef469aceed2ddfc73433b3e50426940c2a23164a"
actual = hashlib.sha256((source / (old_stem + ".kicad_pcb")).read_bytes()).hexdigest()
if actual != expected:
    raise RuntimeError("A.1 source identity differs from approved baseline")
if target.exists():
    raise FileExistsError(target)
target.mkdir()
files = [path for path in source.iterdir() if path.is_file() and (path.suffix in {".kicad_sch", ".kicad_pro", ".kicad_dru", ".kicad_pcb"} or path.name in {"fp-lib-table", "sym-lib-table", "net-contract.json"})]
files = [path for path in files if path.suffix not in {".kicad_pcb", ".kicad_pro", ".kicad_dru"} or path.stem == old_stem]
manifest = []
for path in files:
    destination = target / path.name.replace(old_stem, new_stem)
    shutil.copy2(path, destination)
    manifest.append({"source": path.relative_to(base).as_posix(), "target": destination.relative_to(base).as_posix(), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
for directory in ("duck.pretty", "duck.3dshapes"):
    if (source / directory).is_dir():
        shutil.copytree(source / directory, target / directory)
for path in source.glob("*.kicad_sym"):
    shutil.copy2(path, target / path.name)
record = {"date": "2026-11-04", "status": "baseline_copy_not_revb_design", "production_ready": False, "source_pcb_sha256": expected, "files": manifest}
(target / "source-manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"target": str(target), "copied_files": len(manifest), "status": record["status"]}, ensure_ascii=False))
