# SLURP semantic store release bindings

Status: held. This record prepares the shared release bindings and authorizes no preparation run, runtime configuration, model contact, tokenizer contact, tool contact, scorer contact, or GPU contact.

The reviewed intent source has a complete, executable shared preparation registration in `2026-09-13-slurp-intent-boundaries-preparation-registration-v1.json`. It pins the root-reviewed source in `SPEECHRL_DATA_DIR`, the outer construction roster that defines the source-pool identity, the smaller exact intent-support roster, and the existing repository-held Fold A, Fold B, and DEV-1000 exclusions. The output namespace is create-only and is absent at the time of this record.

The two roster identities have different purposes. The authored source is bound to the outer construction roster identity `f244b9760e9c9c21e04dcf335becb30cea95e66b7f66a8f60147bb94e5d83549`; the exact support roster is a verified subset used to constrain source provenance. The shared preparer now validates both relationships independently. It does not substitute the support identity for the source-pool identity.

The slot binding is held in `2026-09-13-slurp-slot-contracts-preparation-held-v1.json`. Its outer scope, support roster, exclusions, builder, store identity, and output namespace are pinned, but the final root-authored slot source and SHA-256 are unavailable. It is intentionally not a `saea-authored-semantic-knowledge-preparation-v1` registration and cannot be run.

After root provides the final slot source pin and directs preparation, create an executable slot registration by replacing only the held source with the final data-root pin and using the shared schema. Run each registered store separately through the shared CLI, then derive any runtime `knowledge_stores` fragment only from the generated completion's `snapshot` and `release` pins. Do not invent those pins or add an unpinned runtime configuration.
