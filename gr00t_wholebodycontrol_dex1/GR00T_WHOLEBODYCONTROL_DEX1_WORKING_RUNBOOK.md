# GR00T WholeBodyControl Dex1 Working Runbook

## Purpose
This runbook captures the command path that actually worked for running the G1 WBC MuJoCo benchmark with a GR00T model on the fixed remote instance.

It is not a generic upstream guide. It documents the live container state and the extra compatibility work that was required here.

## Scope
- Remote host: `54.155.29.100`
- Runtime: ECS workspace container
- Python env: `unitree_sim_env`
- GR00T repo: `/workspace/Isaac-GR00T`
- WBC repo: `/workspace/GR00T-WholeBodyControl-dex1`
- Validated model: `nvidia/GR00T-N1.6-G1-PnPAppleToPlate`
- Validated env: `gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc`

## Preconditions
- SSH key exists at `/Users/dercio.fernandes/dm-isaac-g1.pem`
- the instance is up
- the ECS workspace container is up
- the container has GPU access

## Expected Steady-State Outcome
- the G1 WBC benchmark env can reset
- the GR00T model can load
- GR00T can emit action tensors for the WBC env
- a closed-loop step changes the simulated joint state

## 1. Reach The Host And Discover The Container

```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100

docker ps --format '{{.Names}} {{.Status}}'
```

Validated container:

```bash
ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901
```

## 2. Confirm GPU And Runtime

```bash
docker exec <container> nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader

docker exec <container> /opt/conda/envs/unitree_sim_env/bin/python -c \
  "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

Validated during this session:
- GPU: `NVIDIA A10G`
- CUDA available: `True`

## 3. Prepare The Missing WBC Python Inputs

The container had the WBC and GR00T repos, but not the exact Python import surface expected by the benchmark.

### 3.1 Clone The Required RoboSuite Branch

```bash
docker exec <container> bash -lc '
  if [ ! -d /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite/.git ]; then
    git clone --depth 1 --branch leo/support_g1_locomanip \
      https://github.com/xieleo5/robosuite.git \
      /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite
  fi
'
```

### 3.2 Create The `gr00t_wbc` Alias Expected By `Isaac-GR00T`

```bash
docker exec <container> bash -lc '
  rm -f /tmp/gr00t_wbc
  ln -s /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc /tmp/gr00t_wbc
