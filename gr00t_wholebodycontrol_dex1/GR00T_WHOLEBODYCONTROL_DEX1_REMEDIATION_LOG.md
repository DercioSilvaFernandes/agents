# GR00T WholeBodyControl Dex1 Remediation Log

Treat `AGENTS.md` and `current_task/GR00T_WHOLEBODYCONTROL_DEX1_REMEDIATION_LOG.md` as the active source of truth for this task.

## 2026-03-16 16:58:02 WET

- Command:
  - inspected `agents/FOLDER_CREATION_GUIDE.md`
  - inspected `agents/sim2sim_pipeline/*`
  - searched the repo for `GR00T`, `WholeBodyControl`, `dex1`, and WBC references
- Reason:
  - establish the correct task-folder template and identify the live WBC path already referenced in the repo
- Result:
  - confirmed a new standard task folder was required
  - confirmed the repo already references `/workspace/GR00T-WholeBodyControl-dex1` and the G1 WBC env names
- Persistence:
  - discovery only

## 2026-03-16 16:58:02 WET

- Command:
  - SSH to `54.155.29.100`
  - `docker ps --format "{{.Names}} {{.Status}}"`
- Reason:
  - confirm the fixed host and live workspace container
- Result:
  - validated container: `ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901`
- Persistence:
  - discovery only

## 2026-03-16 16:58:02 WET

- Command:
  - inspected `/workspace/GR00T-WholeBodyControl-dex1`
  - inspected `/workspace/Isaac-GR00T/examples/GR00T-WholeBodyControl/README.md`
  - inspected `gr00t/eval/rollout_policy.py`
- Reason:
  - determine the official G1 benchmark model/env pair
- Result:
  - selected `nvidia/GR00T-N1.6-G1-PnPAppleToPlate`
  - selected env `gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc`
- Persistence:
  - discovery only

## 2026-03-16 16:58:02 WET

- Command:
  - cloned `https://github.com/xieleo5/robosuite.git` branch `leo/support_g1_locomanip` into `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite`
- Reason:
  - the live container was missing the RoboSuite branch referenced by NVIDIA's setup path
- Result:
  - required source tree added in the live container
- Persistence:
  - live-only remote change

## 2026-03-16 16:58:02 WET

- Command:
  - created `/tmp/gr00t_wbc -> /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc`
- Reason:
  - `Isaac-GR00T` imports `gr00t_wbc`, while the live repo is packaged as `decoupled_wbc`
- Result:
  - import path unblocked
- Persistence:
  - live-only remote change

## 2026-03-16 16:58:02 WET

- File changed:
  - `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py`
  - `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/scene/configs.py`
- Reason:
  - vendored RoboCasa code failed on Python 3.11 due to mutable dataclass defaults
- Fix:
  - converted mutable defaults to `field(default_factory=...)`
- Result:
  - Python 3.11 import path progressed past the dataclass failures
- Persistence:
  - live-only remote change

## 2026-03-16 16:58:02 WET

- Command:
  - `pip install mink`
  - `pip install mujoco==3.2.6`
  - created `/opt/conda/envs/unitree_sim_env/lib/python3.11/site-packages/mink/tasks/exceptions.py`
- Reason:
  - the WBC stack needed `mink`, but the imported API layout did not match the robosuite branch
  - `mink` upgraded MuJoCo to `3.6.0`, which broke `gr00trobocasa`
- Result:
  - restored `mujoco==3.2.6`
  - added compatibility shim `from mink.exceptions import *`
- Persistence:
  - live-only remote change

## 2026-03-16 16:58:02 WET

- File changed:
  - `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/control/envs/robocasa/sync_env.py`
- Reason:
  - the file hardcoded `decoupled_wbc.control.envs.robocasa.sync_env` and failed when imported through the `gr00t_wbc` alias
- Fix:
  - switched the module self-reference to `sys.modules[__name__]`
  - switched the gym entry point to `f"{__name__}:{class_name}"`
- Result:
  - `gr00t_wbc.control.envs.robocasa.sync_env` imported successfully
- Persistence:
  - live-only remote change

## 2026-03-16 16:58:02 WET

- Command:
  - constructed and reset `gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc`
- Reason:
  - verify the env can actually build before loading the GR00T model
- Result:
  - env reset succeeded
  - instruction printed correctly
- Persistence:
  - runtime validation only

## 2026-03-16 16:58:02 WET

- Command:
  - ran `/tmp/gr00t_wbc_probe_vec.py` under `/opt/conda/envs/unitree_sim_env/bin/python`
- Reason:
  - verify that GR00T actions are applied to the WBC simulator and move the robot state
- Result:
  - model loaded: `nvidia/GR00T-N1.6-G1-PnPAppleToPlate`
  - action tensors emitted for waist, arms, hands, base height, and navigation
  - one step produced:
    - `joint_delta_norm 0.49687227606773376`
    - `joint_delta_max_abs 0.2770960330963135`
    - `joint_delta_nonzero 41`
- Persistence:
  - runtime validation only

## 2026-03-16 16:58:02 WET

- File changed:
  - created `agents/gr00t_wholebodycontrol_dex1/*`
- Reason:
  - deliver the requested task folder plus a minimal worked-steps file
- Result:
  - operator documentation created from the validated live path
- Persistence:
  - persistent repo change
