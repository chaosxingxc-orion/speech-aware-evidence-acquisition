# What this verdict cites from the KU-E1c flight receipt, and where the bytes came from

The KU-E1c closure landed on `master` as commit **`df040750`**
("close: KU-E1c flew all 1,593 windows at exactly seven tokens more than the arm"), which the branch
this verdict was written on does not yet contain. Every byte quoted from that receipt was therefore
taken from the **git blob at `df040750`**, not from a working tree — git blob bytes are this
program's evidence-hash authority — and the two files small enough to carry are copied here verbatim.
Both copies re-hash to their blob.

| what | source path at `df040750` | sha256 | bytes | here |
|---|---|---|---|---|
| flight README | `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-kc-e1-brief-44-v1/flight-placebo/README.md` | `8489c89fa63a17d65d9eb2895e0638db6385129d6f2aba3efecddb493c8ca32f` | 10,055 | `ku-e1c-flight-README.md` |
| scoring batch record | `…/flight-placebo/batch-summary.json` | `5de80feecd1d54a8f9249a880d73062c439ede86f83f2f6ccee83b3d6d61f422` | 1,164 | `ku-e1c-flight-batch-summary.json` |
| the one scoring job | `…/flight-placebo/jobs.jsonl` | `caf447f32ce5b183627e0c4822fc8a994e5c77f76d659a33b947e1c49abb6603` | 205 | `ku-e1c-flight-jobs.jsonl` |
| flight receipt | `…/flight-placebo/flight-receipt.json` | `11f1be7afe52607ff7b3eb822f593fc908898bd099481d3873973e1ae2d9e842` | 742,449 | **hashed, not copied** |
| verified score read | `…/flight-placebo/score-read.json` | `0d83b08c4675658d38bd43ff29226930ec165948e30a98fc9215e29e6d09cc0f` | 1,131,617 | **hashed, not copied** |

The last two are not copied on purpose: they are megabyte-scale receipts that already live in this
repository's own history at `df040750`, and duplicating them here would put two copies of the same
sealed bytes under two `MANIFEST.sha256` files. They are addressable by the hashes above and by that
commit, which is what an audit needs. `token-throughput-covariate.json` in the parent directory
records the same `flight-receipt.json` SHA-256 as the source of every twin-side token count it
carries, computed on the file the runner actually read.

**The treatment side needs no copy.** `SAEA-E21-KC-E1-BRIEF-44-V1`'s flight receipt is already in this
branch at `docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-kc-e1-brief-44-v1/flight/`,
under that directory's own `MANIFEST.sha256`.

Nothing in the main checkout was modified to produce any of this; the copies were made with
`git show df040750:<path>` from a worktree that shares the object database.
