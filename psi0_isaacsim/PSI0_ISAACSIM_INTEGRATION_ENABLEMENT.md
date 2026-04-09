# Psi0 IsaacSim Integration Enablement

## Objective
Create an operator-ready task folder for getting Psi0 inference working on Isaac Sim from the upstream repository `physical-superintelligence-lab/Psi0`.

This mission is not complete when the repo merely clones or trains. The required outcome is a validated inference path that serves a Psi0 checkpoint and runs the Isaac Sim evaluation flow successfully.

## Primary Targets
- EC2 instance: `108.129.215.209`
- SSH alias: `smartinterp-108-129-215-209`
- SSH user: `ec2-user`
- Active runtime discovered during setup: `ecs-dm-interactive-shell-237-workspace-ec9cf59d96c397887500`
- Upstream repo: `https://github.com/physical-superintelligence-lab/Psi0`
- Primary model serve command from upstream:
  - `uv run --active --group psi --group serve serve_psi0 ...`
- Primary simulation evaluation mode from upstream:
  - SIMPLE eval client with `--sim-mode=mujoco_isaac`

## User Mission
Run Psi0 on Isaac Sim with inference working.

For this task, "inference working" means:
- a Psi0 checkpoint can be served successfully
- the evaluation client can connect to that server
- the simulator-backed rollout executes through the Isaac Sim path
- outputs are produced and can be inspected

## Important Upstream Context
The upstream README provides a partial simulation path:
- SIMPLE is the benchmarking simulator used for Psi0 and baselines
- SIMPLE is described as using MuJoCo physics and Isaac Sim rendering
- the README documents serving Psi0 and running the eval client with `--sim-mode=mujoco_isaac`
- the README still marks `Install SIMPLE` as `Coming soon`

That means this task must close the gap between the partial upstream guide and a live, reproducible execution path on the target machine.

## Capabilities In Scope
This folder must document and support:
- safe SSH access to the target instance
- discovery of the active ECS workspace container and any mounted workspaces
- Psi0 repo setup with `uv`
- acquisition or identification of checkpoints and evaluation data
- model serving on a known host and port
- SIMPLE evaluation in `mujoco_isaac` mode
- Isaac Sim display or headless execution requirements
- collection of rollout outputs, logs, and failure signatures

## Explicit Completion Criteria
Minimum success for this mission:
- task folder exists with the standard five files
- runbook contains a real step-by-step path for repo setup, serving, and Isaac Sim evaluation
- remediation logs are ready to capture live work

Full mission success:
- Psi0 environment imports correctly on the target runtime
- a concrete checkpoint is served successfully
- health checks succeed on the serving endpoint
- the SIMPLE evaluation client completes at least one rollout in `mujoco_isaac` mode
- output artifacts are generated in the expected evaluation directory
- unresolved blockers, if any, are narrowed to a specific external dependency instead of an unknown failure

## Preconditions
- SSH access via `smartinterp-108-129-215-209` remains available
- the active ECS workspace container remains available or a replacement container can be discovered
- GPU access remains available on the execution environment
- enough disk space exists for repo dependencies, checkpoints, datasets, and simulator assets
- the required Psi0 checkpoint and SIMPLE task data are accessible

## Required Artifacts
- `agents/psi0_isaacsim/AGENTS.md`
- `agents/psi0_isaacsim/PSI0_ISAACSIM_INTEGRATION_ENABLEMENT.md`
- `agents/psi0_isaacsim/PSI0_ISAACSIM_WORKING_RUNBOOK.md`
- `agents/psi0_isaacsim/PSI0_ISAACSIM_REMEDIATION_LOG.md`
- `agents/psi0_isaacsim/current_task/PSI0_ISAACSIM_REMEDIATION_LOG.md`
