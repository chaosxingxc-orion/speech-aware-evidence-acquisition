# STATUS-057: Sole matched Audio2Tool recovery launched

Snapshot source closes at root's 2026-09-12T14:25:36+00:00 process check. This
status records operational identity and accounting only. It contains no
task-result, score, prediction, or quality read.

## Interrupted campaign closure

The original campaign remains preserved. DIRECT is FINALIZED with 4,000
generation contacts, STAGE-CONTROL is FINALIZED with 8,000, and KNOWLEDGE is
ABORTED with 3,864 of its 8,000 target contacts. The old campaign spent 15,864
known generation contacts and 48,004 known actual-fit contacts. Root closed the
orphaned lease without modifying the two finalized attempts and recorded zero
quality reads. The closure receipt is DATA
`coordination/a2t-native-system-interruption-closure-result-v1.json`, SHA-256
`c3c33f86073bb039ada533468633ac3fc7b41d4ac155ce53d9e4badeb89612ea`.

External power is restored and the current GPU power limit is 100 W. This
removes the earlier battery/60 W operating condition; it does not establish
generation completion, throughput, fit, or task quality.

## Registered recovery and live ownership

The sole manual full matched recovery is frozen at
`22b56d706e2f5601dc79f58a8fad2bb6a9629f51`. It uses the same exposed 4,000-row
roster, unchanged direct/stage-control/knowledge task programs, decoder-only
c98304/np3/max1024 geometry, complete packet/vector sources, and whole-roster
phase barriers. The new resident is
`serving-a2t-native-system-recovery-np3-v1` on port 8090.

Root launched the shared campaign CLI with campaign PID 2179 in root exec
session 22617. The resident server PID is 620 in root exec session 51845, and
the ten-second monitor PID is 678 in root exec session 78284. Preserve these
owners and verify current process identity from their receipts before any
operational action. No worker may start, stop, replace, or replay them.

The registration summary records all three final config/protocol identities,
the fresh knowledge recall, root wire eligibility, and six exposure rows. Its
receipt is DATA
`coordination/a2t-native-system-recovery-registration-summary-v1.json`, SHA-256
`7eef2e239f56a675e693fdd862aae4561cd45b8adabb79165baca17b15bc9f59`.
The launch receipt is DATA
`coordination/a2t-native-system-recovery-campaign-launch-v1.json`, SHA-256
`1a61446caf8dccb80d791ac6b04962ac9fe93cf5b5b73b8f9168d0c826e23ebc`.

All three shared model-free preflights passed at frozen source `22b56d70`, each
over the complete 4,000-row roster with readiness `ready`. Their CLI JSON logs
are under DATA
`prepared/SAEA-A2T-NATIVE-SYSTEM-RECOVERY-PREFLIGHT-V1/{direct,stage-control,knowledge}.log`.
The `check` mode writes JSON to its log and ignores `--output`; no corresponding
`.json` files are expected.

At 14:25:36 UTC the campaign was still materializing and validating source
packets before lease acquisition or actual real-phase fit. Fit contacts and
generation contacts were both zero for the recovery. The monitor showed zero
GPU utilization with zero of three slots active. Do not label the GPU busy.
Campaign launch and model-free preflight success do not prove that a fit or
generation phase completed. Another failure stops this recovery; no second
recovery registration or automatic restart is available.

The cumulative family ceilings preserve all known old work and add the fresh
pass ceilings: 36,864 generation contacts, 108,009 fit contacts,
217,897.6323333201 speech-audio seconds, and 12.2345 GPU hours. The old GPU
portion is conservatively bounded through the original stopped receipt rather
than reset. The accounting receipt is DATA
`coordination/a2t-native-system-recovery-cumulative-budget-v1.json`, SHA-256
`f407f15c636a8eca25b229b27ee8b9268e51c6e4d5816b8c55f57533f07a294b`.
Paid API spend remains zero.

## Read gate and next actions

Keep semantic task results and quality scores closed until DIRECT,
STAGE-CONTROL, and KNOWLEDGE in the recovery each have a complete sealed
manifest, or root records an explicit terminal hold. Do not infer recovery
success from live processes, fit progress, utilization, or contact counts.

After root confirms all three seals, register the saved-score read and use the
already frozen analysis recipe. Do not rerun the official scorer. Preserve the
old finalized/aborted attempts beside the recovery and report cumulative
accounting.

Local speech-tool acquisition and offline load validation from STATUS-056 remain
valid; root independently reverified all eight dependency-receipt hashes. They
do not authorize new ASR inference, auxiliary neural forwards, dataset audio
processing, a new experiment, or a second GPU service. The future speech-tool
system plan now points to this recovery as the active experiment; its subsequent
SLURP OBS work remains future, separately registered work.
