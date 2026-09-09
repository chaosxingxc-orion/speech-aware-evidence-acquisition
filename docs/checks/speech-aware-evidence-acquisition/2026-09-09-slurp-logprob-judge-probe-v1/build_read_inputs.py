"""The two derived inputs the registered read declares, and their provenance.

Zero model contacts, zero GPU. Preregistration section 6: the read's five
inputs are files, so the read carries no dataset access of its own; the FLIGHT
read produces the last two and records their provenance and sha256.

``clusters.json``          ``{sample_id: speaker_id}``, resolved through
                           ``data.slurp``'s OWN speaker index over the governed
                           release's ``metadata.json`` (``recordings[...]
                           ["usrid"]``). A sample id whose speaker cannot be
                           resolved is REPORTED and left out, so the read fails
                           closed on it rather than inventing a singleton
                           cluster.
``label-inventory.json``   ``{entity_types, legal_pairs}`` mined from TRAIN
                           ALONE, through ``reproduction.slurp_official_eval.
                           load_legal_intent_inventory`` and ``data.slurp.
                           load_slurp_ontology`` -- the same TRAIN-only
                           inventory the locked closed-list baseline's own
                           prompt suffix renders. No devel or test label
                           reaches either file.
"""

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(
    "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import (  # noqa: E402
    _governed_roots,
    _slurp_speaker_index,
    load_slurp_ontology,
)
from speech_aware_evidence_acquisition.reproduction.slurp_official_eval import (  # noqa: E402
    load_legal_intent_inventory,
)

OUT = Path(sys.argv[1])
OUTPUTS = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

lock = load_lock(umbrella_lock_path())
root = data_root()

# -- the roster, from the arm's OWN sealed outputs -------------------------
sample_ids = []
for line in OUTPUTS.read_text(encoding="utf-8").split("\n"):
    if not line.strip():
        continue
    sample_ids.append(str(json.loads(line)["sample_id"]))
print("sealed rows:", len(sample_ids))

# -- clusters ---------------------------------------------------------------
_, _, metadata_dir = _governed_roots(lock, root)
speaker_index = _slurp_speaker_index(metadata_dir)
metadata_path = metadata_dir / "metadata.json"

clusters = {}
unresolved = []
for sample_id in sample_ids:
    parts = sample_id.split(":")
    if len(parts) != 4:
        unresolved.append(sample_id)
        continue
    filename = parts[3] + ".flac"
    speaker = speaker_index.get(filename)
    if speaker is None:
        unresolved.append(sample_id)
        continue
    clusters[sample_id] = speaker

print("clusters resolved:", len(clusters), "distinct speakers:", len(set(clusters.values())))
if unresolved:
    print("UNRESOLVED (the read will fail closed on these):", unresolved[:5], len(unresolved))

# -- label inventory --------------------------------------------------------
ontology = load_slurp_ontology(lock, root)
inventory = load_legal_intent_inventory(lock, root)
entity_types = sorted(ontology.entity_types)
legal_pairs = sorted([list(pair) for pair in inventory.pairs])
print("entity types:", len(entity_types), "legal pairs:", len(legal_pairs))

clusters_path = OUT / "clusters.json"
inventory_path = OUT / "label-inventory.json"
clusters_path.write_text(
    json.dumps(clusters, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
)
inventory_path.write_text(
    json.dumps(
        {"entity_types": entity_types, "legal_pairs": legal_pairs},
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
    newline="\n",
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


provenance = {
    "schema": "saea-slurp-logprob-read-inputs-v1",
    "model_contacts": 0,
    "clusters": {
        "path": str(clusters_path),
        "sha256": sha256(clusters_path),
        "rows": len(clusters),
        "distinct_speakers": len(set(clusters.values())),
        "unresolved": unresolved,
        "source": str(metadata_path),
        "source_sha256": sha256(metadata_path),
        "reader": "data.slurp._slurp_speaker_index (recordings[...]['usrid'])",
        "join": (
            "sample id 'slurp:<split>:<utt>:<stem>' -> '<stem>.flac', the filename "
            "data.slurp.load_slurp_split itself keys the speaker index by"
        ),
    },
    "label_inventory": {
        "path": str(inventory_path),
        "sha256": sha256(inventory_path),
        "entity_types": len(entity_types),
        "legal_pairs": len(legal_pairs),
        "reader": (
            "data.slurp.load_slurp_ontology(include_synthetic=False).entity_types and "
            "reproduction.slurp_official_eval.load_legal_intent_inventory(...).pairs"
        ),
        "provenance": "TRAIN alone; no devel or test label reaches either half",
    },
    "roster": {
        "path": str(OUTPUTS),
        "sha256": sha256(OUTPUTS),
        "rows": len(sample_ids),
    },
}
(OUT / "read-inputs-provenance.json").write_text(
    json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
)
print(json.dumps({k: v for k, v in provenance.items() if k != "clusters"}, indent=2)[:1200])
print("clusters sha256:", provenance["clusters"]["sha256"])
