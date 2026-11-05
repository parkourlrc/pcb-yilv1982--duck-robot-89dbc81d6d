from pathlib import Path
import argparse
import hashlib
import json

import fitz
from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    arguments = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    topic = root / "docs/references/扩展板乙版降本"
    output = topic / "engineering-feedback"
    output.mkdir(exist_ok=True)
    original = root / ".zcode/hat-order-feedback/engineer-original-20261105.jpg"
    original.parent.mkdir(parents=True, exist_ok=True)
    source_bytes = arguments.source.read_bytes()
    if original.exists() and original.read_bytes() != source_bytes:
        raise ValueError("Archived original differs; do not overwrite")
    original.write_bytes(source_bytes)
    picture = Image.open(original)
    if picture.size != (1168, 1712):
        raise ValueError("Unexpected source dimensions")
    redacted = picture.copy()
    ImageDraw.Draw(redacted).rectangle((55, 419, 650, 486), fill="white")
    redacted.save(output / "engineer-feedback-redacted-20261105.png")
    picture.crop((590, 1100, 820, 1515)).resize((690, 1245)).save(
        output / "engineer-detail-20261105.png"
    )
    for name, pages in [("mic-c7587901", [5, 6]), ("yxc-12mhz", [2])]:
        with fitz.open(topic / "sources" / f"{name}.pdf") as document:
            for page_number in pages:
                document[page_number - 1].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(
                    output / f"{name}-page{page_number}.png"
                )
    manifest = {
        "received_date": "2026-11-05",
        "source": "User-provided engineer screenshot; capture date unknown",
        "original": original.relative_to(root).as_posix(),
        "original_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "redaction": "Customer number rectangle [55,419,650,486]",
        "crop": [590, 1100, 820, 1515],
        "crop_scale": 3,
        "files": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.glob("*.png"))
        },
    }
    (output / "image-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
