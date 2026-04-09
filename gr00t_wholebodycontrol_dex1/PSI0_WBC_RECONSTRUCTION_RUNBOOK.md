# Psi0 + GR00T WholeBodyControl Integration - Reconstruction Runbook

**Purpose**: Rebuild a working Psi0 -> WBC integration on a fresh ECS container.

**Validated on**: 2026-04-09, ECS interactive container on `3.250.72.142`

## Overview

This runbook wires together:
- Psi0 HTTP inference server (`/act` on `22085`)
- GR00T WholeBodyControl G1 MuJoCo env
- Psi0 policy wrapper (`psi0_wbc_policy.py`) and probe (`psi0_wbc_probe_validated.py`)

The sequence below is the path that actually worked.

## Phase 1: Connect + Discover Container

```bash
INSTANCE_IP="<your-instance-ip>"
SSH_USER="ec2-user"

ssh ${SSH_USER}@${INSTANCE_IP}

docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}'
# pick the ecs-dm-interactive-shell-* container
CONTAINER_NAME="<container-name>"
```

Verify base env:

```bash
docker exec ${CONTAINER_NAME} bash -lc '
  source /opt/conda/etc/profile.d/conda.sh
  conda activate unitree_sim_env
  python -c "import gymnasium, torch, mujoco; print(gymnasium.__version__, torch.__version__, mujoco.__version__)"
'
```

## Phase 2: Prepare WBC Runtime (Required)

### 2.1 Clone Required RoboSuite Branch

```bash
docker exec ${CONTAINER_NAME} bash -lc '
  if [ ! -d /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite/.git ]; then
    git clone --depth 1 --branch leo/support_g1_locomanip \
      https://github.com/xieleo5/robosuite.git \
      /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite
  fi
'
```

### 2.2 Apply Python 3.11 + Alias Patches

```bash
docker exec ${CONTAINER_NAME} python3 - <<'PY'
from pathlib import Path

visuals = Path('/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py')
configs = Path('/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/scene/configs.py')
sync = Path('/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/control/envs/robocasa/sync_env.py')
mink = Path('/opt/conda/envs/unitree_sim_env/lib/python3.11/site-packages/mink/tasks/exceptions.py')

vt = visuals.read_text()
vt = vt.replace('from dataclasses import dataclass\n', 'from dataclasses import dataclass, field\n')
vt = vt.replace('rgba_a: np.ndarray = np.array([0, 0, 0, 1])', 'rgba_a: np.ndarray = field(default_factory=lambda: np.array([0, 0, 0, 1]))')
vt = vt.replace('rgba_b: np.ndarray = np.array([1, 1, 1, 1])', 'rgba_b: np.ndarray = field(default_factory=lambda: np.array([1, 1, 1, 1]))')
visuals.write_text(vt)

ct = configs.read_text()
ct = ct.replace('from dataclasses import dataclass\n', 'from dataclasses import dataclass, field\n')
ct = ct.replace('x_range: np.ndarray = np.zeros(2)', 'x_range: np.ndarray = field(default_factory=lambda: np.zeros(2))')
ct = ct.replace('y_range: np.ndarray = np.zeros(2)', 'y_range: np.ndarray = field(default_factory=lambda: np.zeros(2))')
ct = ct.replace('rotation: np.ndarray = np.zeros(2)', 'rotation: np.ndarray = field(default_factory=lambda: np.zeros(2))')
ct = ct.replace('reference_pos: np.ndarray = np.zeros(3)', 'reference_pos: np.ndarray = field(default_factory=lambda: np.zeros(3))')
ct = ct.replace('sampler_config: SamplingConfig = SamplingConfig()', 'sampler_config: SamplingConfig = field(default_factory=SamplingConfig)')
configs.write_text(ct)

st = sync.read_text()
st = st.replace('sys.modules["decoupled_wbc.control.envs.robocasa.sync_env"]', 'sys.modules[__name__]')
st = st.replace('entry_point=f"decoupled_wbc.control.envs.robocasa.sync_env:{class_name}"', 'entry_point=f"{__name__}:{class_name}"')
sync.write_text(st)

mink.parent.mkdir(parents=True, exist_ok=True)
mink.write_text('# Compatibility shim for mink.tasks.exceptions\nfrom mink.exceptions import *\n')
print('patched')
PY
```

### 2.3 Install Required Dependency Pins

