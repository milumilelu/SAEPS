"""Phase 4 development runner: preflight audit, bounded task pool, manifest.

Usage (run with the project venv python):
  python run_development.py preflight   # environment lock + historical hash baseline
  python run_development.py smoke       # tiny-budget pipeline check into preflight/smoke
  python run_development.py tasks       # the 12 planned tasks, max 6 concurrent workers

Workers run under systemd --user units with a hard wall clock, a 4GiB memory
ceiling and a kill-on-close process tree, mirroring the Phase 3 platform
adapter. Historical inputs are never modified.
"""
from __future__ import annotations
import os, signal, subprocess, sys, time, uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from objective_adapter import (SCOPE, OUT, ROOT, TASK_ROOT, env_setup, hash_tree,
                               sha256_file, sha256_tensor)

env_setup()

import numpy as np
import psutil
from common import environment, read, write

WORKER = Path(__file__).with_name('worker.py')


def bounded_process(command, dest, seconds, memory_bytes):
    """Run a worker under a systemd --user unit with hard resource bounds."""
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    unit = 'saeps-p4-' + uuid.uuid4().hex
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1',
               MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', PYTHONUTF8='1')
    launch = ['systemd-run', '--user', '--quiet', '--unit=' + unit,
              '--service-type=exec', '-p', 'RemainAfterExit=yes',
              '-p', 'KillMode=control-group', '-p', 'MemoryAccounting=yes',
              '-p', f'MemoryMax={memory_bytes}', '-p', 'OOMPolicy=kill',
              '-p', f'RuntimeMaxSec={seconds}', '-p', 'TimeoutStopSec=0.1',
              '-p', f'WorkingDirectory={ROOT}',
              '-p', f'StandardOutput=append:{dest}/stdout.log',
              '-p', f'StandardError=append:{dest}/stderr.log']
    for key in ('CUDA_VISIBLE_DEVICES', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                'OPENBLAS_NUM_THREADS', 'PYTHONUTF8'):
        launch.append(f'--setenv={key}={env[key]}')
    launch += ['--', sys.executable, *map(str, command)]
    run = subprocess.run(launch, capture_output=True, text=True, env=env)
    if run.returncode:
        raise RuntimeError('systemd launch failed: ' + run.stderr)
    properties = unit_properties(unit)
    cgroup = Path('/sys/fs/cgroup' + properties['ControlGroup'])
    seen = set()
    samples = []
    peak = None
    reason = None
    try:
        write(dest / 'process_started.json', dict(scope=SCOPE, unit=unit,
              pid=int(properties.get('MainPID', '0')), cgroup=str(cgroup),
              timeout_seconds=seconds, memory_limit_bytes=memory_bytes))
        while True:
            ids = []
            try:
                ids = [int(v) for v in (cgroup / 'cgroup.procs').read_text().split()]
            except FileNotFoundError:
                pass
            seen.update(ids)
            rss_values = []
            for pid in ids:
                try:
                    fields = {line.split(':')[0]: line.split(':')[1].strip()
                              for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line}
                    if 'VmRSS' in fields:
                        rss_values.append(int(fields['VmRSS'].split()[0]) * 1024)
                except (FileNotFoundError, ProcessLookupError):
                    pass
            rss = sum(rss_values) if rss_values else None
            if rss is not None:
                peak = max(peak or rss, rss)
            sample = dict(seconds=time.perf_counter() - started, pids=ids, rss_bytes=rss)
            try:
                sample['cgroup_memory_current_bytes'] = int((cgroup / 'memory.current').read_text())
            except FileNotFoundError:
                sample['cgroup_memory_current_bytes'] = None
            samples.append(sample)
            properties = unit_properties(unit)
            if rss is not None and rss > memory_bytes:
                reason = 'resource_limit'
                break
            if properties.get('SubState') in ('exited', 'dead', 'failed') or \
                    properties.get('ActiveState') in ('inactive', 'failed'):
                break
            if time.perf_counter() - started >= seconds:
                reason = 'budget_exhausted'
                break
            time.sleep(0.2)
        events = (cgroup / 'memory.events').read_text() if (cgroup / 'memory.events').exists() else None
        if properties.get('Result') == 'oom-kill' or (events and any(
                line.startswith('oom_kill ') and int(line.split()[1]) > 0
                for line in events.splitlines())):
            reason = 'resource_limit'
        elif properties.get('Result') == 'timeout':
            reason = 'budget_exhausted'
    finally:
        for arguments in (('kill', '--kill-who=all', '--signal=SIGKILL', unit),
                          ('stop', unit), ('reset-failed', unit)):
            subprocess.run(['systemctl', '--user', *arguments], capture_output=True, text=True)
    survivors = []
    for pid in seen:
        try:
            if psutil.Process(pid).status() != psutil.STATUS_ZOMBIE:
                survivors.append(pid)
        except psutil.NoSuchProcess:
            pass
    code = int(properties.get('ExecMainStatus', '1'))
    if reason and code == 0:
        code = -signal.SIGKILL
    result = dict(scope=SCOPE, unit=unit, exit_code=code,
                  status='PASS' if code == 0 and not reason and not survivors else 'SOLVER_FAILURE',
                  failure_reason=reason or ('surviving_descendants' if survivors else
                                            ('worker_exit_nonzero' if code else None)),
                  wall_seconds=time.perf_counter() - started,
                  sampled_peak_rss_bytes=peak,
                  memory_limit_bytes=memory_bytes, timeout_seconds=seconds,
                  observed_process_ids=sorted(seen), surviving_process_ids=survivors,
                  timing_kind='measured')
    write(dest / 'process.json', result)
    files = [dict(path=path.name, sha256=sha256_file(path)) for path in sorted(dest.iterdir())
             if path.is_file() and path.name != 'manifest.json']
    write(dest / 'manifest.json', dict(scope=SCOPE, process=result, files=files))
    return result


