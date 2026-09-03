import json, sys
from pathlib import Path
import pytest
from reprojudge.schema import parse_task
from reprojudge.runner import run_task
from reprojudge.scoring import score_task
from reprojudge.evidence import source_fingerprint
from reprojudge.reporting import load_results
from reprojudge.leaderboard import build_leaderboard

def symlink_or_skip(link, target, **kwargs):
    try:
        link.symlink_to(target, **kwargs)
    except OSError:
        pytest.skip('symlink creation is unavailable')

def base(**extra):
    p={'task_id':'hard','domain':'demo','paper':'synthetic:test','expected_artifacts':['x.json']}
    p.update(extra); return p

def test_programmatic_metadata_must_be_json():
    with pytest.raises(ValueError, match='finite.*JSON'):
        parse_task(base(metadata={'bad':float('nan')}))
    with pytest.raises(ValueError, match='finite.*JSON'):
        parse_task(base(metadata={'bad':object()}))

def test_json_equals_expected_must_be_json():
    with pytest.raises(ValueError, match='finite.*JSON'):
        parse_task(base(checks=[{'type':'json_equals','artifact':'x.json','json_path':'x','expected':float('nan')}]))

def test_unknown_task_and_check_fields_fail_closed():
    with pytest.raises(ValueError, match='unsupported fields'):
        parse_task(base(typo=True))
    with pytest.raises(ValueError, match='unsupported fields'):
        parse_task(base(checks=[{'type':'artifact_exists','artifact':'x.json','typo':True}]))

def test_agent_request_hides_gold_checks(tmp_path):
    task=parse_task(base(checks=[{'type':'json_numeric','artifact':'x.json','json_path':'score','target':12345.6789}]))
    code="import json,os,pathlib;p=pathlib.Path(os.environ['REPROJUDGE_OUTPUT_DIR']);(p/'x.json').write_text(json.dumps({'score':0}))"
    result,run=run_task(task,[sys.executable,'-c',code],output_root=tmp_path)
    request=(run/'request.json').read_text()
    assert '12345.6789' not in request
    assert 'checks' not in json.loads(request)
    assert result.task_sha256 != result.request_sha256
    assert result.status=='failed'
    assert 'evaluator_check_mismatch' in result.failure_taxonomy

def test_nested_artifact_symlink_is_rejected(tmp_path):
    root=tmp_path/'artifacts'; root.mkdir(); outside=tmp_path/'outside'; outside.mkdir(); (outside/'x.json').write_text('{}')
    symlink_or_skip(root/'nested', outside, target_is_directory=True)
    task=parse_task({'task_id':'s','domain':'d','paper':'p','expected_artifacts':['nested/x.json']})
    checks=score_task(task,root)
    assert checks[0].passed is False
    assert 'symlink' in checks[0].detail

def test_unhashable_declared_artifact_fails_evidence(monkeypatch,tmp_path):
    monkeypatch.setattr('reprojudge.runner.MAX_ARTIFACT_HASH_BYTES',2)
    task=parse_task(base())
    code="import os,pathlib;p=pathlib.Path(os.environ['REPROJUDGE_OUTPUT_DIR']);(p/'x.json').write_text('123')"
    result,_=run_task(task,[sys.executable,'-c',code],output_root=tmp_path)
    assert result.status=='failed'
    assert 'artifact_evidence_unrecordable' in result.failure_taxonomy

def test_runner_rejects_symlink_output_root(tmp_path):
    outside=tmp_path/'outside'; outside.mkdir()
    link=tmp_path/'runs'
    symlink_or_skip(link, outside, target_is_directory=True)
    task=parse_task({'task_id':'root','domain':'d','paper':'p','expected_artifacts':[]})
    with pytest.raises(ValueError, match='output root'):
        run_task(task,[sys.executable,'-c','pass'],output_root=link)
    assert not any(outside.iterdir())

def test_output_root_under_system_temp_is_allowed(tmp_path):
    import tempfile
    task=parse_task({'task_id':'tmpok','domain':'d','paper':'p','expected_artifacts':[]})
    root=Path(tempfile.gettempdir())/'reprojudge-tmp-allowance-test'
    root.mkdir(parents=True, exist_ok=True)
    try:
        result,run=run_task(task,[sys.executable,'-c','pass'],output_root=root)
        assert result.status=='passed'
    finally:
        import shutil
        shutil.rmtree(root, ignore_errors=True)

def test_source_fingerprint_covers_tests_and_suite(tmp_path):
    for d in ('src','tests','benchmarks','scripts','docs','examples','.github'):(tmp_path/d).mkdir()
    (tmp_path/'pyproject.toml').write_text('x')
    (tmp_path/'src/a.py').write_text('a')
    (tmp_path/'tests/test_a.py').write_text('a')
    (tmp_path/'benchmarks/reference-suite.json').write_text('{}')
    a=source_fingerprint(tmp_path)
    (tmp_path/'tests/test_a.py').write_text('b')
    b=source_fingerprint(tmp_path)
    assert a!=b
    (tmp_path/'tests/test_a.py').write_text('a')
    c=source_fingerprint(tmp_path)
    (tmp_path/'benchmarks/reference-suite.json').write_text('{"x":1}')
    d=source_fingerprint(tmp_path)
    assert c!=d

