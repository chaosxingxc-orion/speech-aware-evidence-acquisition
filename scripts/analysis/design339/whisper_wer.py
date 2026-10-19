#!/usr/bin/env python3
"""Aggregate canonical-token WER of the sealed E5-0 Whisper large-v3 Fold B transcripts against the SLURP TRAIN
reference sentence (scoring side, in memory only). Prints aggregates only."""
import importlib.util, json, sys
from pathlib import Path
REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
sys.path.insert(0, str(REPO / "src")); sys.dont_write_bytecode = True
def imp(p, n):
    s = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(s); sys.modules[n] = m; s.loader.exec_module(m); return m
E5 = imp(REPO / "scripts/analysis/e5_transcript_consistency_read.py", "e5read")
S2 = imp(REPO / "scripts/analysis/slurp_s2a1_recall_ceiling.py", "s2a1")
DATA = Path("/home/chao/saea-data/speechrl-data"); LOCK = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json")
out = {}
sent, _ = S2.load_reference_sentences(LOCK, DATA)
for fold in ("fold-b", "fold-a"):
    tx, facts = E5.load_catalog(DATA, fold)
    err = n = 0; exact = 0
    for s, t in tx.items():
        if ":test:" in s: raise SystemExit("test row")
        ref = E5.canon_tokens(sent[s]); hyp = t["canon"]
        e = E5.token_edit(ref, hyp); err += e; n += len(ref); exact += int(e == 0)
    out[fold] = {"rows": len(tx), "ref_tokens": n, "canon_wer": round(err / n, 4), "sentence_exact_rate": round(exact / len(tx), 4)}
Path(sys.argv[1]).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8"); print(json.dumps(out))
