"""Build a JLC-style BOM CSV from the exported KiCad netlist.

Grouping is by (value, footprint); the LCSC column is left blank on purpose -
part numbers must be chosen and checked against stock before ordering.
"""
import csv
import re
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
NETLIST = BASE / "rev_a" / "custom_hat_rev_a.net"
OUT = BASE / "rev_a" / "production" / "custom_hat_rev_a-bom.csv"


def main():
    text = NETLIST.read_text(encoding="utf-8")
    rows = []
    for block in re.split(r"\(comp\s*\n", text)[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', block)
        val = re.search(r'\(value "([^"]*)"\)', block)
        fp = re.search(r'\(footprint "([^"]*)"\)', block)
        if not ref:
            continue
        if ref.group(1).startswith("FLG") or not (fp.group(1) if fp else ""):
            # PWR_FLAG and other virtual symbols are not BOM items
            continue
        value = val.group(1) if val else ""
        if "reserve" in value.lower() or "dnp" in value.lower():
            # do-not-populate parts stay off the order BOM
            continue
        rows.append((ref.group(1), value, fp.group(1) if fp else ""))

    groups = defaultdict(list)
    for ref, val, fp in rows:
        groups[(val, fp)].append(ref)

    def sort_key(refs):
        first = refs[0]
        m = re.match(r"([A-Za-z]+)(\d+)", first)
        return (m.group(1), int(m.group(2))) if m else (first, 0)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Comment", "Designator", "Footprint", "Quantity", "LCSC"])
        for (val, fp), refs in sorted(groups.items(), key=lambda kv: sort_key(kv[1])):
            refs = sorted(refs, key=lambda r: (re.match(r"[A-Za-z]+", r).group(0), int(re.search(r"\d+", r).group(0))))
            writer.writerow([val, ",".join(refs), fp, len(refs), ""])

    print(f"wrote {OUT} with {len(groups)} line items covering {len(rows)} components")


if __name__ == "__main__":
    main()
