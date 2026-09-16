# Phase 2 numerical execution

Run from the SO worktree using the declared Python environment:

```powershell
& 'C:/Users/RZF/Desktop/博士课题资料/SAEPS/.venv/Scripts/python.exe' revision_week/phase2/run_all.py --spec revision_week/protocols/phase2/phase2_spec.json --run-id phase2_v1
```

This command acquires an OS mutex, verifies committed-code development runs,
freezes all future groups and handlers, commits and synchronizes the lock, then
executes every eligible node. It retains scientific stops and failed numerical
runs in their planned denominators. It never replaces a seed or automatically
restarts a partially trained seed. An interrupted dead worker is charged its
reserved time as a clearly labelled conservative estimate; a live PID blocks a
second launch.

The Phase 2 run-manifest namespace is
`revision_week/outputs/phase2_v1/run_manifests/`. The old `outputs/runs` tree has
an immutable V5 inventory, so no new experiment is inserted into that historical
tree and no historical validation rule is weakened. All Phase 2 aggregation
reads its own manifests and verifies raw-file hashes.

Initial numbered `dev*` runs are engineering debugging evidence, including
failures and their actual wall times. Their uncommitted source hashes do not
constitute release provenance. The separately named `verified01` runs use a
committed executable and are the final development acceptance source before
the independent seed lock. Repeating these historical development checks does
not create independent confirmation evidence.

CG remains zero-start, unpreconditioned, tolerance 1e-10, at most 500 iterations,
with acceptance residual 1e-8. Two A-conjugacy reorthogonalization passes and a
true residual each iteration address observed loss of conjugacy. This stores
Krylov vectors; it never constructs the state Jacobian or Hessian. All normal
operator calls are charged. No accuracy claim is made from function-preserving
large-network widening.

An exactly stationary point is accepted only after two explicit same-state
gradient/SPD/zero-displacement plateau revalidations. Root refinement uses the
unanchored loss; gamma is fixed once at its endpoint, and the final gate checks
the anchored A separately. Branch distance/radius uses the fixed anchor norm.

Plotting dependencies are isolated in `requirements-plotting.txt`. Scientific
solvers retain the existing numpy/torch versions. All generated numerical prose,
tables and figures read the same manifest-derived records.

The user explicitly authorized continued pushes to the currently public
`milumilelu/SAEPS` repository after visibility was checked in this session.
Synchronization uses fast-forward atomic pushes to main and the experiment
branch; no force push or modification of the unrelated original worktree.
