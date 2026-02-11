# Ship Closed Loop

Treat the user input as the requirement. If wrapped in <requirement>, use that block as source of truth.

0) If SPEC.md / CONTRACT.md / ACCEPTANCE.md are missing or placeholders, derive them from the requirement and write the files.
   - SPEC: goals, non-goals, constraints, risks, dependencies, rollout/rollback.
   - CONTRACT: API/schema/events/permissions/errors with examples and edge cases.
   - ACCEPTANCE: BDD scenarios + negative/edge cases + performance/SLO checks.
1) Generate or update TASK_MATRIX.yaml with orthogonal atomic tasks + dependencies.
2) Execute the matrix: spawn one worker per ready cell; enforce touch_scope and done_checks.
3) Integrate results, run release/validation steps, and update docs/runbook as needed.
4) Stop only when all checks pass; report remaining risks.

Use collab tools (spawn_agent, wait, send_input, close_agent) to maximize parallelism.
