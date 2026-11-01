"""Patch the Diodes AP64350 PSpice model for ngspice use.

Vendor defect (2021-10-14, Model Version 1.0, file ap64350.lib):
line 118 instantiates subcircuit AP64352_Top_Top_Level_S3, but the file only
defines AP64350_Top_Top_Level_S3 (line 315). ngspice fails with
"unknown subckt ... ap64352_top_top_level_s3". PSpice may resolve it through
the project's .OLB/library set; a plain .include does not.

This script never edits the vendor file. It writes a sibling copy with the
single name corrected and prints the diff so the change can be reviewed.
"""
from pathlib import Path
import os

SRC = Path(os.environ['LOCALAPPDATA']) / 'duck-robot-tools' / 'models' / 'diodes' / 'AP64350' / 'ap64350.lib'
DST = SRC.with_name('ap64350_patched.lib')
BAD = 'AP64352_Top_Top_Level_S3'
GOOD = 'AP64350_Top_Top_Level_S3'

text = SRC.read_text(encoding='latin-1')
count = text.count(BAD)
if count != 1:
    raise SystemExit(f'expected exactly one {BAD} reference, found {count}')
patched = text.replace(BAD, GOOD)
DST.write_text(patched, encoding='latin-1')

for i, (a, b) in enumerate(zip(text.splitlines(), patched.splitlines()), 1):
    if a != b:
        print(f'- {i}: {a.strip()}')
        print(f'+ {i}: {b.strip()}')
print(f'wrote {DST} ({DST.stat().st_size} bytes); vendor file unchanged')
