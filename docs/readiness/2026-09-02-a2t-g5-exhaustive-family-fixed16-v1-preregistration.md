# Audio2Tool G5 exhaustive-family fixed16 v1 preregistration

Date: 2026-09-02. Status: **MODEL CONTACT CLOSED**. Experiment:
`SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1`. Execution profile:
`bounded-discovery-probe`. This is a prospective, bounded discovery ground screen, not
confirmation, scale, candidate pruning, training-free control, test evaluation, or paper work.

## Frozen population and evidence

The identity-only receipt is
`docs/receipts/a2t/A2T-G5-FIXED16-IDENTITY.json`, SHA-256
`81e3703f0529882c943f71dbe213e1c2d9bcd4e9b00fabf51e5499bae3501ffe`.
Its ordered partition hash is
`c1c38f4ac670846df8c2a488aa62642bb6d14733aa8cc4fa33955f5c2bf76550` and its
carrier-prefixed run identity is
`8c0136a901693548a737bf4bf3fa83206d9bae190283123d6412be6a78b069fe`.
Runtime verification, the future ExecutionPlan, bundle verification, and protocol hashing use
the run identity; the partition hash remains receipt-integrity evidence.

There are exactly two identity-selected rows in each of eight tiers, sixteen rows total. G3,
all G4 rows including remainder24, fresh88, test, future turns, TFRL evaluation surfaces, and
the unexposed population are excluded. The roster was selected without audio, task text, gold,
outputs, scores, rewards, tokenizer, scorer, network, or model contact.

The frozen construction-only family corpus is
`knowledge/audio2tool/g5-exhaustive-family-contracts-v1/corpus.json`, SHA-256
`92684a16e39985d3c4c6e7e6d62ac54feaa357eaa7c24c744df21950e51f95e`. Its build
receipt SHA-256 is
`768533a759c742ccc2bd827164c18d77cf5079558169d5104f6760cacecb81c5`; it proves
152 contracts across 28 families, a maximum full compatible bundle of 12,057 ASCII bytes, and
the fixed 18,432-byte bundle ceiling. The builder SHA-256 is
`08a836c79de3dfc821ee4ce8c29381e5f99d22a3a04fa0d5186fe732cde5e737`; the G5
AgentLoop boundary SHA-256 is
`df4f40b6b4269b8dc453ef8579ca9ed8b643b020dc5b7852a750488a4639491c`. The design
authority SHA-256 is
`28eacf0a4553c29a000e8c98340a5e2485a06c0f17fff6a74a6729fdafbbf576`.

## Frozen protocol

The same frozen core makes exactly 32 contacts: PLAN16 followed sequentially by EXECUTE16.
PLAN is non-final and returns only strict English JSON over the closed family taxonomy; it has a
256-token completion cap. Deterministic, contact-free COMPILE validates the PLAN and supplies the
complete, unranked compatible family bundle. EXECUTE is the sole final answer and has a
1,024-token completion cap. Temperature is zero, with two slots, at most two concurrent requests,
and queue depth four.

The PLAN state is capped at 4,096 ASCII bytes. Every full bundle must be at most 18,432 ASCII
bytes; it may not be ranked, pruned, partially trimmed, or changed adaptively. PLAN text is capped
at 6,000 tokens and EXECUTE text at 12,000 tokens before measured speech and special-token
reserves. Every per-slot total must fit within 32,768 tokens. There is no repair, retry, resend,
jitter experiment, cumulative history, or response-format dependency.

## Gate and stop rule

P16 passes only with parse at least 15/16, exact at least 15/16, correct tool 16/16, slot micro-F1
at least 0.90, and at least one exact row in every tier. It additionally requires zero
out-of-registry names, illegal argument-key sets, synthetic literal copies, and parser repairs.
Structural checks do not substitute for the official exact gate. Both complete contact manifests
must seal before gold or the unchanged whole-manifest official scorer opens; no dataset sharding or
shard-score averaging is permitted.

If any gate fails, no scale, pruning, TFRL, G3/G4/remainder contact, fresh88, or test opens. A pass
only permits a separately preregistered, identity-selected, disjoint 40-row discovery proposal,
which must independently meet parse 39/40, exact 36/40, correct tool 38/40, slot micro-F1 0.90,
and four exact rows in each tier.