```bash
docker exec ${CONTAINER_NAME} bash -lc '
  source /opt/conda/etc/profile.d/conda.sh
  conda activate unitree_sim_env
  pip install --upgrade \
    mink \
    mujoco==3.2.6 \
    "PyOpenGL>=3.1.7" \
    numba==0.59.1 \
    coverage==7.4.4
'
```

### 2.4 Create Correct Alias + Validate Env Reset

Important: alias must point to `decoupled_wbc`, not repo root.

```bash
docker exec ${CONTAINER_NAME} bash -lc '
  rm -f /tmp/gr00t_wbc
  ln -s /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc /tmp/gr00t_wbc
'

docker exec ${CONTAINER_NAME} bash -lc '
  export PYTHONPATH=/tmp:/workspace/GR00T-WholeBodyControl-dex1:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite:$PYTHONPATH
  export MUJOCO_GL=egl
  export PYOPENGL_PLATFORM=egl
  source /opt/conda/etc/profile.d/conda.sh
  conda activate unitree_sim_env
  python - <<EOF
import gymnasium as gym
import gr00t_wbc.control.envs.robocasa.sync_env
env = gym.make(
  "gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc",
  onscreen=False, offscreen=True, enable_waist=True,
  randomize_cameras=False,
  camera_names=["robot0_oak_egoview", "robot0_rs_tppview"],
)
obs, info = env.reset()
print("ENV_OK", len(obs))
env.close()
EOF
'
```

## Phase 3: Bring Up Psi0 Server

### 3.1 Clone Psi0 Repo

```bash
docker exec ${CONTAINER_NAME} bash -lc '
  if [ ! -d /workspace/Psi0/.git ]; then
    git clone --depth 1 https://github.com/physical-superintelligence-lab/Psi0.git /workspace/Psi0
  fi
'
```

### 3.2 Install Psi0 Serve Dependencies in `unitree_sim_env`

```bash
docker exec ${CONTAINER_NAME} bash -lc '
  source /opt/conda/etc/profile.d/conda.sh
  conda activate unitree_sim_env
  pip install --upgrade \
    transformers==4.57.0 \
    qwen-vl-utils==0.0.14 \
    tyro==0.9.32 \
    accelerate==1.7.0 \
    peft==0.17.1 \
    flash-attn==2.7.4.post1 --no-build-isolation
'
```

### 3.3 Download Minimal Released Psi0 Run Directory

```bash
docker exec ${CONTAINER_NAME} bash -lc '
  source /opt/conda/etc/profile.d/conda.sh
  conda activate unitree_sim_env
  cd /workspace/Psi0
  [ -f .env ] || cp .env.sample .env
  python - <<EOF
from huggingface_hub import hf_hub_download
repo = "USC-PSI-Lab/psi-model"
for f in [
  "psi0/real-checkpoints/task1/argv.txt",
  "psi0/real-checkpoints/task1/run_config.json",
  "psi0/real-checkpoints/task1/checkpoints/ckpt_40000/model.safetensors",
]:
  print(hf_hub_download(repo_id=repo, filename=f, repo_type="model", local_dir="/workspace/Psi0/.runs"))
EOF
'
```

### 3.4 Start Server on Port 22085

```bash
docker exec ${CONTAINER_NAME} bash -lc '
  pkill -f psi0_serve_simple.py || true
  source /opt/conda/etc/profile.d/conda.sh
  conda activate unitree_sim_env
  cd /workspace/Psi0
  export PYTHONPATH=/workspace/Psi0/src:$PYTHONPATH
  nohup python src/psi/deploy/psi0_serve_simple.py \
    --host 0.0.0.0 \
    --port 22085 \
    --policy psi0 \
    --run-dir /workspace/Psi0/.runs/psi0/real-checkpoints/task1 \
    --ckpt-step 40000 \
    --action-exec-horizon 30 \
    >/tmp/psi0_server.log 2>&1 &
'

docker exec ${CONTAINER_NAME} bash -lc 'curl -s http://127.0.0.1:22085/health'
```

Expected:

```json
{"status":"ok"}
```

If `/health` is still refused, wait ~1-3 minutes and recheck. This model is large and first startup takes time.

## Phase 4: Deploy Integration Files

