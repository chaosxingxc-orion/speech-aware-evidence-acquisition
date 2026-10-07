"""Source qualification never grants or replaces exact complete-family READ."""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest
from test_system_architecture_read import scope_fixture
from speech_aware_evidence_acquisition.analysis import system_architecture_read as architecture
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError

ROOT=Path(__file__).parents[2]
spec=importlib.util.spec_from_file_location('_source_only_ledger',ROOT/'scripts/system_text_search.py')
cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)


def test_source_only_complete_registration_returns_no_evidence_or_authority(tmp_path,monkeypatch):
    _,recipe,registration,owner,_,_,_,_=scope_fixture(tmp_path,monkeypatch)
    scope=architecture.validate_source_registration(recipe,registration,owner,repo_root=tmp_path,data_root=tmp_path/'data')
    assert scope['labels']==list(registration['expected_members'])
    assert len(scope['labels'])==4
    assert not any(k in scope for k in ('read_authority','read_run_id','feedback','summaries'))


@pytest.mark.parametrize('family_authority',[None,'member','wrong-family'])
def test_real_signed_member_read_never_authorizes_complete_family(tmp_path,monkeypatch,family_authority):
    _,recipe,registration,owner,_,_,_,_=scope_fixture(tmp_path,monkeypatch)
    member={'family_id':recipe['family_id'],'expected_members':registration['expected_members'],
            'run_ids':{'read':'ACTUAL-MEMBER-READ'}}
    path=tmp_path/'docs/readiness/member-read.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(member))
    record={'relpath':path.relative_to(tmp_path).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (tmp_path/'docs/exposure-ledger.md').write_text('| run/experiment id | execution profile | split role | calls | artifacts | notes |\n|---|---|---|---|---|---|\n| ACTUAL-MEMBER-READ | model-free-check | discovery | 0 | '+record['relpath']+' | ROOT COUNTERSIGNED after completed member qualification. |\n')
    authority=cli.require_read_registration({**member,'read_registration':record},repo_root=tmp_path)
    assert authority['read_run_id']=='ACTUAL-MEMBER-READ'
    if family_authority is None:authority={}
    elif family_authority=='wrong-family':authority={**authority,'read_run_id':'WRONG-FAMILY-READ'}
    with pytest.raises(PolicyError,match='exact root manual READ'):
        architecture.validate_registration(recipe,registration,owner,authority,repo_root=tmp_path,data_root=tmp_path/'data')
