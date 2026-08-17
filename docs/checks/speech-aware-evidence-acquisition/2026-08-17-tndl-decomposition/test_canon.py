"""Self-test of the T-NDL canonicalizer and of the align_trace mirror."""
import sys
sys.path.insert(0, "/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/agentD")
from tndl_lib import canonical_variants, format_match, align_trace, value_only

POSITIVE = [
    ("2020", "twenty twenty"),
    ("2020", "two thousand twenty"),
    ("2026", "twenty twenty-six"),
    ("1998", "nineteen ninety eight"),
    ("6.8%", "six point eight percent"),
    ("19%", "nineteen percent"),
    ("142.8%", "one hundred forty two point eight percent"),
    ("$58,000", "fifty eight thousand dollars"),
    ("$350,000", "three hundred fifty thousand dollars"),
    ("$6.5", "six point five"),
    ("5.1", "five point one"),
    ("72", "seventy two"),
    ("25 cents", "twenty five cents"),
    ("10-K", "ten K"),
    ("8-K", "eight K"),
    ("3D", "three D"),
    ("18th", "eighteenth"),
    ("4th", "fourth"),
    ("first", "1st"),
    ("third quarter", "3rd quarter"),
    ("the third quarter of fiscal 2020", "the third quarter of fiscal twenty twenty"),
    ("$53.2M", "fifty three point two million dollars"),
    ("53.2 million", "$53.2M"),
    ("2,873", "two thousand eight hundred seventy three"),
    ("$2", "two dollars"),
    ("0.5", "point five" ),
    ("zero cents", "0 cents"),
    ("2021", "twenty twenty one"),
]

NEGATIVE = [
    ("2020", "twenty nineteen"),
    ("6.8%", "six point nine percent"),
    ("$58,000", "fifty eight thousand"),   # currency marker missing -> strict/window differ
    ("72", "seventy three"),
    ("Culp", "Cult"),
    ("first", "second"),
]

print("=== POSITIVE (expect window-tier match) ===")
bad = 0
for ref, hyp in POSITIVE:
    s = format_match(ref, hyp, "strict")
    w = format_match(ref, hyp, "window")
    v = format_match(ref, hyp, "value")
    flag = "" if w else "   <-- MISS"
    if not w:
        bad += 1
    print(f"  strict={int(s)} window={int(w)} value={int(v)}  {ref!r:38} vs {hyp!r}{flag}")

print("\n=== NEGATIVE (expect window-tier NON-match) ===")
for ref, hyp in NEGATIVE:
    s = format_match(ref, hyp, "strict")
    w = format_match(ref, hyp, "window")
    v = format_match(ref, hyp, "value")
    flag = "   <-- FALSE POSITIVE" if w else ""
    print(f"  strict={int(s)} window={int(w)} value={int(v)}  {ref!r:38} vs {hyp!r}{flag}")

print("\n=== canonical_variants spot dump ===")
for t in ["2020", "twenty twenty", "$53.2M", "six point eight percent", "10-K",
          "the third quarter of fiscal 2020", "we'll", "$6.5 million"]:
    vs = sorted(canonical_variants(t))
    print(f"  {t!r:38} -> {vs[:6]}")

print("\n=== align_trace vs frozen align ===")
from speech_aware_evidence_acquisition.scoring.wer import align
import random
random.seed(7)
vocab = ["a", "b", "c", "d", "e"]
fails = 0
for trial in range(300):
    r = [random.choice(vocab) for _ in range(random.randint(0, 12))]
    h = [random.choice(vocab) for _ in range(random.randint(0, 12))]
    _, _, _, mask = align_trace(r, h)
    if mask != align(r, h).ref_hit_mask:
        fails += 1
        if fails < 4:
            print("  MISMATCH", r, h, mask, align(r, h).ref_hit_mask)
print(f"  randomised mirror check: {300 - fails}/300 masks identical to frozen align()")
print(f"\nPOSITIVE misses at window tier: {bad}/{len(POSITIVE)}")

print("\n=== compound ordinals ===")
for ref, hyp, want in [("31st", "thirty first", True),
                       ("December 31st 2019", "December thirty first twenty nineteen", True),
                       ("21st", "twenty first", True),
                       ("31st", "thirty second", False)]:
    got = format_match(ref, hyp, "window")
    print(f"  window={int(got)} want={int(want)}  {ref!r} vs {hyp!r}"
          + ("" if got == want else "   <-- WRONG"))
