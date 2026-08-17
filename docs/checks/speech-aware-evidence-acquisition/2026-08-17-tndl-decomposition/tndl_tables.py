"""Render the T-NDL markdown tables and example blocks from the decomposition JSON."""
import json, sys
from pathlib import Path

d = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
pc = d["per_class"]
NUMERIC = set(d["groups"]["NUMERIC"])
CONVENTION = set(d["groups"]["CONVENTION"])


def pct(a, b):
    return f"{100.0*a/b:.1f}%" if b else "--"


print("### Per-class three-way decomposition\n")
print("| class | group | wrong | FORMAT | PRE-PUB | NOVEL | fmt% | prepub% | novel% | decoy% |")
print("|---|---|--:|--:|--:|--:|--:|--:|--:|--:|")
rows = [(k, v) for k, v in pc.items() if not k.startswith("__")]
rows.sort(key=lambda kv: -kv[1]["wrong"])
for name, v in rows:
    g = "NUM" if name in NUMERIC else "CONV" if name in CONVENTION else "NAME"
    w = v["wrong"]
    f = v.get("format", 0)
    p = v.get("prepublished", 0)
    n = v.get("novel", 0)
    dk = v.get("prepublished_decoy", 0)
    print(f"| {name} | {g} | {w} | {f} | {p} | {n} | {pct(f,w)} | {pct(p,w)} | "
          f"{pct(n,w)} | {pct(dk,w)} |")
for key, label in (("__NUMERIC", "**NUMERIC total**"), ("__CONVENTION", "**CONVENTION total**"),
                   ("__NAME", "**NAME total**"), ("__ALL", "**ALL total**")):
    v = pc[key]
    w = v["wrong"]; f = v.get("format", 0); p = v.get("prepublished", 0)
    n = v.get("novel", 0); dk = v.get("prepublished_decoy", 0)
    print(f"| {label} | | **{w}** | **{f}** | **{p}** | **{n}** | **{pct(f,w)}** | "
          f"**{pct(p,w)}** | **{pct(n,w)}** | {pct(dk,w)} |")

print("\n### Per-call\n")
print("| call | wrong | FORMAT | PRE-PUB | NOVEL | ConEC PDFs |")
print("|---|--:|--:|--:|--:|---|")
for call, v in sorted(d["per_call"].items()):
    pdfs = d["conec_pdfs"].get(call, [])
    label = ", ".join(f"{m['name']} ({m['chars']}c)" for m in pdfs) or "**none**"
    print(f"| {call} | {v['wrong']} | {v.get('format',0)} | {v.get('prepublished',0)} "
          f"| {v.get('novel',0)} | {label} |")

ex = d["examples"]
print("\n### FORMAT examples CAUGHT\n")
print("The tight window is what the aligner paired with the gold mention; the wide "
      "window (+/-6 tokens) is what the match was actually found in.\n")
print("| # | class | gold mention | hypothesis, tight | hypothesis, wide |")
print("|--:|---|---|---|---|")
seen = set()
shown = 0
for r in ex["format_caught"]:
    key = (r["entity_type"], r["ref_text"])
    if key in seen:
        continue
    seen.add(key)
    print(f"| {shown+1} | {r['entity_type']} | `{r['ref_text']}` | "
          f"`{r['hyp_tight']}` | `{r['hyp_wide']}` |")
    shown += 1
    if shown >= 12:
        break

print("\n### FORMAT examples NOT caught (surviving as true errors)\n")
print("| # | class | gold mention | hypothesis, tight | hypothesis, wide |")
print("|--:|---|---|---|---|")
seen = set(); shown = 0
for r in ex["format_missed"]:
    key = (r["entity_type"], r["ref_text"])
    if key in seen:
        continue
    seen.add(key)
    print(f"| {shown+1} | {r['entity_type']} | `{r['ref_text']}` | "
          f"`{r['hyp_tight']}` | `{r['hyp_wide']}` |")
    shown += 1
    if shown >= 8:
        break

print("\n### PRE-PUBLISHED examples (numeric)\n")
shown = 0
for r in ex["prepublished"]:
    layers = ",".join(k for k, v in r["layer_hit"].items() if v and k != "any")
    print(f"{shown+1:2d}. `{r['entity_type']}` gold `{r['ref_text']}` keys={r['keys']} "
          f"found in [{layers}] decoy_hit={r['decoy_hit']}")
    shown += 1
    if shown >= 10:
        break

print("\n### NOVEL examples (numeric)\n")
shown = 0
for r in ex["novel"]:
    print(f"{shown+1:2d}. `{r['entity_type']}` gold `{r['ref_text']}` "
          f"-> hypothesis `{r['hyp_tight']}` keys={r['keys']}")
    shown += 1
    if shown >= 10:
        break
