"""Observe Windows physical memory with a pinned bounded config; no experiment dispatch."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time

from speech_aware_evidence_acquisition.core.session.windows_memory import WindowsMemoryObserver


def run_probe(config, output, *, observer_factory=WindowsMemoryObserver, sleep=time.sleep):
    if (not isinstance(config, dict) or set(config) != {'schema','sample_count','interval_seconds','timeout_seconds'}
        or config['schema'] != 'saea-memory-observer-probe-v1'
        or type(config['sample_count']) is not int or config['sample_count'] <= 0
        or any(type(config[k]) not in (int,float) or not math.isfinite(config[k]) or config[k] <= 0
               for k in ('interval_seconds','timeout_seconds'))
        or config['timeout_seconds'] > 8):
        raise ValueError('invalid bounded observer diagnostic config')
    root=Path(output)
    root.mkdir(parents=True,exist_ok=False)
    (root/'started.json').write_text(json.dumps({'pid':os.getpid(),'started_at':time.time(),'config':config})+'\n')
    count=0
    status='completed'
    with (root/'samples.jsonl').open('x') as log, observer_factory(timeout=config['timeout_seconds']) as observer:
        for index in range(config['sample_count']):
            started=time.monotonic()
            wall_start=time.time()
            reading=observer()
            log.write(json.dumps({'index':index,'wall_start':wall_start,'wall_end':time.time(),
                                  'roundtrip_seconds':time.monotonic()-started,'reading':reading},allow_nan=False)+'\n')
            log.flush()
            count += 1
            if reading.get('host_free_gb') is None:
                status='observation-failed'
                break
            if index+1 < config['sample_count']:
                sleep(config['interval_seconds'])
    result={'schema':'saea-memory-observer-probe-result-v1','status':status,'samples':count,
            'config':config,'finished_at':time.time(),'model_contacts':0,'scorer_contacts':0,
            'services_changed':False,'experiment_recovery':False}
    (root/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    raw=args.config.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.sha256:
        raise ValueError('diagnostic config hash differs')
    result=run_probe(json.loads(raw),args.output)
    print(json.dumps(result))
    return 0 if result['status']=='completed' else 125


if __name__=='__main__':
    raise SystemExit(main())
