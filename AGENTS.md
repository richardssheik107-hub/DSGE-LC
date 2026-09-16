# Research-agent operating rules

Read docs/CURRENT_STATUS.md, the latest audit, and docs/plans/correction_backlog.md before acting. Old phase PASS records do not override newly confirmed defects. Main model is monthly semi-structural M0_CORE5, not a complete DSGE or implemented mixed-frequency model.

## Work discipline

- Respect the user's current access scope. This audit switched to GitHub-only; do not reconnect a Windows device without renewed instruction.
- Check latest remote main; no force push, hard reset, broad git add, or deletion of unexplained untracked work.
- Earlier local MCMC/test edits may remain uncommitted: inspect and preserve differences before synchronization.
- Keep original observations, posterior draws, configs, outputs and historical phase memos traceable. New corrections need new audit/version records.
- Never turn a numerical bug into PASS_WITH_WARNING. Distinguish implementation validity, convergence, statistical evidence, economic interpretation and submission readiness.
- No MCMC rerun for a presentation/diagnostic fix unless stored draws actually fail corrected diagnostics. Missing artifacts are not permission to reconstruct silently.
- No result beautification: do not tune sample, priors, fixed parameters, roll rules or thresholds to get attractive signs/rankings.
- Raw proprietary data, full reference manuscripts, credentials, posterior arrays and large generated outputs remain private. Publicly viewable is not automatically redistributable.
- Any new model/measurement/scaler/diagnostic definition has a separate version; changing state units changes parameter interpretation.
- Report tests as actually executed: portable, synthetic, authorized integration and long experiments separately. Missing inputs/SKIP do not establish PASS.
- Complete a stage by recording result review, remaining warnings and plan, then explicit staging/commit/push and remote verification when authorized.
- Do not claim future/background work continues unless a supported scheduled tool has actually created it.

## Current priority

A01—A04 before additional modeling. The independent checker is scripts/audit_posterior_independent.py; it reads stored artifacts only. See docs/REPRODUCIBILITY.md for dependencies and limitations.