```bash
LOCAL_POLICY="/Users/dercio.fernandes/dm-isaac-g1/agents/gr00t_wholebodycontrol_dex1/psi0_wbc_policy.py"
LOCAL_PROBE="/Users/dercio.fernandes/dm-isaac-g1/agents/gr00t_wholebodycontrol_dex1/psi0_wbc_probe_validated.py"

cat "$LOCAL_POLICY" | ssh ${SSH_USER}@${INSTANCE_IP} "docker exec -i ${CONTAINER_NAME} tee /tmp/psi0_wbc_policy.py >/dev/null"
cat "$LOCAL_PROBE" | ssh ${SSH_USER}@${INSTANCE_IP} "docker exec -i ${CONTAINER_NAME} tee /tmp/psi0_wbc_probe_validated.py >/dev/null"
```

## Phase 5: Validation

Use the same runtime path + env vars for both tests:

```bash
export PYTHONPATH=/tmp:/workspace/Psi0/src:/workspace/Psi0:/workspace/GR00T-WholeBodyControl-dex1:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite:$PYTHONPATH
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
```

### 5.1 5-Step Test

```bash
docker exec ${CONTAINER_NAME} bash -lc '
  rm -f /tmp/gr00t_wbc
  ln -s /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc /tmp/gr00t_wbc
  export PYTHONPATH=/tmp:/workspace/Psi0/src:/workspace/Psi0:/workspace/GR00T-WholeBodyControl-dex1:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite:$PYTHONPATH
  export MUJOCO_GL=egl
  export PYOPENGL_PLATFORM=egl
  source /opt/conda/etc/profile.d/conda.sh
  conda activate unitree_sim_env
  timeout 180 python /tmp/psi0_wbc_probe_validated.py --max-steps 5 --control-freq 50 --wbc-upper-body-speed 0.2 2>&1 | tail -120
'
```

### 5.2 300-Step Standing Test

```bash
docker exec ${CONTAINER_NAME} bash -lc '
  rm -f /tmp/gr00t_wbc
  ln -s /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc /tmp/gr00t_wbc
  export PYTHONPATH=/tmp:/workspace/Psi0/src:/workspace/Psi0:/workspace/GR00T-WholeBodyControl-dex1:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite:$PYTHONPATH
  export MUJOCO_GL=egl
  export PYOPENGL_PLATFORM=egl
  source /opt/conda/etc/profile.d/conda.sh
  conda activate unitree_sim_env
  timeout 900 python /tmp/psi0_wbc_probe_validated.py --max-steps 300 --control-freq 50 --wbc-upper-body-speed 0.2 2>&1 | tail -220
'
```

Validated in this session:
- 5/5 steps completed, nonzero motion at every step
- 300/300 steps completed, robot remained standing (`base_z` stable around `0.75`)
- No output clipping/scaling required in `psi0_wbc_policy.py`

## Root-Cause Notes

Main integration failures came from interface mismatches, not model post-processing:
- Observation key mismatch: env exposes `q` + `annotation.human.task_description`, not `body_q` / `language_instruction`.
- State mismatch: Psi0 task1 expects `hand(14)+arm(14)+torso(4)+pad(4)` state layout (36-D padded).
- Action layout mismatch: Psi0 task1 action is `hand(14)+arm(14)+torso(4)+pad(4)` (not arm-first).
- History/reset bug: sending `{"reset": ...}` every call forced reset behavior every step.
- Control-path mismatch: direct `SyncEnv` stepping with raw `q` bypasses decoupled WBC balancing behavior.
- Lower-body command mismatch: Psi0 task1 channels `31:35` are not reliable WBC locomotion/base commands and should not be forwarded by default.
- Runtime tuning: decoupled WBC path is stable with `control_freq=50` and low interpolation speed (`--wbc-upper-body-speed 0.2`) in this setup.

The working path is to fix mapping/timing semantics rather than clipping model outputs.

## Troubleshooting

### `ModuleNotFoundError: gr00t_wbc.control`
- Ensure `/tmp/gr00t_wbc -> /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc` (not repo root).

### `ModuleNotFoundError: robosuite`
- Ensure `gr00trobosuite` branch clone exists and is on `PYTHONPATH`.

### `OpenGL.EGL.EGLDeviceEXT` missing
- Install `PyOpenGL>=3.1.7` in `unitree_sim_env`.

### `coverage.types.Tracer` error from numba
- Pin `numba==0.59.1` and `coverage==7.4.4`.

### Psi0 server crash: FlashAttention2 missing
- Install `flash-attn==2.7.4.post1 --no-build-isolation`.

### `/health` not responding
- Check `/tmp/psi0_server.log` and verify checkpoint files exist under:
  `/workspace/Psi0/.runs/psi0/real-checkpoints/task1`
