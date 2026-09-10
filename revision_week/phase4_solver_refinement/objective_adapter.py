"""Phase 4 development-only objective adapters and provenance helpers.

Import-only reuse of the locked Phase 2 objective machinery; no locked file is
modified. Route R optimizes the raw physical sum-of-squares objective; Route P
adds a proximal term anchored at the archived network state theta0 with a
per-center gamma frozen before any solve.
"""
from __future__ import annotations
import hashlib, math, os, sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PHASE2 = Path(__file__).resolve().parents[1] / 'phase2'


def env_setup():
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'):
        os.environ[key] = '1'
    os.environ['PYTHONUTF8'] = '1'
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    if PHASE2.is_dir():
        sys.path.insert(0, str(PHASE2))
    sys.path.insert(0, str(ROOT / 'revision_week'))
    sys.path.insert(0, str(ROOT / 'src'))
    import torch
    torch.set_default_dtype(torch.float64)
    torch.set_num_threads(1)
    return torch


env_setup()

import torch
from common import load_payload, save_payload, residual_from_payload, read, native, write, norm
from numerics import Objective
from core import numerical_mu, sym

SCOPE = 'PHASE4_SOLVER_REFINEMENT'
OUT = ROOT / 'revision_week/outputs/phase4_solver_refinement_v1'
TASK_ROOT = ROOT / 'revision_week/outputs/phase2_v1/tasks'


class SolverAbort(RuntimeError):
    """Controlled failure inside a residual/Jacobian evaluation."""

    def __init__(self, kind, detail):
        super().__init__(f'{kind}: {detail}')
        self.kind = kind
        self.detail = detail


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_tensor(theta):
    return hashlib.sha256(theta.detach().cpu().numpy().tobytes()).hexdigest()


def center_group(center):
    return 'E4C' if center.startswith('multi_') else 'E1'


def source_dir(center):
    return TASK_ROOT / center_group(center) / center


def load_source(center):
    """Load the archived Phase-2 state for a center; raises FileNotFoundError."""
    directory = source_dir(center)
    if not directory.is_dir():
        raise FileNotFoundError(f'{center}: missing source dir {directory}')
    required = directory / 'lbfgs_state.pt'
    if not required.exists():
        raise FileNotFoundError(f'{center}: missing {required}')
    payload = load_payload(required)
    hashes = {'lbfgs_state.pt': sha256_file(required)}
    historical_gamma = None
    historical_anchor = None
    state_path = directory / 'state.pt'
    if state_path.exists():
        hashes['state.pt'] = sha256_file(state_path)
        historical = load_payload(state_path)
        historical_gamma = float(historical['gamma'])
        historical_anchor = historical['theta'].detach().clone()
    return dict(center=center, group=center_group(center), source_dir=directory,
                payload=payload, hashes=hashes, historical_gamma=historical_gamma,
                historical_anchor=historical_anchor)


def payload_residual(payload):
    return residual_from_payload(payload)


def state_objective(payload, theta0, gamma):
    """Unified Phase-2 Objective for the requested gamma; gamma=0 -> Route R."""
    theta0 = theta0.detach().clone()
    coordinate = payload['coordinate'].detach().clone()
    return Objective(payload_residual(payload), coordinate, theta0, gamma)


def residual_block_sizes(payload, residual):
    """Training-block layout as produced by stack_weighted_residuals."""
    points = payload['points']
    benchmark = payload['benchmark']
    if benchmark == 'multi':
        blocks = [('pde_u', points['pde_x'].numel()),
                  ('pde_v', points['pde_x'].numel()),
                  ('data_u', points['data_x'].numel()),
                  ('data_v', points['data_x'].numel()),
                  ('initial_u', points['initial_x'].numel()),
                  ('initial_v', points['initial_x'].numel()),
                  ('boundary_u', 2 * points['boundary_t'].numel()),
                  ('boundary_v', 2 * points['boundary_t'].numel())]
    else:
        blocks = [('pde', points['pde_x'].numel()),
                  ('data', points['data_x'].numel()),
                  ('initial', points['initial_x'].numel()),
                  ('boundary', 2 * points['boundary_t'].numel())]
    if sum(size for _, size in blocks) != int(residual.numel()):
        return None
    return blocks


def lambda_max_state_block(residual, theta, coordinate):
    """lambda_max(J_theta(theta)^T J_theta(theta)) over the theta block only."""
    J = torch.func.jacrev(lambda t: residual(t, coordinate))(theta.detach())
    J = J.detach().double()
    g = sym((J.T @ J).numpy())
    values = np.linalg.eigvalsh(g)
    return float(values[-1]), g, J.numpy()


