"""提取六个时刻的回放画面以检查姿态和转向；不以静帧判定有效步数。"""
import argparse
import hashlib
import json
from pathlib import Path

import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont


def main(evidence, font_path):
    font = ImageFont.truetype(str(font_path), 18)
    out = evidence / "comparison"
    index = []
    for video in sorted(evidence.glob("*/diagnostic/straight_0.06_101/replay-50fps.mp4")):
        reader = imageio.get_reader(video)
        canvas = Image.new("RGB", (960, 550), "white")
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 4), video.parents[2].name, font=font, fill="black")
        times = []
        try:
            fps = reader.get_meta_data()["fps"]
            for i, target in enumerate((3, 7, 11, 15, 19, 22)):
                frame_id = round(target * fps) - 1
                try:
                    frame = reader.get_data(frame_id)
                except IndexError:
                    break
                x, y = (i % 3) * 320, (i // 3) * 260 + 30
                canvas.paste(Image.fromarray(frame).resize((320, 240)), (x, y))
                draw.text((x + 5, y + 240), f"第 {target} 秒", font=font, fill="black")
                times.append({"seconds": target, "frame_index": frame_id})
        finally:
            reader.close()
        output = out / (video.parents[2].name + "-frames.png")
        canvas.save(output)
        index.append({"video": video.relative_to(evidence).as_posix(), "sha256": hashlib.sha256(video.read_bytes()).hexdigest(), "frames": times, "output": output.name})
    (out / "video-frames.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"videos": len(index)}, ensure_ascii=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--font", type=Path, required=True)
    args = parser.parse_args()
    main(args.evidence, args.font)
