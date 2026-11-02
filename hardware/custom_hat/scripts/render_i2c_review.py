"""Render native KiCad SVG and source pages for the I2C change review."""
import json
import argparse
from pathlib import Path
import subprocess

import fitz


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/hat-simulation-tools-20261029/i2c-pullups-20261031"
CLI = Path.home() / "AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"


def main():
    global EVIDENCE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--cap-vias", action="store_true")
    parser.add_argument("--buck-thermal", action="store_true")
    parser.add_argument("--buck-control", action="store_true")
    arguments = parser.parse_args()
    EVIDENCE = arguments.evidence.resolve() if arguments.evidence else EVIDENCE
    candidate = json.loads((EVIDENCE / "candidate.json").read_text(encoding="utf-8"))
    board = Path(candidate["project"]) / "custom_hat_rev_a.kicad_pcb"
    for side in ("F", "B"):
        target = EVIDENCE / ("board-" + side + ".svg")
        subprocess.run([str(CLI), "pcb", "export", "svg", "--layers", f"{side}.Cu,{side}.Silkscreen,Edge.Cuts", "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet", "--output", str(target), str(board)], check=True)
        with fitz.open(target) as svg:
            pdf = fitz.open("pdf", svg.convert_to_pdf())
            page = pdf[0]
            page.get_pixmap(matrix=fitz.Matrix(7, 7), alpha=False).save(target.with_suffix(".png"))
            if side == "F" or arguments.buck_thermal or arguments.buck_control:
                bounds = page.rect
                region = (0.35,0.22,0.54,0.85) if arguments.buck_control else ((0.30,0.18,0.51,0.70) if arguments.buck_thermal else ((0.52, 0.32, 0.80, 0.72) if arguments.cap_vias else (0.63, 0.17, 0.80, 0.49)))
                clip = fitz.Rect(bounds.width * region[0], bounds.height * region[1], bounds.width * region[2], bounds.height * region[3])
                name = ("control-"+side+"-detail.png") if arguments.buck_control else (("buck-"+side+"-detail.png") if arguments.buck_thermal else ("cap-vias-detail.png" if arguments.cap_vias else "pullups-detail.png"))
                page.get_pixmap(matrix=fitz.Matrix(18, 18), clip=clip, alpha=False).save(EVIDENCE / name)
    for filename, pages in (("vishay-dcrcwe3.pdf", (0, 2)), ("ti-slva689.pdf", (2,))):
        if not (EVIDENCE / "sources" / filename).exists():
            continue
        with fitz.open(EVIDENCE / "sources" / filename) as document:
            for page_number in pages:
                document[page_number].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(EVIDENCE / "sources" / (Path(filename).stem + f"-p{page_number + 1}.png"))
    print(EVIDENCE)


if __name__ == "__main__":
    main()
