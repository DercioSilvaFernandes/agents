# GR00T WholeBodyControl Dex1 Minimal Working Steps

This file lists only the steps that were validated to work on `54.155.29.100`.

## 1. Use The ECS Container

```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100
docker ps --format '{{.Names}} {{.Status}}'
```

Use:

```bash
ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901
```

## 2. Use `unitree_sim_env`

Validated interpreter:

```bash
/opt/conda/envs/unitree_sim_env/bin/python
```

## 3. Add The Missing Python Paths

```bash
export PYTHONPATH=/tmp:/workspace/GR00T-WholeBodyControl-dex1:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite:$PYTHONPATH
export MUJOCO_GL=egl
export PYOPENGL_PLATFORM=egl
```

## 4. Use This Model And This Env

```text
Model: nvidia/GR00T-N1.6-G1-PnPAppleToPlate
Env:   gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc
```

## 5. Use The Vector-Env Probe, Not A Raw Single Env

The raw single env shape was wrong for the GR00T policy. The working path was:
- build a `gym.vector.SyncVectorEnv` with one env
- reset it
- call `policy.get_action(obs)`
- step once
- compare `obs["q"]` before and after

## 6. What Proved It Was Really Actuating The Robot

Validated output:

```text
joint_delta_norm 0.49687227606773376
joint_delta_max_abs 0.2770960330963135
joint_delta_nonzero 41
```

That is the proof that the simulator was not just open. The joint state changed after the GR00T action was applied through the WBC stack.
