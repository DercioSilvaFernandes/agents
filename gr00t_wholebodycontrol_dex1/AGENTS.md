# AGENTS.md

## Repo Purpose
This task folder exists to make the `GR00T-WholeBodyControl-dex1` G1 workflow repeatable on the fixed EC2 instance and to separate validated simulator actuation from guesswork.

When a task-specific markdown file exists under `current_task/`, treat it as the mission-specific source of truth.
Keep both remediation logs updated during work, not only after the fact.

## Remote Access Requirements
- Target instance: `54.155.29.100`
- SSH user: `ec2-user`
- SSH key: `/Users/dercio.fernandes/dm-isaac-g1.pem`
- Validated access path:

```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100
```

- Active runtime is inside the ECS workspace container, not on the EC2 host filesystem.
- Discover the live container first:

```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100 \
  'docker ps --format "{{.Names}} {{.Status}}"'
```

Validated container during this session:
- `ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901`

## Core Operating Principles
- Act like an operator, not a note-taker.
- Prefer the official NVIDIA G1 WBC example path unless the live container disproves it.
- Do not claim success from imports or model download alone.
- Treat simulator actuation as the acceptance test, not simulator startup.
- Keep live-only compatibility fixes explicit when they are required to make the stack run.

## Task-Specific Rules
- Do not use `./run.sh` wrappers for this task.
- Use `unitree_sim_env` for the GR00T + MuJoCo + RoboCasa validation path.
- The validated G1 model for this task is `nvidia/GR00T-N1.6-G1-PnPAppleToPlate`.
- The validated environment ID is `gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc`.
- The local `GR00T-WholeBodyControl-dex1` checkout required live compatibility fixes for Python 3.11 and package naming before the WBC env could run.

## Logging Rules
Record every meaningful action in both remediation logs:
- timestamp
- exact command run or file changed
- reason
- result
- whether the change was live-only or persisted in this repo

## Validation Standard
Do not mark this task complete unless all of the following are true:
- the remote container can build the `gr00tlocomanip_g1_sim/..._gear_wbc` env
- the selected GR00T model loads successfully
- a closed-loop policy step executes against the WBC env
- post-step joint values change in the simulator

This task was considered complete only after the validated probe produced:
- `joint_delta_norm 0.49687227606773376`
- `joint_delta_max_abs 0.2770960330963135`
- `joint_delta_nonzero 41`
