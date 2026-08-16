import re
import sys
from pathlib import Path

REPO = Path(r"D:\chao_workspace\exploring-l4-intelligence")
HAN = re.compile("[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef]")

for rel in sys.argv[1:]:
    p = REPO / rel
    text = p.read_text(encoding="utf-8")
    print(f"########## {rel}")
    for i, line in enumerate(text.splitlines(), 1):
        if HAN.search(line):
            s = line.strip()
            print(f"  {i}: {s[:220]}")
    print()
