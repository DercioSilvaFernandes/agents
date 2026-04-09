# AGENTS.md

## Repo Purpose
This task folder exists to make Psi0 inference on Isaac Sim repeatable, inspectable, and operator-friendly on the validated remote instance.

When a task-specific markdown file exists under `current_task/`, treat it as the mission-specific source of truth.
Keep remediation logs updated during the work, not after the fact.

## Remote Access Requirements
- Target instance for this task: `108.129.215.209`
- Verified SSH alias: `smartinterp-108-129-215-209`
- Verified SSH user: `ec2-user`
- Verified access path: `ssh smartinterp-108-129-215-209`
- SSH identity file from local config: `~/.ssh/smartinterp-108-129-215-209.pem`
- Verified GPU on host: `NVIDIA A10G`
- Active ECS workspace container during setup: `ecs-dm-interactive-shell-237-workspace-ec9cf59d96c397887500`

Discover the active runtime first before making assumptions about paths:

```bash
ssh smartinterp-108-129-215-209 \
  'docker ps --format "{{.Names}} {{.Image}} {{.Status}}"'
```

## Core Operating Principles
- Act like an operator, not a note-taker.
- Prefer discovery before mutation.
- Validate live commands on the target host instead of relying on README text alone.
- Keep changes scoped to the Psi0 plus Isaac Sim inference path.
- Do not claim success from a served endpoint alone; prove end-to-end evaluation reaches the simulator path.
- Preserve any existing running workloads unless the mission requires replacing them.

## Task-Specific Rules
- The upstream target repo is `https://github.com/physical-superintelligence-lab/Psi0`.
- Upstream README states Psi0 simulation uses SIMPLE, described as MuJoCo physics plus Isaac Sim rendering.
- Upstream README currently leaves `Install SIMPLE` marked as `Coming soon`; this task must capture the real install and launch path discovered on the target environment.
- Treat `serve_psi0` plus the SIMPLE evaluation client with `--sim-mode=mujoco_isaac` as the minimum inference path to validate.
- Prefer running inside the active ECS workspace container unless discovery proves the required Isaac Sim components live elsewhere on the host.
- Record checkpoint sources, dataset sources, ports, and environment variables explicitly once discovered.

## Logging Rules
Record every meaningful action in both remediation logs:
- timestamp
- exact command run or file changed
- reason
- result
- success or failure
- whether the action was live-only or persistent

## Validation Standard
Do not mark this task complete until the validated scope is explicit:
- SSH access works to the target instance
- active workspace container is identified
- Psi0 repo is present and its Python environment imports successfully
- model serving starts and `curl http://localhost:22085/health` succeeds from the execution environment
- SIMPLE evaluation client runs with `--sim-mode=mujoco_isaac`
- inference produces rollout artifacts or videos under the expected eval output path
- any Isaac Sim display or headless requirements are documented with the exact working command

If only partial validation is achieved, state the exact boundary directly.
