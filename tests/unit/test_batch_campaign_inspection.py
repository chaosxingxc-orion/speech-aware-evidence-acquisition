"""Whole-plan inspection reuses every member's existing sealed inspector."""
import json
from pathlib import Path
import runpy
import shutil
import sys
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.core.flight import cli
from speech_aware_evidence_acquisition.core import config
from speech_aware_evidence_acquisition.rails import native_episode_config


@pytest.mark.parametrize("fault", [None, "failed-member", "invalid-json", "outside-plan", "strict-global-notool"])
def test_campaign_inspects_every_configured_member(tmp_path,monkeypatch,capsys,fault):
    source=Path(__file__).resolve().parents[2]/"scripts/flights/batch/batch_inspect.py"
    repo=tmp_path/"repo"
    script=repo/"scripts/flights/batch/batch_inspect.py"
    script.parent.mkdir(parents=True)
    shutil.copyfile(source,script)
    plan=repo/"plan.json"
    plan.write_text("{}",encoding="utf-8")
    from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
    root = Path(__file__).resolve().parents[2]
    labels = ("seed", "seed-aa", "review-off", "solver-lookup")
    from speech_aware_evidence_acquisition.core.flight.campaign import CampaignCell

    def member_cell(stem):
        # Decision 243 (2026-10-10) retired three of these unflown cells (readiness superseded), which
        # campaign loading refuses by design; the inspector fan-out is proven against their registered
        # bytes, so the in-memory cell is marked ready here and nothing on disk changes.
        raw = json.loads((root / "configs/experiment" / (stem + ".json")).read_text(encoding="utf-8"))["cells"][0]
        raw["readiness"]["state"] = "ready"
        return CampaignCell.from_document(raw)

    selected = tuple(("slurp-native-stage3-simple-consumption-" + label + "-n100-v1",
                      member_cell("slurp-native-stage3-simple-consumption-" + label + "-n100-v1"))
                     for label in labels)
    monkeypatch.setattr(cli,"load_campaign_plan",lambda repo,path:selected)
    original_compose = config.compose
    monkeypatch.setattr(config,"compose",lambda repo,m,d,b,e:original_compose(root,m,d,b,e))
    calls=[]
    def inspect(command,**kwargs):
        calls.append(command)
        failed=fault=="failed-member" and command[4]==selected[2][1].run_id
        return SimpleNamespace(returncode=2 if failed else 0,
            stdout="not structural JSON" if fault=="invalid-json" and command[4]==selected[2][1].run_id else
            json.dumps({"run_id":command[4],"attempt_id":command[5],"pass":not failed}),stderr="")
    import subprocess
    monkeypatch.setattr(subprocess,"run",inspect)
    args=[str(script),str(tmp_path/"data"),"representative","outer-attempt","arm","100","13","1" if fault=="strict-global-notool" else "0","a"*40,"--repo-root",str(repo),"--campaign-plan",str(plan if fault!="outside-plan" else tmp_path/"outside.json")]
    monkeypatch.setattr(sys,"argv",args)
    with pytest.raises(SystemExit)as stopped:runpy.run_path(str(script),run_name="__main__")
    if fault=="outside-plan":
        assert stopped.value.code==2 and not calls
        return
    report=json.loads(capsys.readouterr().out)
    assert [c[4]for c in calls]==[cell.run_id for _,cell in selected]
    assert [c[8]for c in calls]==["13","13","2","3"]
    assert [c[9]for c in calls]==(["1"]*4 if fault=="strict-global-notool" else ["0","0","1","0"])
    assert all(c[6:8]==["arm","100"]for c in calls)
    assert [r["report"]["run_id"]for r in report["members"]]==[cell.run_id for _,cell in selected]
    assert stopped.value.code==(0 if fault in (None,"strict-global-notool") else 2)
    assert report["pass"] is (fault in (None,"strict-global-notool"))