## Current closure and provisional identity

The baseline and experiment fragments are registered at
`configs/baseline/a2t-g5-exhaustive-family-agentloop.json` and
`configs/experiment/a2t-g5-exhaustive-family-fixed16-v1.json`. The required runtime fragment is
`q4km-mmproj-free-speech-native-np2-a2t-max1024`: the established two-slot Audio2Tool profile with
a 32,768-token per-slot context and a 1,024-token final completion cap. The prior provisional
`q4km-mmproj-free-speech-native-np16` composition is non-launchable and remains audit history
only; it cannot be used for G5 contact.

The corrected provisional composition uses `q4km-mmproj-free-speech-native-np2-a2t-max1024`, the
`audio2tool-g1-104` dataset fragment solely for composition, this baseline, this experiment, and
the G5 run identity above. It does not authorize contact and will be prospectively superseded by
one final hash amendment when the dedicated G5 integration, exact prompt-fit receipt, runtime
binding, ExecutionPlan, and launcher hashes land.

The current baseline, experiment, provisional composed-config, and provisional protocol SHA-256
values are `bda861b2d110b2b98b9a0cc8ffa3311cef21d2325091ff2be42417a3a8152e92`,
`fb69d031fc291e9fdc228430acfda95d9f743059795059593205891e57afe0c4`,
`797bf47bcb7fb7c94c46a79cc62e9cd1963414d48c3aa3f8912020f450607f09`, and
`e669d545e7ffb7ed09e9a827e99951807699c9fc49796d5942a0b31f6716f9fd`, respectively. The
superseded non-launchable np16 experiment, composed-config, and protocol identities are
`da536090f85a6131f9e7da061d4bbcbcbc32230ee462906ded1238a3307f7bf9d`,
`0c6cf271d79a79190226bc046c40105f04927b35f8a7ceb7a10d2cf8473ce941`, and
`fa7ea93447b6965fcd0758a0ee8c5ee3e28aecd6786fe8d8fe9d543699612e42`.

## Final prospective activation amendment

Before any G5 contact, the dedicated launcher landed at commit
`b8b01ecf9d57452db8cfd11da116b6cee6fa8be4`, SHA-256
`68f3179d791998b9018ae2d49a7f84e7eeedd5a053d6054f816343ae00427194`.
It binds the corrected np2 experiment, composed-config, and protocol identities above and checks
the corpus, roster, promotion receipt, runtime packet surface, integration, prompt-fit receipt,
and all model-facing request identities before service start.

The zero-contact integration module and prompt-fit receipt are SHA-256
`dc6ad763473d7f7854f900330cacf5194a5ccc5beab9955ce0ee97b613541c5d` and
`75b1a9bfbff4373d4cc35d7ce472ae888567a03863a2a9d226c141eb4289c869`.
The prompt-fit receipt passes without tokenizer contact: PLAN requires at most 2,871 and EXECUTE
at most 26,219 of 32,768 per-slot tokens, including the fixed 512 special-token reserve, measured
speech reserve, and the respective 256 and 1,024 completion reserves. The receipt-pinned runtime
receipt is `docs/receipts/runtime-q4km-mmproj-free.json`, SHA-256
`b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77`.

The launcher constructs and validates exactly one `saea-execution-plan-v1` plan for this attempt:
run `SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1`, bounded-discovery-probe, Audio2Tool discovery,
run identity `8c0136a901693548a737bf4bf3fa83206d9bae190283123d6412be6a78b069fe`, 32 model calls,
247 registered speech-audio seconds, 0.3 GPU-hours, and protocol
`e669d545e7ffb7ed09e9a827e99951807699c9fc49796d5942a0b31f6716f9fd`. It permits exactly
PLAN then EXECUTE for each fixed16 row, with no scoring or response-meaning inspection during the
flight. The 37 combined G5 tests and Ruff check pass at the launcher commit.

This final prospective amendment opens only that fixed16 launcher attempt after its own clean-tree
preflight. It opens neither another roster nor a scorer read: gold and unchanged whole-manifest
official scoring remain closed until all sixteen final responses and both contact manifests seal.
Every population, protocol, packet bound, temperature, contact count, gate, exclusion, stop rule,
and terminal consequence above remains unchanged.
