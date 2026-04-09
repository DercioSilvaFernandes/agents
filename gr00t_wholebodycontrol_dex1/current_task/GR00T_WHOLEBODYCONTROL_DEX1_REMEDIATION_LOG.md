# Current Task Remediation Log

Parent source of truth:
- `../AGENTS.md`
- `../GR00T_WHOLEBODYCONTROL_DEX1_INTEGRATION_ENABLEMENT.md`

## 2026-03-16 16:58:02 WET

- Validated the live host and container:
  - host `54.155.29.100`
  - SSH user `ec2-user`
  - container `ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901`

## 2026-03-16 16:58:02 WET

- Confirmed the target upstream path:
  - WBC repo `/workspace/GR00T-WholeBodyControl-dex1`
  - GR00T repo `/workspace/Isaac-GR00T`
  - model `nvidia/GR00T-N1.6-G1-PnPAppleToPlate`
  - env `gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc`

## 2026-03-16 16:58:02 WET

- Applied live-only remote fixes required for importability:
  - cloned `gr00trobosuite` branch
  - created `/tmp/gr00t_wbc` alias
  - patched two Python 3.11 dataclass files in `gr00trobocasa`
  - added `mink.tasks.exceptions` shim
  - patched `sync_env.py` self-reference

## 2026-03-16 16:58:02 WET

- Validated env construction:
  - G1 WBC env reset successfully
  - task instruction loaded correctly

## 2026-03-16 16:58:02 WET

- Validated closed-loop GR00T actuation:
  - GR00T emitted non-empty action tensors
  - one WBC simulator step changed the joint state
  - measured:
    - `joint_delta_norm 0.49687227606773376`
    - `joint_delta_max_abs 0.2770960330963135`
    - `joint_delta_nonzero 41`

---

## 2026-04-09 PSI0 + WBC INTEGRATION - COMPLETED ✅

### Root Cause Analysis: 6 Major Issues Fixed

**Issue 1: Python 3.11 Mutable Dataclass Defaults**
- **Error**: `ValueError: mutable default <class 'numpy.ndarray'> for field rgba_a is not allowed`
- **Files**: `visuals_utls.py`, `configs.py`
- **Solution**: Converted to `field(default_factory=lambda: np.array(...))`
- **Status**: ✓ FIXED

**Issue 2: Module Aliasing in sync_env.py**
- **Error**: `KeyError: 'decoupled_wbc.control.envs.robocasa.sync_env'` in sys.modules
- **Root**: Hardcoded module path but module loaded as `/tmp/gr00t_wbc` alias
- **Solution**: Changed to dynamic `sys.modules[__name__]`
- **File**: `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/control/envs/robocasa/sync_env.py`
- **Status**: ✓ FIXED

**Issue 3: Missing Mink Dependency**
- **Error**: `ModuleNotFoundError: No module named 'mink'`
- **Solution**: `pip install mink mujoco==3.2.6`
- **Also created**: `/opt/conda/envs/.../mink/tasks/exceptions.py` compatibility shim
- **Status**: ✓ FIXED

**Issue 4: Image Serialization Dtype Mismatch**
- **Error**: "cannot reshape array of size 3686400 into shape (480,640,3)"
- **Root**: numpy_serialize converting uint8 to float32, breaking byte math
- **Solution**: Implemented dtype_to_descr/descr_to_dtype for proper preservation
- **File**: `psi0_wbc_policy.py` - numpy_serialize/deserialize functions
- **Status**: ✓ FIXED

**Issue 5: Image Resolution Mismatch**
- **Error**: Psi0 trained on 240×320, WBC provides 480×640
- **Solution**: Added cv2.resize() for downsampling
- **File**: `psi0_wbc_policy.py` - _request_psi0_action() method
- **Status**: ✓ FIXED

