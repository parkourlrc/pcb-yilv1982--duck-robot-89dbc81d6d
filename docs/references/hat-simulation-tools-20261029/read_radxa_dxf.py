"""Minimal DXF reader for the Radxa Zero 3W 2D drawing (POLYLINE/VERTEX aware).

Prints board outline candidates (closed polylines with their extents), circles
grouped by radius (header pads, mounting holes, vias) and text labels.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path

PATH = Path(sys.argv[1])


def pairs(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out = []
    for i in range(0, len(lines) - 1, 2):
        try:
            code = int(lines[i].strip())
        except ValueError:
            continue
        out.append((code, lines[i + 1].strip()))
    return out


def parse(ps):
    polys, circles, texts = [], [], []
    cur = None
    poly = None
    for code, value in ps:
        if code == 0:
            if poly is not None:
                polys.append(poly)
                poly = None
            if value == "POLYLINE":
                poly = {"flags": 0, "verts": []}
                cur = poly
            elif value == "VERTEX" and poly is not None:
                poly["verts"].append([None, None])
                cur = None
            elif value == "CIRCLE":
                circles.append({})
                cur = circles[-1]
            elif value == "TEXT":
                texts.append({})
                cur = texts[-1]
            else:
                cur = None
            continue
        if cur is None:
            continue
        if isinstance(cur, dict) and "verts" in cur and cur["verts"] and code in (10, 20):
            cur["verts"][-1][0 if code == 10 else 1] = float(value)
        elif isinstance(cur, dict) and "verts" in cur and code == 70:
            cur["flags"] = int(float(value))
        elif code == 10:
            cur["x"] = float(value)
        elif code == 20:
            cur["y"] = float(value)
        elif code == 40:
            cur["r"] = float(value)
        elif code == 1:
            cur["text"] = value
    if poly is not None:
        polys.append(poly)
    return polys, circles, texts


def main():
    ps = pairs(PATH)
    polys, circles, texts = parse(ps)
    print(f"polylines {len(polys)}, circles {len(circles)}, texts {len(texts)}")

    closed = []
    for p in polys:
        v = [pt for pt in p["verts"] if None not in pt]
        if len(v) < 3:
            continue
        xs = [pt[0] for pt in v]
        ys = [pt[1] for pt in v]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        closed.append((w * h, len(v), min(xs), max(xs), min(ys), max(ys), p["flags"]))
    closed.sort(reverse=True)
    print("largest closed/outline candidates (area, nverts, x1..x2, y1..y2, flags):")
    for c in closed[:6]:
        print(f"   {c[0]:9.1f}  n={c[1]:4d}  x {c[2]:7.2f}..{c[3]:7.2f}  y {c[4]:7.2f}..{c[5]:7.2f}  flags={c[6]}")

    groups = defaultdict(list)
    for c in circles:
        if "r" in c and "x" in c:
            groups[round(c["r"], 2)].append((c["x"], c["y"]))
    print("circle radius groups:")
    for r in sorted(groups, key=lambda v: -len(groups[v])):
        pts = groups[r]
        print(f"   r={r:5.2f} n={len(pts):4d} sample={[(round(a,2), round(b,2)) for a, b in pts[:5]]}")

    if texts:
        print("texts:", [t.get("text") for t in texts][:12])


if __name__ == "__main__":
    main()
