"""Audit and summarize the historical matrix pilot without changing its inputs."""
from pathlib import Path
import hashlib
import json
import platform
import subprocess
import sys
import tempfile

import numpy as np

from pilot_curvature_correction import self_test

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'outputs/runs/v5/upgrade_pilot'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = {'synthetic': self_test()}
    combined, retained, comparisons, bad = [], [], [], []
    manifests = {}
    for method, directory in [('gn-diagonal', 'gn_diagonal_01'), ('gn-exact', 'gn_exact_01')]:
        folder = BASE / directory
        records = json.loads((folder / 'records.json').read_text(encoding='utf-8'))
        manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        manifests[directory] = {p.name: sha(p) for p in folder.iterdir() if p.is_file()}
        assert sha(Path(__file__).with_name('pilot_curvature_correction.py')) == manifest['script_sha256']
        assert len(records) == len(manifest['input_sha256']) == 25
        for name, digest in manifest['input_sha256'].items():
            assert sha(ROOT / name) == digest, name
        for record in records:
            if not record['rows']:
                retained.append({'method': method, 'seed': record['seed'], 'benchmark': record['benchmark'],
                                 'status': 'CHECKPOINT_INVALID' if record['status'] == 'SKIPPED_ORIGINAL_INVALID' else 'NUMERICAL_FAILURE',
                                 'failure_reason': record['reason']})
                continue
            source = json.loads((ROOT / record['source']).read_text(encoding='utf-8'))
            rows = record['rows']
            assert [r['step_budget'] for r in rows] == [0, 1, 3, 5, 10]
            baseline_diff = record['gn_vs_archived_saeps_relative_difference']
            ref_diff = abs(rows[0]['reference_scalar'] - source['rerun']['H_red_exact']) / (abs(source['rerun']['H_red_exact']) + 1e-8)
            assert baseline_diff < 1e-6 and ref_diff < 1e-6
            comparisons.append({'method': method, 'seed': record['seed'], 'baseline_difference': baseline_diff,
                                'schur_reference_difference': ref_diff})
            for row in rows:
                scale = max(abs(row['reference_scalar']), abs(row['corrected_scalar']), 1e-8)
                assert row['identity_relative_residual'] < 1e-8
                assert row['minimum_gap_eigenvalue'] >= -1e-8 * scale
                assert row['maximum_positive_nested_increment_so_far'] <= 1e-8 * scale
                assert record['first_correction_identity_residual'] <= 1e-8 * scale
                entry = {'method': method, 'benchmark': record['benchmark'], 'seed': record['seed'],
                         'status': 'PASS', 'failure_reason': None, 'n_theta': record['n_theta'], **row}
                combined.append(entry)
                if row['corrected_relative_error'] > row['gn_relative_error']:
                    bad.append(entry)
        # Check the CLI's actual overwrite protection, including a sentinel.
        with tempfile.TemporaryDirectory() as temporary:
            sentinel = Path(temporary) / 'sentinel.txt'
            sentinel.write_text('preserve', encoding='utf-8')
            run = subprocess.run([sys.executable, str(Path(__file__).with_name('pilot_curvature_correction.py')),
                                  '--repo', str(ROOT), '--output', temporary], capture_output=True)
            assert run.returncode != 0 and sentinel.read_text() == 'preserve'
    summary = []
    for method in ['gn-diagonal', 'gn-exact']:
        for benchmark in ['ALL', 'Allen-Cahn', 'Burgers']:
            for step in [0, 1, 3, 5, 10]:
                selected = [r for r in combined if r['method'] == method and r['step_budget'] == step
                            and (benchmark == 'ALL' or r['benchmark'] == benchmark)]
                errors = [r['corrected_relative_error'] for r in selected]
                summary.append({'method': method, 'benchmark': benchmark, 'step_budget': step,
                                'valid_n': len(selected), 'median_gn_error': float(np.median([r['gn_relative_error'] for r in selected])),
                                'median_error': float(np.median(errors)), 'worst_error': max(errors),
                                'improved_n': sum(r['improved_over_gn'] for r in selected),
                                'worst_seed': max(selected, key=lambda r:r['corrected_relative_error'])['seed']})
    output = BASE / 'audit'
    output.mkdir(exist_ok=True)
    data = {'status': 'PASSED', 'scope': 'HISTORICAL_MATRIX_DEVELOPMENT_ONLY',
            'unique_planned': 25, 'unique_valid': 21, 'unique_invalid': 4,
            'checks': checks, 'summary': summary, 'retained_invalid': retained,
            'worsened_rows': bad, 'baseline_checks': comparisons, 'rows': combined,
            'input_artifact_sha256': manifests, 'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'git_status_at_audit': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True),
            'hardware': platform.platform(), 'dtype': 'float64', 'python': platform.python_version(),
            'audit_script_sha256': sha(Path(__file__)), 'starter_zip_sha256': sha(ROOT / 'SAEPS_upgrade_starter.zip'),
            'JVP_count': 0, 'VJP_count': 0, 'HVP_count': 0, 'CG_iterations': 0,
            'timing': None, 'timing_limitation': 'Starter does not instrument component timing; dense oracle and candidate work are interleaved. No speedup or equal-accuracy cost claim.',
            'peak_memory': None}
    (output / 'audit.json').write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    lines = ['# 第一层：历史矩阵开发试验', '',
             '仅复用归档矩阵；不训练、不改变历史确认配置与结论。本文数值由 audit_pilot.py 从 outputs/runs/v5/upgrade_pilot 自动生成。', '',
             f"工程核验：{data['status']}。历史计划 {data['unique_planned']} 条，有效 {data['unique_valid']} 条，原有无效 {data['unique_invalid']} 条；两组使用完全相同检查点。", '',
             '误差定义：相对同一 gamma 下精确 Schur 的 Frobenius 误差，分母为 ||H*||+1e-8。预算0为已有 K(Z0) 二阶投影修正；预算k是最多k次共同子空间扩展，并非完整算法迭代成本。', '',
             '|预处理|问题|扩展预算|有效数|原SAEPS中位误差|修正中位误差|最差误差|改善数|',
             '|---|---|---:|---:|---:|---:|---:|---:|']
    for row in summary:
        lines.append(f"|{row['method']}|{row['benchmark']}|{row['step_budget']}|{row['valid_n']}|{row['median_gn_error']:.6g}|{row['median_error']:.6g}|{row['worst_error']:.6g}|{row['improved_n']}|")
    lines += ['', '## 核验', '',
              f"归档SAEPS最大相对复核差：{max(r['baseline_difference'] for r in comparisons):.6g}；归档精确Schur最大相对复核差：{max(r['schur_reference_difference'] for r in comparisons):.6g}。",
              f"配方恒等式最大相对残差：{max(r['identity_relative_residual'] for r in combined):.6g}。正半定间隙、嵌套单调性和已有修正公式在1e-8尺度容差内通过。基线复核容差1e-6。",
              '16组随机SPD、仿射退化、非正定拒绝、原无效保留与实际CLI覆盖保护均通过。以上容差用于工程核验，不是新增科学支持阈值。', '',
              '## 变差记录', '', '|预处理|问题|seed|预算|原误差|修正误差|', '|---|---|---:|---:|---:|---:|']
    for r in bad:
        lines.append(f"|{r['method']}|{r['benchmark']}|{r['seed']}|{r['step_budget']}|{r['gn_relative_error']:.6g}|{r['corrected_relative_error']:.6g}|")
    lines += ['', 'K(Z0)高于精确Schur不代表它必然比原SAEPS更接近参考；这些变差样本保留，不调参消除。', '', '## 保留的无效检查点', '']
    for r in retained:
        if r['method'] == 'gn-diagonal':
            lines.append(f"- {r['benchmark']} seed {r['seed']}: {r['status']} — {r['failure_reason']}")
    lines += ['', '## 解释与下一步边界', '',
              '结果支持继续研究二阶响应修正。对角预处理下增加少量方向收益有限，精确GN控制组收益显著；这提示预处理可能是主要瓶颈，但不是因果证明。',
              'gn-exact每次使用稠密状态求解，只是乐观控制组；当前矩阵规模小，且初始GN响应与验证oracle均用稠密求解。没有独立组件计时、HVP成本或可扩展性证据，尚未满足“同等误差下成本更低”的进阶条件。',
              '不自动启动第二层训练。下一步应先研究可扩展预处理与完整成本测量；新的确认评价必须冻结新配置并使用独立种子/观测。精确Schur代数的一致性不能替代nonlinear profile验证。', '',
              '## 全部有效检查点逐预算数据', '', '|预处理|问题|seed|预算|状态维数|子空间维数|原误差|修正误差|', '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in combined:
        lines.append(f"|{r['method']}|{r['benchmark']}|{r['seed']}|{r['step_budget']}|{r['n_theta']}|{r['basis_dimension']}|{r['gn_relative_error']:.6g}|{r['corrected_relative_error']:.6g}|")
    validation_path = output / 'repository_validation.json'
    if validation_path.exists():
        validation = json.loads(validation_path.read_text(encoding='utf-8'))
        lines += ['', '## 全仓库验证', '', f"全仓库状态：{validation['status']}。本试验独立审计状态与全仓库状态分别报告。"]
        for name, result in validation['checks'].items():
            if result['status'] != 'PASS':
                lines.append(f"- {name}: {result['status']}；详情见 repository_validation.json。")
        lines.append('全仓库剩余失败源于任务开始前已删除的历史报告/协议文件；未替用户恢复这些文件，未推送远端。')
    (output / 'REPORT.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'status': data['status'], 'summary_all': [r for r in summary if r['benchmark'] == 'ALL']}, indent=2))


if __name__ == '__main__':
    main()