def unit_properties(unit):
    result = subprocess.run(['systemctl', '--user', 'show', unit,
                             '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID',
                             '-p', 'ExecMainStatus', '-p', 'Result', '-p', 'ControlGroup'],
                            capture_output=True, text=True)
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def git_head():
    return subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip()


def preflight():
    protocol = read(Path(__file__).with_name('protocol.json'))
    destination = OUT / 'preflight'
    destination.mkdir(parents=True, exist_ok=True)
    records = hash_tree(protocol['historical_hash_audit']['paths'])
    write(destination / 'HISTORICAL_HASH_BASELINE.json',
          dict(scope=SCOPE, purpose='baseline SHA256 audit before any Phase 4 numerical task',
               baseline_commit=protocol['baseline_commit'], unix_time=time.time(),
               file_count=len(records), records=records))
    import scipy
    record = environment()
    try:
        blas = np.__config__.CONFIG.get('Build Dependencies', {}).get('blas', {}).get('name')
    except Exception:
        blas = None
    record.update(numpy=np.__version__, scipy=scipy.__version__,
                  blas_backend=blas,
                  thread_environment={key: os.environ.get(key) for key in
                                      ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                                       'CUDA_VISIBLE_DEVICES')},
                  protocol_sha256=sha256_file(Path(__file__).with_name('protocol.json')),
                  git_head=git_head(), git_branch=subprocess.check_output(
                      ['git', '-C', str(ROOT), 'rev-parse', '--abbrev-ref', 'HEAD']).decode().strip())
    write(destination / 'environment.json', record)
    print('preflight complete:', destination)


def smoke():
    import json
    protocol = read(Path(__file__).with_name('protocol.json'))
    override = dict(wall_seconds=90.0, wall_caps=[40.0, 30.0, 20.0], nfev_total=6000)
    destination = OUT / 'preflight' / 'smoke'
    destination.mkdir(parents=True, exist_ok=True)
    for center in protocol['centers']['list'][:1]:
        for route in ('raw', 'proximal'):
            task = destination / f'{center}_{route}'
            bounded_process([str(WORKER), center, route, str(task),
                             '--smoke', json.dumps(override)], task,
                            seconds=int(override['wall_seconds']) + 60,
                            memory_bytes=int(protocol['resources']['memory_bytes_per_worker']))
            claim_path = task / 'claim.json'
            if claim_path.exists():
                claim = read(claim_path)
                print(f"smoke {center} {route}: {claim['terminal_status']} "
                      f"g={claim.get('achieved_normalized_gradient')}")
            else:
                print(f"smoke {center} {route}: claim.json missing")
    print('smoke complete:', destination)


