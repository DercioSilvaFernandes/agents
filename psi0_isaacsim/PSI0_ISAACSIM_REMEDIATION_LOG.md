# Psi0 IsaacSim Remediation Log

## Purpose
Chronological record of all actions taken to get Psi0 inference working on Isaac Sim.

## Chronological Entries

### 2026-04-08 14:58 WEST
- Action: Created the standard task folder `agents/psi0_isaacsim/` with `AGENTS.md`, integration enablement, working runbook, and both remediation logs.
- Reason: Establish an operator-ready workspace for the Psi0 on Isaac Sim mission.
- Result: Persistent task structure created and seeded with the current target host and upstream execution path.

### 2026-04-08 14:58 WEST
- Commands:
  - `ssh -o BatchMode=yes -o ConnectTimeout=10 smartinterp-108-129-215-209 'hostname && whoami && pwd'`
  - `ssh smartinterp-108-129-215-209 'hostname; uname -a; nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || true'`
  - `ssh smartinterp-108-129-215-209 'docker ps --format "{{.Names}} {{.Image}} {{.Status}}" || true'`
- Reason: Capture the validated execution target for the new task folder.
- Result:
  - SSH access verified as `ec2-user`
  - host identified as `ip-172-31-43-127.eu-west-1.compute.internal`
  - GPU identified as `NVIDIA A10G`
  - active workspace container identified as `ecs-dm-interactive-shell-237-workspace-ec9cf59d96c397887500`

### 2026-04-08 14:58 WEST
- Source reviewed: `https://github.com/physical-superintelligence-lab/Psi0`
- Reason: Seed the runbook with the actual upstream serve and Isaac Sim evaluation flow.
- Result:
  - captured the documented `serve_psi0` command pattern
  - captured the documented SIMPLE eval command with `--sim-mode=mujoco_isaac`
  - noted that upstream `Install SIMPLE` instructions are still incomplete and must be resolved during execution

### 2026-04-08 15:22 WEST
- Actions:
  - cloned `https://github.com/physical-superintelligence-lab/Psi0.git` into `/workspace/Psi0` inside container `ecs-dm-interactive-shell-237-workspace-ec9cf59d96c397887500`
  - validated Python `3.10.20` availability from the existing `gmr` conda env
  - created `/workspace/Psi0/.venv-psi`
  - ran `GIT_LFS_SKIP_SMUDGE=1 uv sync --group psi --group serve --index-strategy unsafe-best-match --active`
- Reason: Build a runnable Psi0 serve environment on the target instance.
- Result:
  - Psi0 environment installed successfully, including `torch`, `transformers`, `deepspeed`, `flash-attn`, and the editable `psi` package
  - CUDA remained available to the venv on `NVIDIA A10G`

### 2026-04-08 15:22 WEST
- Actions:
  - attempted `git submodule update --init --recursive third_party/SIMPLE`
  - inspected `examples/simple/README.md` and `examples/simple/simple_eval.py`
- Reason: Try to activate the official Isaac Sim evaluation path.
- Result:
  - submodule fetch failed because `third_party/SIMPLE` points to `git@github.com:songlin/SIMPLE.git`
  - the active machine does not have the required access path for that repo
  - no reusable `simple` Python package was present elsewhere in the workspace
  - official Isaac-backed evaluation remains blocked on SIMPLE availability

### 2026-04-08 15:22 WEST
- Actions:
  - queried the public Hugging Face model index for `USC-PSI-Lab/psi-model`
  - confirmed there are no public `psi0` SIMPLE run directories in that model repo
  - identified a public serveable run directory at `psi0/real-checkpoints/task1`
  - downloaded `argv.txt`, `run_config.json`, and `checkpoints/ckpt_40000/model.safetensors`
  - staged the artifact as `/workspace/Psi0/.cache/runs/psi0_real_task1`
- Reason: Prove the Psi0 inference boundary with a public artifact even though SIMPLE is unavailable.
- Result:
  - public run artifact downloaded successfully
  - serve-compatible run directory assembled locally inside the container

### 2026-04-08 15:22 WEST
- Actions:
  - created `.env` from `.env.sample`
  - rewired `PSI_HOME`, `DATA_HOME`, `HF_HOME`, `TORCH_HOME`, `UV_CACHE_DIR`, and `HF_LEROBOT_HOME` into `/workspace/Psi0/.cache/...`
  - launched:
    - `python -m psi.deploy.psi0_serve_simple --host 0.0.0.0 --port 22085 --policy psi0 --run-dir /workspace/Psi0/.cache/runs/psi0_real_task1 --ckpt-step 40000 --device cuda:0 --rtc`
  - captured logs in `/tmp/psi0_task1.log`
- Reason: Validate a live Psi0 inference server on the target instance.
- Result:
  - model loaded successfully
  - `curl http://127.0.0.1:22085/health` returned `{"status":"ok"}`
  - a serialized `/act` request returned HTTP `200` with an action payload
  - validated server process remained alive as PID `1836`

### 2026-04-08 15:22 WEST
- Current validated boundary:
  - Psi0 inference is working on the target instance at the HTTP server layer
  - the live server currently runs inside the active ECS workspace container on port `22085`
  - the official Isaac Sim evaluation path is still blocked because the required `third_party/SIMPLE` repo is unavailable on this machine
- Remaining gap to full task completion:
  - obtain or install a working SIMPLE checkout on the instance
  - obtain a public or private Psi0 checkpoint intended for SIMPLE evaluation, or explicitly accept testing Isaac with the real-task checkpoint
  - run the SIMPLE client in `mujoco_isaac` mode and collect rollout artifacts

### 2026-04-08 15:47 WEST
- Actions:
  - created `scripts/eval/run_psi0_g1_mujoco.py` in `dm-isaac-g1`
  - upgraded `PyOpenGL` in `unitree_sim_env` from `3.1.0` to `3.1.7` and installed `PyOpenGL-accelerate` to repair MuJoCo EGL rendering
  - used the public Psi0 server on `http://127.0.0.1:22085/act`
  - ran the bridge script against `/workspace/Psi0/real/assets/g1/g1_body29_hand14.xml`
  - generated rollout artifacts under `/tmp/psi0_g1_mujoco_run3`
- Reason: Validate a direct Psi0-to-MuJoCo G1 path without depending on SIMPLE or Isaac Sim.
- Result:
  - MuJoCo rollout succeeded in stable `kinematic` mode with `fixed_base=true` and `zero_gravity=true`
  - Psi0 served a fresh `POST /act` request and returned an action chunk of shape `(30, 36)`
  - rollout video written to `/tmp/psi0_g1_mujoco_run3/psi0_g1_mujoco_ego.mp4`
  - summary and trace written to `/tmp/psi0_g1_mujoco_run3/{summary.json,trace.json}`
- Current limitation:
  - full dynamic torque-driven whole-body physics is still unstable with this public real-task checkpoint and the naive PD bridge
  - the working validated boundary is a MuJoCo kinematic rollout of the G1 asset driven by live Psi0 inference