class ProximalLeastSquaresObjective:
    """Fixed-reference proximal objective in residual-augmented form.

    0.5*||r_aug||^2 == 0.5*||r||^2 + 0.5*gamma*||theta-theta0||^2 exactly.
    theta0 is cloned at construction and never updated.
    """

    def __init__(self, residual_vector, coordinate, theta0, gamma):
        self.residual_vector = residual_vector
        self.coordinate = coordinate.detach().clone()
        self.theta0 = theta0.detach().clone()
        self.gamma = float(gamma)
        self.counts = dict(augmented=0, jacobian=0)

    def residual_augmented(self, theta):
        self.counts['augmented'] += 1
        physical = self.residual_vector(theta, self.coordinate)
        if self.gamma == 0.0:
            return physical
        proximal = math.sqrt(self.gamma) * (theta - self.theta0)
        return torch.cat((physical, proximal))

    def raw(self, theta):
        return self.residual_vector(theta, self.coordinate)


class ResidualEvaluator:
    """scipy-facing float64/CPU/1-thread residual and Jacobian adapters.

    Every call checks the shared Deadline, records the last completed iterate,
    never accumulates autograd graphs and converts non-finite values into a
    controlled failure instead of a silent NaN.
    """

    def __init__(self, residual, coordinate, theta0, gamma, deadline):
        self.residual = residual
        self.coordinate = coordinate.detach().clone()
        self.theta0 = theta0.detach().clone()
        self.gamma = float(gamma)
        self.deadline = deadline
        self.nfev = 0
        self.njev = 0
        self.last_x = None
        self.failure = None

    def augmented(self, theta):
        physical = self.residual(theta, self.coordinate)
        if self.gamma == 0.0:
            return physical
        return torch.cat((physical, math.sqrt(self.gamma) * (theta - self.theta0)))

    def fun_numpy(self, x):
        theta = torch.from_numpy(np.asarray(x, dtype=np.float64))
        try:
            with torch.enable_grad():
                value = self.augmented(theta)
            arr = value.detach().cpu().numpy().astype(np.float64, copy=False)
        except TimeoutError:
            raise
        except Exception as error:
            self.failure = dict(kind='residual_exception', reason=repr(error))
            raise SolverAbort('residual_exception', repr(error)) from error
        self.last_x = np.asarray(x, dtype=np.float64).copy()
        self.nfev += 1
        if self.deadline is not None:
            self.deadline.check()
        if not np.isfinite(arr).all():
            self.failure = dict(kind='nonfinite_residual', at_nfev=self.nfev)
            raise SolverAbort('nonfinite_residual', f'nfev={self.nfev}')
        return arr

    def jac_numpy(self, x):
        theta = torch.from_numpy(np.asarray(x, dtype=np.float64))
        try:
            with torch.enable_grad():
                J = torch.func.jacrev(lambda t: self.augmented(t))(theta)
            arr = J.detach().cpu().numpy().astype(np.float64, copy=False)
        except TimeoutError:
            raise
        except Exception as error:
            self.failure = dict(kind='jacobian_exception', reason=repr(error))
            raise SolverAbort('jacobian_exception', repr(error)) from error
        self.njev += 1
        if self.deadline is not None:
            self.deadline.check()
        if not np.isfinite(arr).all():
            self.failure = dict(kind='nonfinite_jacobian', at_njev=self.njev)
            raise SolverAbort('nonfinite_jacobian', f'njev={self.njev}')
        return arr


def hash_tree(paths, excluded_suffixes=('.pyc',), excluded_dirs=('__pycache__',)):
    """SHA256 every file under the given repo-relative paths or glob patterns."""
    records = {}
    for pattern in paths:
        base = ROOT / pattern
        matches = sorted(ROOT.glob(pattern)) if any(ch in pattern for ch in '*?[') else [base]
        if not matches:
            records[str(Path(pattern).as_posix())] = dict(status='MISSING')
            continue
        for item in matches:
            if not item.exists():
                records[str(Path(pattern).as_posix())] = dict(status='MISSING')
                continue
            if item.is_file():
                records[item.relative_to(ROOT).as_posix()] = sha256_file(item)
                continue
            for path in sorted(item.rglob('*')):
                if not path.is_file():
                    continue
                if path.suffix in excluded_suffixes:
                    continue
                if any(part in excluded_dirs for part in path.parts):
                    continue
                records[path.relative_to(ROOT).as_posix()] = sha256_file(path)
    return records
