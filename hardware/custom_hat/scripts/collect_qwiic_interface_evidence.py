"""Archive the official connector schematic and scope evidence without assuming physical status."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

import fitz


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/qwiic-pinout-20261031"


def render_schematic(path, source_dir):
    pages = []
    with fitz.open(path) as document:
        if len(document) > 4:
            raise RuntimeError("Select schematic pages before rendering a larger document")
        for index, page in enumerate(document):
            image = source_dir / ("sparkfun-qwiic-p" + str(index + 1) + ".png")
            page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(image)
            pages.append({"page": index + 1, "image": image.name, "has_extractable_text": bool(page.get_text().strip())})
    return pages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attachment", type=Path)
    parser.add_argument("--render-only", action="store_true")
    arguments = parser.parse_args()
    source_dir = EVIDENCE / "sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    url = "https://docs.sparkfun.com/SparkFun_Qwiic_Hall_Effect_Sensor_TMAG5273/assets/board_files/schematic.pdf"
    path = source_dir / "sparkfun-qwiic-schematic.pdf"
    if arguments.render_only:
        record_path = EVIDENCE / "sources-and-scope.json"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["official_schematic"]["relevant_pages"] = render_schematic(path, source_dir)
        record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(record["official_schematic"]))
        return
    if arguments.attachment is None:
        parser.error("--attachment is required when collecting scope evidence")
    if path.exists():
        raise FileExistsError("Inspect the existing official connector evidence")
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "duck-robot-hat-review"}), timeout=30) as response:
        data = response.read()
    path.write_bytes(data)
    pages = render_schematic(path, source_dir)
    contents = arguments.attachment.read_bytes()
    lines = contents.decode("utf-8-sig").splitlines()
    selected = [{"line": index + 1, "text": line} for index, line in enumerate(lines) if "J504" in line]
    spec_path = ROOT / "docs/specs/20261028-custom-hat/spec.md"
    spec_lines = spec_path.read_text(encoding="utf-8").splitlines()
    scope = [{"line": index + 1, "text": line} for index, line in enumerate(spec_lines) if "| R04 |" in line or "| R05 |" in line]
    record = {"recorded_at": datetime.now(timezone.utc).isoformat(), "official_schematic": {"url": url, "file": str(path.relative_to(EVIDENCE)),
              "sha256": hashlib.sha256(data).hexdigest(), "relevant_pages": pages},
              "user_attachment": {"source_path": str(arguments.attachment), "sha256": hashlib.sha256(contents).hexdigest(),
                                  "line_count": len(lines), "headphone_term_count": sum("耳机" in line or "headphone" in line.lower() for line in lines),
                                  "j504_excerpts": selected},
              "current_spec": {"path": str(spec_path.relative_to(ROOT)), "sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(), "r04_r05": scope},
              "scope_limit": "Only the available attachment and current approved spec were checked; absence of a headphone request here is not a statement about every past conversation",
              "physical_manufacturing_status": "awaiting user clarification; do not infer an answer from silence"}
    (EVIDENCE / "sources-and-scope.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, ensure_ascii=False))


if __name__ == "__main__":
    main()
