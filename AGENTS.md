# Active instructions: capacity/storage theory candidate

Effective 2026-09-19. User explicitly authorised the two necessary theoretical expansions before experiments: capacity investment with construction delay and endogenous storage. They are now derived and locally solved, not empirically estimated. Do not resume old M0 patches or add optional trade/recycling/futures/mixed-frequency mechanisms by default.

Read docs/CURRENT_STATUS.md, docs/rebuild/MASTER_PLAN.md, configs/masters_rebuild_plan_v1.json, and docs/rebuild/two_step_v1/{EQUATIONS,STATE_SPACE,SOURCES,VALIDATION}. Current model ID is RB_CAPACITY_STORAGE_V1. NEXT_WORK_PACKAGE.md is now scope/measurement/identification discussion, not another instruction to start deriving the same two modules.

## Scientific boundaries

26 numbered groups are not 26 independent equations. Interior sequence count is L+8, memory state dimension L+4; the two-period six-state fixture is purely synthetic, NOT lithium construction-time evidence. Price, material output and capacity shadow value are equilibrium outputs. No arbitrary new investment/inventory AR innovations.

The new producer replaces the single-period FOC and gQ^2 cost with intertemporal Q/J decisions and gamma Q^2/(2K). Endogenous storage replaces given-J E24; old C0 closed-form price does not apply. Log inventory service is an explicit own assumption informed by operational storage theory. A no-service positive-cost deterministic reference cannot support positive interior stock; do not silently set service to zero while retaining the interior solver.

The potential formulation requires price-taking, common beta/expectations, no unaccounted wedges and fixed outside flows. Riccati solves a first-order INTERIOR approximation, not a global constrained model or a fitted state matrix. Never drop future expectation terms, clip invalid levels to claim equilibrium, or confuse deterministic reference with stochastic mean. Inactive capacity must still have a documented productive role if claiming positive investment.

## What is permitted next

Supervisor discussion, source/engineering checks, product and observation mapping, local/nonlinear feasibility investigation, parameter identification and synthetic recovery. Formal real-data estimation remains blocked until actual supervisor scope evidence AND technical/protocol gates. Draft-ready does not mean sent or approved. Do not promise later estimation must be quick. Long master's structure is flexible; no fixed chapter or equation count.

## Preserve and separate

New theoretical code lives in src/rebuild_theory. Preserve existing data, src/structural, src/theory_audit, priors/posteriors and R1/R2/R3 records. New model IDs, observation transformations and results are separate; never relabel old draws. Old A/D/phase ledgers are historical, not current queues. Fixed predecessor is df0e66dcb57eae5e326168a059c3010492d94670; full pre-rebuild c6a61b72e1c21acb042be47b13c6138854c8d8df remains accessible.

LC grades, LC/LiOH/LCE, ore/finished imports, installation/manufacturing/use, annual capacity/monthly output differ. Same-source I and differenced J are not independent measurements. No double-counted recycled output. Sources motivate mechanisms, not industry parameter values or unsupported causal claims.

## Execution

GitHub-only chat: do not reconnect Windows. Preserve unknown local changes. No hard reset, force push, broad git add, untracked deletion, credentials, proprietary data, original papers or private outputs committed. Archive/supersede conflicting instructions rather than erase history.

Actual current tests: PYTHONPATH=. python -m pytest -q tests/test_capacity_storage_v1.py; python scripts/check_capacity_storage_v1.py. Report only executed commands and scope, never add historical counts. Update explicit paths, compare diff, fast-forward only and verify remote head/protected objects. No claiming full checkout, private hashes, parameter recovery, estimation, advisor or school acceptance without evidence.