**Issue 6: Action Format Incompatibility (MAIN BLOCKER)**
- **Error**: `KeyError: 'q'` at sync_env.py line 246
- **Root**: Psi0 outputs 36 DOFs but WBC g1_body29_hand14.xml requires 43-DOF q vector
- **Discovery**: G1 = 29 body DOFs + 14 hand DOFs (7 per Inspire hand) = 43 total
- **Solution**: Map Psi0 hand outputs to q[29:43] indices
  ```python
  q_trajectory[:, 29:36] = psi0_action[:, 14:21]  # left hand
  q_trajectory[:, 36:43] = psi0_action[:, 21:28]  # right hand
  ```
- **File**: `psi0_wbc_policy.py` - _convert_psi0_to_wbc_actions() method
- **Status**: ✓ FIXED

### Validation Results

**50-Step Integration Probe - PASSED ✓**
```
[PROBE] ✓ Step   1/50: delta_norm=0.365749 | max_abs=0.220678
[PROBE] ✓ Step   2/50: delta_norm=0.375358 | max_abs=0.145133
...
[PROBE] ✓ Step  50/50: delta_norm=0.031818 | max_abs=0.016939

VALIDATION SUMMARY
  ✓ WBC environment created and reset
  ✓ Psi0 policy integrated
  ✓ Actions generated in WBC format
  ✓ Completed 50 steps
  ✓ Mean delta: 0.081538
  ✓ Max delta: 0.404377
  ✓ Nonzero steps: 50/50 (all dynamic, no stuck states)
```

### Files Modified

**Remote (Container: ecs-dm-interactive-shell-237-...)**
1. `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py`
   - Added: `from dataclasses import field`
   - Changed: `rgba_a` and `rgba_b` to use `field(default_factory=...)`

2. `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/scene/configs.py`
   - Added: `from dataclasses import field`
   - Changed: `x_range`, `y_range`, `rotation`, `reference_pos` to use `field(default_factory=...)`

3. `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/control/envs/robocasa/sync_env.py`
   - Changed: Hardcoded `sys.modules["decoupled_wbc..."]` → `sys.modules[__name__]`
   - Changed: entry_point strings from literal names → `f"{__name__}:..."`

4. `/opt/conda/envs/unitree_sim_env/lib/python3.11/site-packages/mink/tasks/exceptions.py`
   - Created: New compatibility shim with `from mink.exceptions import *`

**Local Updates**
- `/Users/dercio.fernandes/dm-isaac-g1/agents/gr00t_wholebodycontrol_dex1/psi0_wbc_policy.py`
  - Added: `dtype_to_descr()` and `descr_to_dtype()` for numpy dtype preservation
  - Added: `cv2.resize()` for image resolution conversion (480×640 → 240×320)
  - Fixed: `_convert_psi0_to_wbc_actions()` to generate 43-DOF q vector with proper Inspire hand mapping
  - Updated: `_request_psi0_action()` to serialize/deserialize with dtype preservation

### Key Architectural Insight

**G1 Configuration for WBC with Inspire Hands:**
```
q vector (43 DOFs):
  q[0:29]   = body DOFs (WBC balance layer controls these)
  q[29:36]  = left Inspire hand (from Psi0[14:21])
  q[36:43]  = right Inspire hand (from Psi0[21:28])
```

**Psi0 Real Robot Checkpoint (40K steps):**
- Trained on real Unitree G1 with Inspire dexterous hands
- 36 DOF output: arms(14) + hands(14) + waist(3) + base_height(1) + navigate(3) + reserved(1)
- Outputs explicit dexterous manipulation commands (not just gripper open/close)

### Deployment Status

- ✅ All patches deployed to remote container
- ✅ Psi0 server verified responding on port 22085
- ✅ Integration layer handling full control flow
- ✅ 50-step probe validation passed
- ✅ Joint state changes measurable and consistent

### Next Steps (Now Possible)

With integration complete, can now:
1. Run actual manipulation tasks (pick apple, place on plate)
2. Validate task success metrics
3. Optimize WBC control parameters for smoother motions
4. Record full rollout videos with GUI visualization
5. Measure robustness over longer horizons (100+ steps)
