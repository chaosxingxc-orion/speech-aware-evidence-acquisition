"""Exercise the future driver fragment and unchanged strict inspector on synthetic files."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]


def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value)+'\n')


@pytest.fixture
def f(tmp_path):
    main,worker,data,pkg=(tmp_path/name for name in ('main','frozen-worker','data','stub-package'))
    original=(ROOT/'scripts/flights/batch/batch_inspect.py').read_bytes()
    for root in (main,worker):
        path=root/'scripts/flights/batch/batch_inspect.py';path.parent.mkdir(parents=True);path.write_bytes(original)
    module=pkg/'speech_aware_evidence_acquisition'
    for rel in ('','core','core/flight','rails'):
        path=module/rel;path.mkdir(parents=True,exist_ok=True);(path/'__init__.py').write_text('')
    (module/'core/flight/cli.py').write_text("""import json
from types import SimpleNamespace
def load_campaign_plan(repo,plan):
 return [(v["experiment"],SimpleNamespace(document=v,run_id=v["run_id"],attempt_id=v["attempt_id"])) for v in json.loads(plan.read_text())["cells"]]
""")
    (module/'core/config.py').write_text("""from types import SimpleNamespace
def compose(*args):
 return SimpleNamespace(values={"population":{"count":2},"policy":"synthetic-native"})
""")
    (module/'rails/controllers.py').write_text('def default_phase_program(policy):return policy\n')
    (module/'rails/native_episode_config.py').write_text("""from types import SimpleNamespace
def load_native_episode_config(*args):
 return SimpleNamespace(max_contacts=3,roles=[SimpleNamespace(max_iterations=1,tool_names=[])])
""")
    cells=[]
    for label in ('synthetic-seed','synthetic-aa'):
        run=label+'-run';attempt=label+'-attempt';directory=data/'runs'/run/attempt
        put(data/'attempts'/run/(attempt+'.json'),{'state':'FINALIZED'})
        put(directory/'original.run-manifest.json',{'status':'COMPLETED','study_commit':'f'*40,'result_kind':'task-answer','study_repo_dirt':None})
        rows=[{'sample_id':sid,'native_episode_receipt':{'contact_count':1}}for sid in ('synthetic-a','synthetic-b')]
        (directory/'original.outputs.jsonl').write_text(''.join(json.dumps(row)+'\n'for row in rows))
        (directory/'score-jobs.jsonl').write_text('{}\n')
        cells.append({'experiment':label,'cell_id':label+'-cell','run_id':run,'attempt_id':attempt,'model_fragment':'synthetic-model','dataset_fragment':'synthetic-dataset','baseline_fragment':'synthetic-baseline'})
    put(worker/'campaign.json',{'cells':cells})
    text=(ROOT/'scripts/flights/batch/batch_driver.sh').read_text();start=text.index('    inspection_args=()');end=text.index('; irc=$?',start)+len('; irc=$?')
    fragment=text[start:end]+"\nprintf '%s\\n' \"$out\"\nexit \"$irc\"\n"
    env={k:v for k,v in os.environ.items()if not k.upper().startswith('GIT_')}
    env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(pkg),PY=sys.executable,SP=str(main/'scripts/flights/batch'),REPO=str(worker),DATA=str(data),run=cells[0]['run_id'],gatt=cells[0]['attempt_id'],plan='campaign.json',rows='2',ceil='3',nt='0',FLIGHT_COMMIT='f'*40,result_kind='task-answer')
    return fragment,env


def test_campaign_uses_frozen_entrypoint_with_real_strict_guard(f):
    fragment,env=f;result=subprocess.run(['bash','-c',fragment],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout);assert report['mode']=='campaign'and report['pass']
    assert len(report['members'])==2 and all(row['exit_code']==0 for row in report['members'])


def test_original_main_entrypoint_reproduces_argparse_refusal(f):
    fragment,env=f
    old=fragment.replace('inspection_script="$REPO/scripts/flights/batch/batch_inspect.py"','inspection_script="$SP/batch_inspect.py"')
    assert old!=fragment
    result=subprocess.run(['bash','-c',old],env=env,capture_output=True,text=True)
    assert result.returncode==2
    assert 'campaign inspector must run from the exact frozen repo-root'in result.stderr
    assert not result.stdout.strip()


@pytest.mark.parametrize('plan',['','None'])
def test_legacy_noncampaign_path_is_unchanged(f,plan):
    fragment,env=f;env['plan']=plan
    result=subprocess.run(['bash','-c',fragment],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout);assert report['mode']=='arm'and report['pass']


def test_smoke_and_inspector_source_guard_remain_unchanged():
    driver=(ROOT/'scripts/flights/batch/batch_driver.sh').read_text()
    assert 'out=$($PY -B $SP/batch_inspect.py "$DATA" "$srun" "$satt" smoke'in driver
    inspector=(ROOT/'scripts/flights/batch/batch_inspect.py').read_text()
    assert 'if repo != Path(__file__).resolve().parents[3]:'in inspector
    assert 'parser.error("campaign inspector must run from the exact frozen repo-root")'in inspector
