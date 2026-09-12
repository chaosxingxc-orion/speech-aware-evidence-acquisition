# STATUS-052: native comparison ready with resident decoder

Date: September 12, 2026 UTC. The broad system goal remains active.

All three complete fake wire checks passed: 4,000 direct requests, 8,000
stage-control requests and 8,000 knowledge requests, with zero real model
contacts. Knowledge supplies exactly 32,000 typed blocks, eight per sample.
Every arm verifies all 4,000 complete speech packets. The direct/control/knowledge
wire receipt hashes are bb61cfb0432d7e8e0c932ea279c260d91fff480a795dd095e5db669b17706bd7,
2104427d25c0b1ef647077dd32cb17527eec1c3f959bdd721f4aaa88b50107f5,
and c11f44a4de928a5fd87b9d83a478e4b0164b09ce6b93d5262f375d0dafe7edcd.

Final campaign-stage recall is sealed at DATA
prepared/SAEA-A2T-NATIVE-SYSTEM-KNOWLEDGE-CAMPAIGN-PREPARE-V1/recall.json,
SHA da05deb0fd8db99d7e60a399b22a8924df1a796b83686291088616af3f202abe.
Its complete output and all source bindings exactly equal the first preparation.
The first refresh was correctly refused because the copied baseline still pinned
the old artifact. No model, tokenizer, encoder or GPU contact occurred. Preserve
DATA coordination/a2t-native-system-final-recall-stale-pin-refusal-v1.json;
removing that stale optional pin allowed the ordinary shared preparation to seal.

Root wire qualification: DATA coordination/a2t-native-system-root-wire-verdict-v1.json,
SHA 9de327b187e8d3571fa1b69e9078aecaadddc7b57a4edd2cc46081a2624da39a.
Scientific execution eligibility: DATA coordination/a2t-native-system-root-eligibility-v1.json,
SHA cc32e69f7dfda6bfe07897f3ce59ce3745a069c8029313b189c6d4b957bae080.
This is permission to execute the bounded comparison, not a quality verdict.

The root-owned serving-a2t-native-system-np3-v1 started at 04:57:04 UTC:
decoder only, no mmproj, c98304/np3 and 32768 tokens per slot. Allocation
succeeded on the 24 GB GPU. Sampled memory is 22,962 MiB. Startup overlapped
the last CPU fake wire; early samples show zero generation utilization.
The source is the clean assembly checkout at7539aab510473b2e1dd1df02a9af3185c084478b.
Keep its foreground owner and ten-second monitor running. Never use an old PID
without revalidation. Service operations registration SHA
afeb72b2b02f3b6cf433d2bd8b2b0a5fce403f0e4458a0d8aee4253c85fb133b.

Final execution configurations are in the isolated
/home/chao/saea-worktrees/a2t-native-campaign-v1 checkout. All three cells are
ready, with source, preparation, wire and decision requirements. The six final
generation/fit plans are in docs/readiness/2026-09-12-a2t-native-system-v1/.
Each has a unique unconsumed exposure row. The campaign plan is
configs/campaign/a2t-native-system-v1.json. No worker may start a substitute
service. Current preparation source hashes exclude only documented operational
receipt/readiness fields; preserve all other configuration bytes.

Next, launch the existing shared campaign entry from a clean frozen checkout.
It fits complete actual requests at every whole-roster phase boundary, generates
direct then stage-control then knowledge through one exclusive lease at a time,
and overlaps full-manifest official scoring after each seal. Preserve max1024,
all speech chunks and the physical8192-token reserve. Keep all three semantic
task-result reads closed until all three seal or a root terminal hold closes
the comparison. The existing family ceilings are21,000 generation contacts,
60,005 fit endpoints,125,000 speech seconds and10 utilization-integral GPU hours
inclusive of loading/fitting. No outcome exists yet at this registration point.

Use OpenJiuwen's supported configure_log_config API to keep INFO logs in
DATA serving/serving-a2t-native-system-np3-v1/campaign-framework-logs with
output/interface_output/performance_output all set to [file]. Repository
MODEL_REQUEST/MODEL_RESPONSE/OBS/ORG/SUPPLY/USE/COST audit traces are independent
and remain enabled. The CLI already forwards runtime/lock paths correctly;
the earlier suspected missing forwarding was a truncated-read error.

The next owner status report should distinguish the retained positive SLURP
compact-frame baseline from the closed negative role-coverage package. E21's
fresh two-stage system improves native WER/PERSON but retains its failed old
insertion guard. E22's tail-silence test is complete and closed, with its protocol
qualification; no new test read is authorized by this Audio2Tool campaign.
Native datasets do not define meeting-summary evaluation. Validated corrective
memory and system-level training-free policy updates remain future work, not
already established gains.
