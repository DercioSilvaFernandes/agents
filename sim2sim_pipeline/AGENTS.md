# AGENTS.md

## Repo Purpose
This task folder exists to make the G1 sim2sim deployment path on the remote instance repeatable, inspectable, and safe to operate without restarting the machine.

When a task-specific markdown file exists under `current_task/`, treat it as the mission-specific source of truth.
Keep remediation logs updated during work, not only after the fact.

## Remote Access Requirements
- Target instance for this task: `54.155.29.100`
- Verified SSH user: `ec2-user`
- Verified access path: `ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100`
- Do not restart, stop, or recreate the instance during this task.
- Do not rely on password-based SSH in tracked instructions. On the validated host, password auth is disabled; key-based SSH works.

The sim2sim runtime is not on the EC2 host directly. It runs inside the active ECS workspace container. Discover it first:

```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100 \
  'docker ps --format "{{.Names}} {{.Status}}"'
```

Validated container during this session:
- `ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901`

## Core Operating Principles
- Act like an operator, not a note-taker.
- Prefer discovery before mutation.
- Keep fixes scoped to the sim2sim workflow.
- Do not claim success from docs alone; validate the actual remote commands.
- Separate startup validation from full mimic-policy validation.
- Do not change policy scripts unless the mission explicitly requires it.

## Task-Specific Rules
- The operator-provided logic mentions `conda activate env_isaaclab`, but this validated container exposes `base`, `gmr`, `phmr`, and `unitree_sim_env`.
- For simulator and controller startup, the C++ binaries do not require activating a Python env first.
- `unitree_mujoco` requires an X display inside the container. Export `DISPLAY=:1` before launching it over SSH.
- Both `unitree_mujoco` and `g1_ctrl` must use loopback DDS for this task. Export `CYCLONEDDS_URI=file:///tmp/cyclonedds.xml` and use `--network lo`.

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
- Startup scope:
  - SSH access works
  - active container identified
  - `unitree_mujoco` launches on `DISPLAY=:1`
  - `g1_ctrl --network lo` launches in the same container
- Full sim2sim scope:
  - policy folder added under `config/policy/mimic/<task_name>/`
  - `config.yaml` updated with the new policy ID and references
  - policy trigger script runs
  - motion plays in sim2sim

If only startup scope is validated, say so directly.
