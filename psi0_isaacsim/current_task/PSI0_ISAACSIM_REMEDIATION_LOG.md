# PSI0_ISAACSIM Current Task Remediation Log

Reference: follow `agents/psi0_isaacsim/AGENTS.md` as the operating source of truth for this task.

## Active Scope
- Set up the standard task folder for Psi0 on Isaac Sim
- Use the validated instance `108.129.215.209` as the initial target
- Capture the upstream Psi0 serve and SIMPLE eval path
- Prepare the workspace for live inference validation in a later execution session

## Current Working Snapshot
- SSH access works via `ssh smartinterp-108-129-215-209`
- verified user: `ec2-user`
- host GPU: `NVIDIA A10G`
- active container at folder creation time: `ecs-dm-interactive-shell-237-workspace-ec9cf59d96c397887500`
- upstream target repo: `https://github.com/physical-superintelligence-lab/Psi0`
- upstream documented inference path:
  - serve Psi0 with `serve_psi0` on port `22085`
  - run SIMPLE eval client with `--sim-mode=mujoco_isaac`
- known documentation gap:
  - upstream `Install SIMPLE` section is still marked `Coming soon`

## Chronological Entries

### 2026-04-08 14:58 WEST
- Action: Created task folder files under `agents/psi0_isaacsim/`.
- Result: Standard task structure is in place and ready for live execution logging.

### 2026-04-08 14:58 WEST
- Action: Recorded the validated SSH alias, host, GPU, and active ECS container in the task documents.
- Result: Operator docs now target the real current environment instead of placeholders.

### 2026-04-08 14:58 WEST
- Action: Seeded the runbook with the upstream Psi0 serve flow and the SIMPLE Isaac Sim evaluation command.
- Result: The task now has a concrete starting path for live inference validation, with the main unresolved gap explicitly called out.

### 2026-04-08 15:22 WEST
- Actions:
  - cloned `/workspace/Psi0` on `108.129.215.209`
  - created `.venv-psi` with Python `3.10.20` from the existing `gmr` conda env
  - installed Psi0 serve dependencies with `uv sync --group psi --group serve --active`
- Result:
  - Psi0 runtime environment is present and importable on the remote container

### 2026-04-08 15:22 WEST
- Actions:
  - attempted to initialize `third_party/SIMPLE`
  - confirmed the submodule URL is `git@github.com:songlin/SIMPLE.git`
  - checked for an existing `simple` package in the workspace and found none
- Result:
  - Isaac-backed evaluation is blocked by missing SIMPLE access on this machine

### 2026-04-08 15:22 WEST
- Actions:
  - inspected the public `USC-PSI-Lab/psi-model` file index
  - found no public `psi0` SIMPLE run directories
  - downloaded the public real-task run artifact `psi0/real-checkpoints/task1`
  - staged it as `/workspace/Psi0/.cache/runs/psi0_real_task1`
- Result:
  - a serveable public Psi0 run directory is now available on the remote machine

### 2026-04-08 15:22 WEST
- Actions:
  - normalized `.env` cache roots into `/workspace/Psi0/.cache/...`
  - launched the server on port `22085`
  - verified `/health`
  - sent a minimal serialized `/act` request using the repo's `RequestMessage` helper
- Result:
  - live server is running as PID `1836`
  - `GET /health` returns `{"status":"ok"}`
  - `POST /act` returns HTTP `200` with an action tensor payload

## Current Status
- Working now:
  - Psi0 serving and HTTP inference on the target instance
  - direct Psi0-driven MuJoCo rollout for the G1 asset in stable kinematic mode
- Not yet working:
  - official SIMPLE Isaac Sim evaluation
  - dynamic torque-driven MuJoCo whole-body control with this public checkpoint
- Exact blocker:
  - `third_party/SIMPLE` is not accessible from this machine through the configured upstream submodule path

## Latest Execution

### 2026-04-08 15:47 WEST
- Actions:
  - created `/workspace/dm-isaac-g1/scripts/eval/run_psi0_g1_mujoco.py`
  - repaired MuJoCo EGL rendering in `unitree_sim_env` by upgrading `PyOpenGL` to `3.1.7` and installing `PyOpenGL-accelerate`
  - ran the bridge against `/workspace/Psi0/real/assets/g1/g1_body29_hand14.xml`
  - used the live Psi0 server at `http://127.0.0.1:22085/act`
- Result:
  - fresh `/act` call succeeded and returned `(30, 36)` actions
  - stable rollout completed in `kinematic` mode with `fixed_base=true` and `zero_gravity=true`
  - artifacts created at `/tmp/psi0_g1_mujoco_run3/`
  - verified video: `/tmp/psi0_g1_mujoco_run3/psi0_g1_mujoco_ego.mp4`
  - verified metadata: `/tmp/psi0_g1_mujoco_run3/summary.json` and `/tmp/psi0_g1_mujoco_run3/trace.json`
- Limitation:
  - dynamic MuJoCo stepping with naive PD on the public real-task checkpoint still becomes unstable, so the current validated path is kinematic playback driven by live Psi0 inference
