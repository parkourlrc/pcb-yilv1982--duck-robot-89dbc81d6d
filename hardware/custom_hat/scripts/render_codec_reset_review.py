"""Render native candidate pages and board layers for the codec reset review."""
import json
import hashlib
from pathlib import Path
import subprocess

import fitz


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/codec-reset-20261031"
CLI = Path.home() / "AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"


def main():
    candidate = json.loads((EVIDENCE / "candidate.json").read_text(encoding="utf-8"))
    project = Path(candidate["project"])
    outputs = []
    for layer in ("F.Cu", "B.Cu", "In2.Cu"):
        target = EVIDENCE / ("reset-board-" + layer + ".svg")
        subprocess.run([str(CLI), "pcb", "export", "svg", "--layers", layer + ",Edge.Cuts",
                        "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet",
                        "--output", str(target), str(project / "custom_hat_rev_a.kicad_pcb")], check=True)
        with fitz.open(target) as document:
            with fitz.open("pdf", document.convert_to_pdf()) as pdf:
                pdf[0].get_pixmap(matrix=fitz.Matrix(8, 8), alpha=False).save(target.with_suffix(".png"))
        outputs.append(str(target.with_suffix(".png")))
    for sheet in ("radxa_40p", "servo_ttl"):
        target = EVIDENCE / (sheet + "-review.pdf")
        subprocess.run([str(CLI), "sch", "export", "pdf", "--output", str(target), str(project / (sheet + ".kicad_sch"))], check=True)
        with fitz.open(target) as document:
            document[0].get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False).save(target.with_suffix(".png"))
            region = (100, 54, 158, 122) if sheet == "radxa_40p" else (162, 29, 278, 109)
            clip = fitz.Rect(*(value * 72 / 25.4 for value in region))
            detail = EVIDENCE / (sheet + "-detail.png")
            document[0].get_pixmap(matrix=fitz.Matrix(4, 4), clip=clip, alpha=False).save(detail)
            outputs.append(str(detail))
        outputs.append(str(target.with_suffix(".png")))
    package = ROOT / "hardware/custom_hat/rev_a/production-20261031-codec-reset-review"
    for side in ("front", "back"):
        source = package / ("assembly-" + side + ".svg")
        if not source.is_file():
            continue
        target = EVIDENCE / ("assembly-" + side + ".png")
        with fitz.open(source) as document:
            with fitz.open("pdf", document.convert_to_pdf()) as pdf:
                pdf[0].get_pixmap(matrix=fitz.Matrix(8, 8), alpha=False).save(target)
        outputs.append(str(target))
    sources = [project / name for name in ("custom_hat_rev_a.kicad_pcb", "radxa_40p.kicad_sch", "servo_ttl.kicad_sch")]
    (EVIDENCE / "render-manifest.json").write_text(json.dumps({"project": str(project), "outputs": outputs,
        "source_hashes": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        "native_exports": True, "assembly_source": str(package), "assembly_back_mirrored": True,
        "copper_views_mirrored": False}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
