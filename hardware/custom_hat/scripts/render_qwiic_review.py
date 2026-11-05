"""Render the A.1 connector correction and native schematic for visual review."""
import hashlib
import json
from pathlib import Path
import subprocess

import fitz


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "docs/references/扩展板电路仿真工具/qwiic-pinout-20261031"
CLI = Path.home() / "AppData/Local/Programs/KiCad/10.0/bin/kicad-cli.exe"


def main():
    candidate = json.loads((EVIDENCE / "candidate.json").read_text(encoding="utf-8"))
    project = Path(candidate["project"])
    board = project / "custom_hat_rev_a.kicad_pcb"
    primary = ROOT / "hardware/custom_hat/rev_a" / board.name
    if candidate.get("promoted") and hashlib.sha256(primary.read_bytes()).hexdigest() != candidate["promoted_pcb_sha256"]:
        raise RuntimeError("Primary changed after this visual checkpoint")
    images = []
    for side in ("F", "B"):
        path = EVIDENCE / ("qwiic-board-" + side + ".svg")
        command = [str(CLI), "pcb", "export", "svg", "--layers", side + ".Cu," + side + ".Silkscreen,Edge.Cuts",
                   "--mode-single", "--fit-page-to-board", "--exclude-drawing-sheet", "--output", str(path)]
        if side == "B":
            command.append("--mirror")
        command.append(str(board))
        subprocess.run(command, check=True)
        with fitz.open(path) as document:
            with fitz.open("pdf", document.convert_to_pdf()) as pdf:
                pdf[0].get_pixmap(matrix=fitz.Matrix(8, 8), alpha=False).save(path.with_suffix(".png"))
                images.append(path.with_suffix(".png").name)
                if side == "B":
                    bounds = pdf[0].rect
                    clip = fitz.Rect(0, bounds.height * .20, bounds.width * .22, bounds.height * .56)
                    detail = EVIDENCE / "qwiic-b-detail.png"
                    pdf[0].get_pixmap(matrix=fitz.Matrix(24, 24), clip=clip, alpha=False).save(detail)
                    images.append(detail.name)
    schematic = project / "imu_tof.kicad_sch"
    pdf_path = EVIDENCE / "qwiic-schematic.pdf"
    subprocess.run([str(CLI), "sch", "export", "pdf", "--output", str(pdf_path), str(schematic)], check=True)
    with fitz.open(pdf_path) as document:
        document[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(EVIDENCE / "qwiic-schematic.png")
        clip = fitz.Rect(*(value * 72 / 25.4 for value in (165, 80, 218, 113)))
        document[0].get_pixmap(matrix=fitz.Matrix(5, 5), clip=clip, alpha=False).save(EVIDENCE / "qwiic-schematic-detail.png")
    images.extend(["qwiic-schematic.png", "qwiic-schematic-detail.png"])
    package = ROOT / "hardware/custom_hat/rev_a/production-20261031-qwiic-review"
    if package.is_dir():
        for side in ("front", "back"):
            source = package / ("assembly-" + side + ".svg")
            target = EVIDENCE / ("assembly-" + side + ".png")
            with fitz.open(source) as document:
                with fitz.open("pdf", document.convert_to_pdf()) as pdf:
                    pdf[0].get_pixmap(matrix=fitz.Matrix(8, 8), alpha=False).save(target)
            images.append(target.name)
        policy = json.loads((EVIDENCE / "dnp-stencil-policy.json").read_text(encoding="utf-8"))
        filtered = Path(policy["plot_work"]) / board.name
        if hashlib.sha256(filtered.read_bytes()).hexdigest() != policy["plot_copy_pcb_sha256"]:
            raise RuntimeError("Filtered-paste plotting copy changed")
        for label, plot_board in (("before", primary), ("after", filtered)):
            target = EVIDENCE / ("paste-" + label + ".svg")
            subprocess.run([str(CLI), "pcb", "export", "svg", "--layers", "F.Paste,Edge.Cuts", "--mode-single", "--fit-page-to-board",
                            "--exclude-drawing-sheet", "--output", str(target), str(plot_board)], check=True)
            with fitz.open(target) as document:
                with fitz.open("pdf", document.convert_to_pdf()) as pdf:
                    bounds = pdf[0].rect
                    clip = fitz.Rect(bounds.width * .82, bounds.height * .36, bounds.width * .99, bounds.height * .55)
                    image = EVIDENCE / ("c307-paste-" + label + ".png")
                    pdf[0].get_pixmap(matrix=fitz.Matrix(24, 24), clip=clip, alpha=False).save(image)
                    images.append(image.name)
    (EVIDENCE / "render-manifest.json").write_text(json.dumps({"pcb_sha256": hashlib.sha256(board.read_bytes()).hexdigest(),
        "schematic_sha256": hashlib.sha256(schematic.read_bytes()).hexdigest(), "images": images,
        "board_b_view_mirrored": True, "layers_shown": "copper, silkscreen, outline", "pin_numbers_not_screen_left_right": True}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
