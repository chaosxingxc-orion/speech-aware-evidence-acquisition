# Corrective memory source verification v2

Status: accepted shared implementation. This successor preserves the version 1 runtime note and adds mandatory source membership for every live corrective-memory binding. It establishes TRAIN provenance, not scientific quality or task benefit.

## Authority boundary

A corrective-memory record contains one primary `ExperienceSource` and supporting or contradicting `SourceRef` values. Their hashes are archive pointers; syntactic hashes and a self-hashed memory manifest do not prove that the referenced events came from an authorized TRAIN run.

Source verification therefore occurs offline. `rails.experience_memory_sources.verify_experience_memory_sources` calls `reward_link_io.read_verified_reward_link_artifact` for every declared reward source. That shared reader rebuilds each RewardLink from its pinned completed bundle, complete score receipt, construction roster, trace, responses, and native sufficient statistics. The verifier then requires:

- every RewardLink to carry the memory catalog's exact construction-roster SHA-256;
- every source sample to be in the catalog's expected TRAIN membership;
- every record's primary `ExperienceSource` to equal one verified RewardLink source in every field;
- every secondary reference to use `SourceRef("reward-link:<LINK_SHA256>", "<LINK_SHA256>", "train")` exactly and resolve to a verified link;
- reward-link hashes and primary source identities to be unambiguous across all bound artifacts; and
- the persisted record order, primary correspondence, supporting links, and contradicting links to equal the memory manifest exactly.

Supporting and contradicting labels remain an offline scientific judgment. Membership proves where a source came from; it does not prove that the source supports a rule, that the rule is useful, or that task quality improves.

## Shared preparation API

Use these shared functions; do not create another writer or runtime reward reader:

```python
from speech_aware_evidence_acquisition.rails.experience_memory_sources import (
    prepare_experience_memory_sources,
    reward_link_source_ref,
    verify_experience_memory_sources,
)

reference = reward_link_source_ref(verified_link)
proof = verify_experience_memory_sources(catalog, reward_source_bindings)
receipt_pin = prepare_experience_memory_sources(
    catalog,
    reward_source_bindings,
    output_path,
)
```

Each `reward_source_bindings` entry contains the exact RewardLink artifact pin and the existing `saea-reward-link-artifact-config-v1` configuration used by the authoritative reader. `prepare_experience_memory_sources` persists the compact proof through `core.preparation.prepare_artifact` with kind `experience-memory-sources` and contact class `model-free`. It never writes reward vectors, answer text, trace payloads, gold labels, or references. The proof retains only source identifiers, hashes, construction identity, verifier identity, and per-record correspondence.

The offline verifier hashes the RewardLink artifact before the authoritative read and then requires the same SHA-256 and unchanged inode, size, and modification-time fingerprint afterward. A valid but different file encoding substituted during verification is rejected.

## Required live configuration

Every live `experience_memory` declaration now has seven exact fields. `source_verification` is mandatory:

```json
{
  "experience_memory": {
    "manifest": {
      "relpath": "<DATA_RELATIVE_MEMORY_MANIFEST>",
      "sha256": "<MEMORY_MANIFEST_SHA256>"
    },
    "construction_roster": {
      "repo_relpath": "<REPOSITORY_RELATIVE_TRAIN_ROSTER>",
      "sha256": "<TRAIN_ROSTER_SHA256>"
    },
    "admission": {
      "relpath": "<DATA_RELATIVE_ADMISSION_V2>",
      "sha256": "<ADMISSION_V2_SHA256>"
    },
    "source_verification": {
      "relpath": "<DATA_RELATIVE_SOURCE_VERIFICATION>",
      "sha256": "<SOURCE_VERIFICATION_RECEIPT_SHA256>"
    },
    "task_id": "<RUNTIME_TASK_FAMILY>",
    "component_tags": ["supply", "use"],
    "max_records": 1
  }
}
```

The independently root-frozen admission is the trust anchor and must use this exact schema and fields:

```json
{
  "schema": "saea-experience-memory-admission-v2",
  "status": "admitted",
  "manifest_sha256": "<MEMORY_MANIFEST_SHA256>",
  "construction_roster_sha256": "<TRAIN_ROSTER_SHA256>",
  "admitted_record_sha256s": ["<EXACT_RECORD_SHA256>"],
  "source_verification_sha256": "<SOURCE_VERIFICATION_RECEIPT_SHA256>"
}
```

The configuration pins the receipt independently, and admission v2 must name the same receipt SHA-256. Admission v1 is not live authority and is rejected. Generic `SourceRef`, `ExperienceRecord`, and memory-manifest parsing remain available for offline archives; they do not bypass the live admission-v2 gate.

## Runtime behavior

`rails.experience_memory_runtime.load_experience_memory_binding` loads the pinned memory manifest, TRAIN roster, admission v2, and compact source-verification receipt before any model contact. `load_verified_memory_sources` validates the preparation wrapper, memory and construction identities, exact record correspondence, and the admission-bound receipt hash.

The answering runtime never imports or calls the RewardLink reader, bundle verifier, scorer, or archived score and trace sources. It does not reopen the RewardLink artifact. The selected guidance retains the source-verification receipt SHA-256 in internal lineage; model-visible guidance remains compact and contains no TRAIN sample identifier or archived answer.

Quality authority remains separate. Existing record validation and root admission decide whether guidance is admitted for a task. The source receipt attests only that its primary, supporting, and contradicting provenance corresponds to verified TRAIN RewardLinks.

## Verification

The accepted validation covers exact primary-source matching, canonical supporting and contradicting references, wrong construction membership, duplicate and ambiguous reward sources, artifact tampering, replacement during the check/use seam, receipt-to-record correspondence, admission pinning, legacy-v1 refusal, runtime loading without archived sources, and shared FlightRuntime/OpenJiuwen propagation.

The final review passed 134 related tests. Branch-inclusive coverage was 81 percent for `experience_memory_sources.py` and 84 percent for `experience_memory_runtime.py`. Ruff, the engineering-base check, and the whitespace/diff check passed. The immutable validation receipt is:

- `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/memory-source-verification-validation-v1.json`
- SHA-256 `eb5159058f18d7905f70dea7ae6e64bd288f4e1cae044af4c4ac86fd97e7351a`
