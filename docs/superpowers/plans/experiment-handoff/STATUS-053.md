# STATUS-053: campaign dispatched and future E21 quality preference recorded

Date: September 12, 2026 UTC. Goal active. Read STATUS-052 for complete
preparation, source and admission identities.

The three-arm native Audio2Tool campaign is dispatched through the shared CLI
from the clean frozen /home/chao/saea-worktrees/a2t-native-campaign-v1 checkout,
commit cbc53ac0c36bed94fdb50c3b069a74569d935720. Root owns the resident decoder
and monitor. Launch receipt: DATA coordination/a2t-native-system-campaign-launch-v1.json,
SHA fd03659a80ea1017748b318c769bf8e227ef5d096d505c43e705f0ca61ddf638.
Runtime log: DATA serving/serving-a2t-native-system-np3-v1/root-campaign.log.

At the last operational inspection the direct arm held the sole generation
lease, acquired at05:12:33UTC by the live campaign process. Its generation
attempt had not opened yet: source/runtime preprocessing was still in progress.
The latest sampled GPU utilization was0percent, memory22962MiB and all three
slots idle. Do not label resident memory as active generation or full GPU load.
No new semantic task results were read. Use fresh monitoring and attempt
metadata for subsequent status; do not reuse this snapshot as a current count.

The completed code/configuration work is fast-forwarded into local master at
cbc53ac0. No remote push or GitHub merge is claimed. The active campaign source
will stay frozen while this separate canonical checkout records owner decisions.

OWNER-E21-QUALITY-PRIORITY-022 applies only to future newly registered E21 work:
prioritize overall WER and PERSON quality; analyze a small insertion increase
without automatic rejection. Preserve the completed system's failed historical
insertion guard. Define numeric rules prospectively before the next E21
experiment; retain native ASR tasks and all diagnostic outcomes.

Next: finish current exact live-request fitting and generation for direct,
stage-control and knowledge, with complete scoring overlapped after each seal.
Inspect native task quality only after all three seal or a terminal root hold.
Do not modify the active campaign, automatically restart it, or add a new
mechanism while this comparison is in flight.