'
```

### 3.3 Patch Python 3.11 Dataclass Defaults In Vendored `gr00trobocasa`

Validated files that required live fixes:
- `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py`
- `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/scene/configs.py`

Required change pattern:
- replace mutable `np.array(...)` dataclass defaults with `field(default_factory=...)`
- replace `SamplingConfig()` dataclass defaults with `field(default_factory=SamplingConfig)`

### 3.4 Add The `mink.tasks.exceptions` Compatibility Shim

```bash
docker exec <container> bash -lc "
cat > /opt/conda/envs/unitree_sim_env/lib/python3.11/site-packages/mink/tasks/exceptions.py <<'EOF'
from mink.exceptions import *
EOF
"
```

### 3.5 Restore MuJoCo 3.2.6

`mink` pulled in MuJoCo `3.6.0`, but `gr00trobocasa` hard-asserts `3.2.6` or `3.3.2`.

```bash
docker exec <container> /opt/conda/envs/unitree_sim_env/bin/pip install mink
docker exec <container> /opt/conda/envs/unitree_sim_env/bin/pip install mujoco==3.2.6
```

### 3.6 Patch `sync_env.py` Module Self-Reference

The local file hardcoded the `decoupled_wbc...` module name. It must use the loaded module name instead:
- line using `sys.modules[...]` must use `sys.modules[__name__]`
- gym `entry_point` must use `f"{__name__}:{class_name}"`

Validated file:
- `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/control/envs/robocasa/sync_env.py`

## 4. Export The Python Search Path Used By The Working Flow

Any probe or rollout command must expose these paths:

```bash
export PYTHONPATH=/tmp:/workspace/GR00T-WholeBodyControl-dex1:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite:$PYTHONPATH
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
```

## 5. Validate Env Construction

This is the first meaningful proof point. It must reset successfully.

```bash
docker exec <container> /opt/conda/envs/unitree_sim_env/bin/python -c "
import os, sys, gymnasium as gym
os.environ['MUJOCO_GL']='egl'
sys.path.insert(0, '/tmp')
sys.path.insert(0, '/workspace/GR00T-WholeBodyControl-dex1')
sys.path.insert(0, '/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa')
sys.path.insert(0, '/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite')
import gr00t_wbc.control.envs.robocasa.sync_env
env = gym.make(
    'gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc',
    onscreen=False,
    offscreen=True,
    enable_waist=True,
    randomize_cameras=False,
    camera_names=['robot0_oak_egoview', 'robot0_rs_tppview'],
)
obs, info = env.reset()
print('ENV_OK', type(env))
print('RESET_OK', sorted(obs.keys())[:10], len(obs))
env.close()
"
```

Validated result:
- env constructed
- reset succeeded
- instruction loaded: `pick up the apple, walk left and place the apple on the plate.`

## 6. Run The Closed-Loop GR00T Probe

This is the command path that proved the simulator is being actuated by GR00T-generated commands.

Create and run:

```bash
docker exec <container> bash -lc 'cat > /tmp/gr00t_wbc_probe_vec.py <<\"EOF\"
import os, sys, numpy as np
os.environ[\"MUJOCO_GL\"] = \"egl\"
os.environ[\"PYOPENGL_PLATFORM\"] = \"egl\"
sys.path.insert(0, \"/tmp\")
sys.path.insert(0, \"/workspace/GR00T-WholeBodyControl-dex1\")
sys.path.insert(0, \"/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa\")
sys.path.insert(0, \"/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite\")
import gymnasium as gym
from functools import partial
from gr00t.eval.rollout_policy import WrapperConfigs, VideoConfig, MultiStepConfig, create_eval_env, create_gr00t_sim_policy
from gr00t.data.embodiment_tags import EmbodimentTag

env_name = \"gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc\"
wrapper_configs = WrapperConfigs(
    video=VideoConfig(video_dir=None, max_episode_steps=16),
    multistep=MultiStepConfig(n_action_steps=4, max_episode_steps=16, terminate_on_success=False),
)
env = gym.vector.SyncVectorEnv([
    partial(create_eval_env, env_idx=0, env_name=env_name, total_n_envs=1, wrapper_configs=wrapper_configs)
])
policy = create_gr00t_sim_policy(\"nvidia/GR00T-N1.6-G1-PnPAppleToPlate\", EmbodimentTag.UNITREE_G1)
obs, info = env.reset()
policy.reset()
q0 = np.array(obs[\"q\"])[0, -1].copy()
actions, _ = policy.get_action(obs)
obs2, rewards, terminations, truncations, env_infos = env.step(actions)
q1 = np.array(obs2[\"q\"])[0, -1].copy()
delta = q1 - q0
print(\"action keys\", sorted(actions.keys()), flush=True)
for k, v in actions.items():
    arr = np.array(v)
    print(\"action\", k, arr.shape, arr.dtype, flush=True)
print(\"reward\", rewards.tolist(), \"terminated\", terminations.tolist(), \"truncated\", truncations.tolist(), flush=True)
print(\"joint_delta_norm\", float(np.linalg.norm(delta)), flush=True)
print(\"joint_delta_max_abs\", float(np.max(np.abs(delta))), flush=True)
print(\"joint_delta_nonzero\", int(np.count_nonzero(np.abs(delta) > 1e-6)), flush=True)
print(\"delta_first10\", np.round(delta[:10], 6).tolist(), flush=True)
env.close()
EOF
/opt/conda/envs/unitree_sim_env/bin/python /tmp/gr00t_wbc_probe_vec.py'
```

Validated output from this session:

```text
action keys ['action.base_height_command', 'action.left_arm', 'action.left_hand', 'action.navigate_command', 'action.right_arm', 'action.right_hand', 'action.waist']
action action.left_arm (1, 30, 7) float32
action action.right_arm (1, 30, 7) float32
action action.left_hand (1, 30, 7) float32
action action.right_hand (1, 30, 7) float32
action action.waist (1, 30, 3) float32
action action.base_height_command (1, 30, 1) float32
action action.navigate_command (1, 30, 3) float32
reward [0.0] terminated [False] truncated [False]
joint_delta_norm 0.49687227606773376
joint_delta_max_abs 0.2770960330963135
joint_delta_nonzero 41
```

Interpretation:
- the GR00T model produced action tensors
- the WBC wrapper consumed them
- the simulator state changed on 41 joints after one step
- this is sufficient proof that the robot was actuated, not merely displayed

## 7. Optional Next Step: Longer Rollout

Not required for this task, but the next logical step is a one-episode rollout using the same env/model after exporting the same `PYTHONPATH`.

## Troubleshooting
- `ValueError: mutable default <class 'numpy.ndarray'> ...`
  - patch the two vendored `gr00trobocasa` dataclass files
- `ModuleNotFoundError: gr00t_wbc`
  - recreate `/tmp/gr00t_wbc` symlink and add `/tmp` to `PYTHONPATH`
- `ModuleNotFoundError: mink.tasks.exceptions`
  - add the compatibility shim under the `unitree_sim_env` site-packages path
- `AssertionError: MuJoCo version must be 3.2.6 or 3.3.2`
  - reinstall `mujoco==3.2.6`
- `Video key 'ego_view' ... got (1, 480, 640, 3)`
  - do not call the policy on a raw single env; use the vector-env path so observations have batch and time dimensions