def tasks_run():
    protocol = read(Path(__file__).with_name('protocol.json'))
    centers = protocol['centers']['list']
    resources = protocol['resources']
    per_task = int(resources['memory_bytes_per_worker'])
    available = psutil.virtual_memory().available
    requested = int(resources['max_concurrent_workers'])
    concurrency = max(1, min(requested, available // per_task))
    lowered = concurrency < requested
    planned = [(center, route) for center in centers for route in ('raw', 'proximal')]
    destination = OUT / 'tasks'
    destination.mkdir(parents=True, exist_ok=True)
    started_unix = time.time()

    def run_one(item):
        center, route = item
        task_dir = destination / f'{center}_{route}'
        command = [str(WORKER), center, route, str(task_dir)]
        try:
            process = bounded_process(command, task_dir,
                                      seconds=int(resources['wall_seconds_per_task']) + int(resources['runtime_max_sec_grace']),
                                      memory_bytes=per_task)
        except Exception as error:
            process = dict(scope=SCOPE, status='LAUNCH_FAILURE', failure_reason=repr(error),
                           wall_seconds=0.0, sampled_peak_rss_bytes=None, exit_code=None)
        return center, route, process

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        outcomes = list(pool.map(run_one, planned))
    rows = []
    for center, route, process in outcomes:
        task_dir = destination / f'{center}_{route}'
        claim_path = task_dir / 'claim.json'
        claim = read(claim_path) if claim_path.exists() else None
        rows.append(dict(center=center, route=route, process_status=process['status'],
                         process_failure_reason=process['failure_reason'],
                         exit_code=process['exit_code'],
                         terminal_status=claim['terminal_status'] if claim else None,
                         failure_reason=claim['failure_reason'] if claim else 'claim.json missing after worker exit',
                         wall_seconds=process['wall_seconds'],
                         sampled_peak_rss_bytes=process['sampled_peak_rss_bytes'],
                         nfev_total=claim.get('nfev_total') if claim else None,
                         smoke=bool(claim.get('smoke')) if claim else None))
    manifest = dict(scope=SCOPE, started_unix=started_unix, finished_unix=time.time(),
                    head_commit=git_head(), planned_positions=planned,
                    concurrency_limit=requested, concurrency_used=concurrency,
                    concurrency_lowered=lowered, lowering_note='scheduler lowered concurrency for memory feasibility; per-task limits unchanged' if lowered else None,
                    rows=rows)
    write(OUT / 'RUN_MANIFEST.json', manifest)
    for row in rows:
        print(f"{row['center']} {row['route']}: process={row['process_status']} "
              f"terminal={row['terminal_status']} reason={row['failure_reason']}")


def grid():
    """The frozen alpha grid: 6 centers x 5 alpha = 30 proximal tasks, all in the denominator."""
    protocol = read(Path(__file__).with_name('protocol.json'))
    centers = protocol['centers']['list']
    alphas = [float(v) for v in protocol['alpha_grid']['values']]
    resources = protocol['resources']
    per_task = int(resources['memory_bytes_per_worker'])
    available = psutil.virtual_memory().available
    requested = int(resources['max_concurrent_workers'])
    concurrency = max(1, min(requested, available // per_task))
    lowered = concurrency < requested
    planned = [(center, alpha) for alpha in alphas for center in centers]
    destination = OUT / 'tasks_grid'
    destination.mkdir(parents=True, exist_ok=True)
    started_unix = time.time()

    def run_one(item):
        center, alpha = item
        task_dir = destination / f'{center}_a{alpha:.0e}'
        command = [str(WORKER), center, 'proximal', str(task_dir), '--alpha', repr(alpha)]
        try:
            process = bounded_process(command, task_dir,
                                      seconds=int(resources['wall_seconds_per_task']) + int(resources['runtime_max_sec_grace']),
                                      memory_bytes=per_task)
        except Exception as error:
            process = dict(scope=SCOPE, status='LAUNCH_FAILURE', failure_reason=repr(error),
                           wall_seconds=0.0, sampled_peak_rss_bytes=None, exit_code=None)
        return center, alpha, process

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        outcomes = list(pool.map(run_one, planned))
    rows = []
    for center, alpha, process in outcomes:
        task_dir = destination / f'{center}_a{alpha:.0e}'
        claim_path = task_dir / 'claim.json'
        claim = read(claim_path) if claim_path.exists() else None
        rows.append(dict(center=center, alpha=alpha,
                         task_dir=str(task_dir.relative_to(OUT)),
                         process_status=process['status'],
                         process_failure_reason=process['failure_reason'],
                         exit_code=process['exit_code'],
                         terminal_status=claim['terminal_status'] if claim else None,
                         failure_reason=claim['failure_reason'] if claim else 'claim.json missing after worker exit',
                         wall_seconds=process['wall_seconds'],
                         sampled_peak_rss_bytes=process['sampled_peak_rss_bytes'],
                         achieved_normalized_gradient=(claim.get('achieved_normalized_gradient') if claim else None),
                         smoke=bool(claim.get('smoke')) if claim else None))
    manifest = dict(scope=SCOPE, kind='alpha_grid', started_unix=started_unix,
                    finished_unix=time.time(), head_commit=git_head(),
                    planned_positions=planned, alphas=alphas,
                    concurrency_limit=requested, concurrency_used=concurrency,
                    concurrency_lowered=lowered, rows=rows)
    write(OUT / 'GRID_RUN_MANIFEST.json', manifest)
    for row in rows:
        print(f"{row['task_dir']}: {row['terminal_status']} {row['failure_reason']}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode == 'preflight':
        preflight()
    elif mode == 'smoke':
        smoke()
    elif mode == 'tasks':
        tasks_run()
    elif mode == 'grid':
        grid()
    else:
        raise SystemExit('usage: run_development.py preflight|smoke|tasks|grid')


if __name__ == '__main__':
    main()
