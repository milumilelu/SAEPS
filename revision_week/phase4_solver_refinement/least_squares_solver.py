"""Staged scipy least_squares (TRF, exact dense, x_scale='jac', linear loss).

scipy 1.15.3 least_squares has no callback, so every stage runs bounded
max_nfev chunks with repository-side gate checks between chunks. Stopping is
only by frozen protocol gates or recorded budgets; no silent retries.
"""
from __future__ import annotations
import time
import numpy as np
import torch

from objective_adapter import SolverAbort


def normalized_gradient(gradient_sum, theta, m):
    """||grad L_sum|| / (m * max(||theta||, 1)) with m the residual count."""
    theta = theta.detach().cpu().numpy()
    return float(np.linalg.norm(gradient_sum) / (m * max(float(np.linalg.norm(theta)), 1.0)))


class StageDeadline:
    """Hard deadline = min(task deadline, stage wall cap); checked inside evaluations."""

    def __init__(self, task_deadline, stage_end):
        self.task_deadline = task_deadline
        self.stage_end = stage_end

    def check(self):
        import time as _time
        if _time.perf_counter() >= self.stage_end:
            raise TimeoutError('stage_budget_exhausted')
        if self.task_deadline is not None:
            self.task_deadline.check()

    def remaining(self):
        import time as _time
        left = self.stage_end - _time.perf_counter()
        if self.task_deadline is not None:
            left = min(left, self.task_deadline.remaining())
        return max(0.0, left)


def solve_stage(ev, x0, target, obj, stage_name, deadline, wall_cap, nfev_pool, chunk_nfev, tol):
    """Run one polish stage; returns a full record including per-chunk rows.

    The stage wall cap is enforced inside every residual/Jacobian evaluation via
    a composite deadline, so a chunk cannot overrun the stage or task budget.
    """
    x = np.asarray(x0, dtype=np.float64).copy()
    started = time.perf_counter()
    stage_deadline = StageDeadline(deadline, started + float(wall_cap))
    original_deadline = ev.deadline
    ev.deadline = stage_deadline
    rows = []
    nfev_used = 0
    njev_used = 0
    target_reached = False
    last_gate = None
    termination = None
    scipy_stop = None
    try:
        while True:
            elapsed = time.perf_counter() - started
            wall_left = stage_deadline.remaining()
            nfev_left = nfev_pool - nfev_used
            if wall_left <= 0.0:
                termination = 'wall_budget_exhausted'
                break
            if nfev_left <= 0:
                termination = 'nfev_budget_exhausted'
                break
            max_nfev = int(min(chunk_nfev, nfev_left))
            try:
                out = _run_least_squares(ev, x, max_nfev, tol)
            except TimeoutError:
                termination = 'wall_budget_exhausted'
                if ev.last_x is not None:
                    x = np.asarray(ev.last_x, dtype=np.float64).copy()
                break
            except SolverAbort as abort:
                termination = abort.kind
                if ev.last_x is not None:
                    x = np.asarray(ev.last_x, dtype=np.float64).copy()
                break
            x = np.asarray(out['x'], dtype=np.float64).copy()
            nfev_used += int(out['nfev'])
            njev_used += int(out['njev'])
            try:
                gate = _gate_row(obj, x, stage_name, nfev_used, njev_used,
                                 time.perf_counter() - started, out)
            except TimeoutError:
                termination = 'wall_budget_exhausted'
                break
            last_gate = gate
            rows.append(gate)
            if gate['normalized_gradient'] <= target:
                target_reached = True
                if out['status'] != 0:
                    scipy_stop = dict(status=int(out['status']), message=str(out['message']))
                break
            if out['status'] != 0:
                scipy_stop = dict(status=int(out['status']), message=str(out['message']))
                termination = f'scipy_stop_status_{out["status"]}'
                break
    finally:
        ev.deadline = original_deadline
    if termination is None and not target_reached:
        termination = 'unknown'
    seconds = time.perf_counter() - started
    return dict(x=x, target_reached=target_reached, termination=termination,
                scipy_stop=scipy_stop, rows=rows, seconds=seconds,
                nfev_used=nfev_used, njev_used=njev_used, last_gate=last_gate,
                stage_wall_cap=float(wall_cap))


def _run_least_squares(ev, x, max_nfev, tol):
    from scipy.optimize import least_squares
    out = least_squares(ev.fun_numpy, x, jac=ev.jac_numpy, method='trf',
                        tr_solver='exact', x_scale='jac', loss='linear',
                        ftol=tol, xtol=tol, gtol=tol, max_nfev=max_nfev)
    return dict(x=np.asarray(out.x, dtype=np.float64), nfev=int(out.nfev), njev=int(out.njev),
                cost=float(out.cost), optimality=float(out.optimality),
                status=int(out.status), success=bool(out.success), message=str(out.message))


def _gate_row(obj, x, stage_name, nfev_cum, njev_cum, seconds, out):
    theta = torch.from_numpy(x.copy())
    gradient = obj.grad(theta)
    normalized = normalized_gradient(gradient, theta, obj.m)
    return dict(stage=stage_name, nfev_cum=nfev_cum, njev_cum=njev_cum, seconds=seconds,
                normalized_gradient=normalized, loss=obj.value(theta),
                scipy_status=int(out['status']), scipy_success=bool(out['success']),
                scipy_message=str(out['message']),
                scipy_cost=float(out['cost']), scipy_optimality=float(out['optimality']))