def test_release_relevant_symlink_fails_source_identity(tmp_path):
    (tmp_path/'src').mkdir(); outside=tmp_path/'outside'; outside.write_text('x'); symlink_or_skip(tmp_path/'src/x.py', outside)
    with pytest.raises(ValueError, match='symlink'):
        source_fingerprint(tmp_path)

def test_load_results_rejects_result_symlink(tmp_path):
    root=tmp_path/'runs'; root.mkdir(); outside=tmp_path/'outside'; outside.mkdir(); (outside/'result.json').write_text('{"task_id":"x","status":"passed"}')
    symlink_or_skip(root/'link', outside, target_is_directory=True)
    symlink_root=tmp_path/'root-link'; symlink_or_skip(symlink_root, outside, target_is_directory=True)
    with pytest.raises(ValueError, match='must not be a symlink'):
        load_results(symlink_root)

def test_load_results_rejects_nonfinite_and_inconsistent_evidence(tmp_path):
    root=tmp_path/'runs'; run=root/'x'; run.mkdir(parents=True)
    result=run/'result.json'
    result.write_text('{"result_schema_version":1,"task_id":"x","status":"passed","passed":true,"duration_seconds":1e999}')
    with pytest.raises(ValueError, match='non-finite|duration_seconds'):
        load_results(root)
    result.write_text(json.dumps({'result_schema_version':1,'task_id':'x','status':'failed','passed':True,'duration_seconds':1.0}))
    with pytest.raises(ValueError, match='inconsistent'):
        load_results(root)

def test_load_results_rejects_unsafe_recorded_artifact_path(tmp_path):
    root=tmp_path/'runs'; run=root/'x'; run.mkdir(parents=True)
    payload={
        'result_schema_version':1, 'task_id':'x', 'status':'passed',
        'passed':True, 'duration_seconds':1.0,
        'artifacts':[{'path':'../secret.txt','size_bytes':0,'sha256':'0'*64}],
    }
    (run/'result.json').write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(ValueError, match='artifact path'):
        load_results(root)

def test_load_results_rejects_unsupported_nested_result_fields(tmp_path):
    root=tmp_path/'runs'; run=root/'x'; run.mkdir(parents=True)
    payload={
        'result_schema_version':1, 'task_id':'x', 'status':'passed',
        'passed':True, 'duration_seconds':1.0,
        'artifacts':[], 'checks':[], 'telemetry':{'unexpected':'value'},
    }
    (run/'result.json').write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(ValueError, match='telemetry'):
        load_results(root)

def test_standalone_export_rejects_symlink_destination(tmp_path):
    from scripts.standalone_export import export_standalone

    target=tmp_path/'outside'; target.mkdir()
    link=tmp_path/'export'
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('symlink creation is unavailable')
    with pytest.raises(ValueError, match='symlink'):
        export_standalone(link)
    assert target.is_dir()

def test_standalone_export_omits_versioned_release_evidence(tmp_path, monkeypatch):
    import scripts.standalone_export as standalone_export

    source = tmp_path / 'source'; (source / 'src').mkdir(parents=True)
    (source / 'src' / 'core.py').write_text('VALUE = 1\n', encoding='utf-8')
    (source / 'benchmarks').mkdir()
    evidence = source / 'benchmarks' / 'release-evidence-0.3.0.json'
    evidence.write_text('{}\n', encoding='utf-8')
    destination = tmp_path / 'export'
    monkeypatch.setattr(standalone_export, 'ROOT', source)

    result = standalone_export.export_standalone(destination)

    assert result['files'] == 1
    assert not (destination / 'benchmarks' / evidence.name).exists()

def test_leaderboard_rejects_invalid_measurements():
    with pytest.raises(ValueError, match='model_cost_usd'):
        build_leaderboard([{'task_id':'x','status':'passed','duration_seconds':1.0,'telemetry':{'agent_name':'a','agent_version':'1','model_cost_usd':-1}}])
    with pytest.raises(ValueError, match='token_usage'):
        build_leaderboard([{'task_id':'x','status':'passed','duration_seconds':1.0,'telemetry':{'agent_name':'a','agent_version':'1','token_usage':-1}}])

def test_regex_scorer_has_hard_timeout(tmp_path):
    p=tmp_path/'x.txt'; p.write_text('a'*200000+'!')
    task=parse_task({'task_id':'r','domain':'d','paper':'p','expected_artifacts':['x.txt'],'checks':[{'type':'text_regex','artifact':'x.txt','pattern':'(a+)+$'}]})
    checks=score_task(task,tmp_path)
    assert checks[0].passed is False
    assert 'timeout' in checks[0].detail

def test_successful_agent_cannot_leave_same_group_background_writer(tmp_path):
    if sys.platform == 'win32':
        pytest.skip('POSIX process-group invariant')
    task=parse_task({'task_id':'bg','domain':'d','paper':'p','expected_artifacts':[]})
    marker=tmp_path/'late.txt'
    child="import time,pathlib,sys;time.sleep(0.7);pathlib.Path(sys.argv[1]).write_text('late')"
    parent=(
        "import subprocess,sys;"
        f"subprocess.Popen([sys.executable,'-c',{child!r},{str(marker)!r}]);"
        "raise SystemExit(0)"
    )
    result,_=run_task(task,[sys.executable,'-c',parent],output_root=tmp_path/'runs')
    assert result.status=='passed'
    import time; time.sleep(0.9)
    assert not marker.exists()
