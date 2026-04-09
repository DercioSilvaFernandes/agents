# Psi0 + GR00T WholeBodyControl Integration - Remediation Log

## Session Overview
**Objective**: Integrate Psi0 VLA server inference into GR00T WholeBodyControl framework for balanced whole-body humanoid control on Unitree G1 in MuJoCo simulation.

**Target Instance**: 54.155.29.100 (EC2)  
**Container**: ecs-dm-interactive-shell-237-workspace-ec9cf59d96c397887500  
**Environment**: unitree_sim_env (conda)  
**Base Repo**: /workspace/GR00T-WholeBodyControl-dex1

---

## Files Created

### Core Integration
1. **psi0_wbc_policy.py** (11KB)
   - Custom policy wrapper implementing `Psi0WBCPolicy` class
   - Drop-in replacement for GR00T policy interface
   - Calls Psi0 HTTP server with WBC observations
   - Converts (30, 36) Psi0 output → WBC action dict format
   - Handles numpy serialization/deserialization for HTTP
   - Added to container: `/tmp/psi0_wbc_policy.py`

### Validation/Testing Scripts
2. **psi0_wbc_probe.py** (9KB, initial version)
   - SyncVectorEnv-based probe (batch dimension handling)
   - GUI viewer support via `--viewer` flag
   - Real-time metrics reporting per step
   - Status: Works with proper PYTHONPATH setup

3. **psi0_wbc_probe_validated.py** (6.3KB, working version)
   - Simplified single-env probe (non-batched)
   - Based on validated working pattern from GR00T_WHOLEBODYCONTROL_DEX1_WORKING_RUNBOOK.md
   - Uses simple loop instead of vector env
   - Better error handling and reporting
   - Status: Should work after dataclass patch applied

4. **psi0_wbc_run.py** (Enhanced standalone)
   - Attempted dataclass patching on import
   - Self-contained with error recovery
   - Status: Namespace collision with gymnasium - needs simpler approach

### Patch/Utility Scripts
5. **patch_dataclass.py**
   - Regex-based patch for Python 3.11 dataclass mutable defaults
   - Targets visuals_utls.py and configs.py
   - Not yet executed due to quoting issues

6. **fix_visuals.py**
   - Simpler targeted fix for rgba_a field issue
   - Adds field import, fixes dataclass default
   - Not yet executed

### Documentation
7. **PSI0_WBC_INTEGRATION.md** (comprehensive)
   - Architecture diagrams and explanations
   - Quick start guide
   - Action format specifications
   - Troubleshooting section
   - Usage examples

---

## Architecture Overview

```
Psi0 Server (HTTP)
         ↓ (30, 36 raw arm/hand/torso commands)
    
Psi0WBCPolicy Wrapper
    • Accepts WBC observations (images + state + instruction)
    • Calls Psi0 server
    • Converts to WBC action dict
         ↓
         
WBC Environment (GR00T-WholeBodyControl-dex1)
    • Inverse kinematics
    • Balance controller
    • Whole-body optimizer
         ↓
         
MuJoCo Simulator
    • Robot actuates with balance maintained
```

---

## Key Conversion: Psi0 → WBC Actions

**Psi0 Output** (shape: 30 timesteps × 36 DOFs):
```
[0:7]     left_arm (7 DOF)
[7:14]    right_arm (7 DOF)
[14:21]   left_hand (7 DOF)
[21:28]   right_hand (7 DOF)
[28:31]   waist XYZ (3 DOF)
[31:32]   base_height (1 DOF)
[32:35]   navigate VX/VY/VYAW (3 DOF)
[35]      reserved
```

**WBC Action Dict** (output with batch=1):
```python
{
    "action.left_arm": (1, 30, 7),
    "action.right_arm": (1, 30, 7),
    "action.left_hand": (1, 30, 7),
    "action.right_hand": (1, 30, 7),
    "action.waist": (1, 30, 3),
    "action.base_height_command": (1, 30, 1),
    "action.navigate_command": (1, 30, 3),
}
```

---

## Issues Encountered & Solutions

### Issue 1: ModuleNotFoundError - gr00t_wbc
**Symptom**: `ModuleNotFoundError: No module named 'gr00t_wbc'`  
**Root Cause**: gr00t_wbc is a symlink alias expected in sys.path  
**Solution**: Created symlink in container
```bash
rm -f /tmp/gr00t_wbc
ln -s /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc /tmp/gr00t_wbc
```
**Status**: ✓ Fixed

### Issue 2: robosuite Module Missing
**Symptom**: `ModuleNotFoundError: No module named 'robosuite'`  
**Root Cause**: robosuite branch not cloned to expected location  
**Solution**: Clone the leo/support_g1_locomanip branch  
**Command**:
```bash
git clone --depth 1 --branch leo/support_g1_locomanip \
  https://github.com/xieleo5/robosuite.git \
  /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite
```
**Status**: ⏳ Not yet verified if needed (PYTHONPATH may cover it)

### Issue 3: Numba/Coverage Incompatibility
**Symptom**: `AttributeError: module 'coverage.types' has no attribute 'Tracer'`  
**Root Cause**: numba and coverage versions conflict in unitree_sim_env  
**Solution**: Downgrade to compatible versions
```bash
pip install numba==0.59.1 coverage==7.4.4
```
**Status**: ✓ Applied (some dependency conflicts remain but non-blocking)

### Issue 4: Python 3.11 Dataclass Mutable Defaults
**Symptom**: `ValueError: mutable default <class 'numpy.ndarray'> for field rgba_a is not allowed`  
**Root Cause**: Python 3.11+ forbids mutable defaults in dataclasses; gr00trobocasa uses old pattern  
**Files Affected**: 
- `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py`
- `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/scene/configs.py`

**Solution**: Manually patch files to use `field(default_factory=...)`  
**Manual Fix Pattern**:
```python
# Before:
@dataclass
class Gradient:
    rgba_a: np.ndarray = np.array([...])

# After:  
from dataclasses import field

@dataclass
class Gradient:
    rgba_a: np.ndarray = field(default_factory=lambda: np.array([...]))
```
**Status**: ⏳ Needs manual application in container

---

## Environment Setup Requirements

### Conda Environment
```bash
source /opt/conda/bin/activate unitree_sim_env
```

### PYTHONPATH (all required for robocasa import to work)
```bash
export PYTHONPATH=/tmp:\
/workspace/GR00T-WholeBodyControl-dex1:\
/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa:\
/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite:$PYTHONPATH
```

### MuJoCo Display
```bash
export DISPLAY=:1                    # For GUI viewer
export MUJOCO_GL=glfw                # Use GLFW renderer (GUI mode)
# OR
export MUJOCO_GL=egl                 # Use EGL renderer (headless)
export PYOPENGL_PLATFORM=egl
```

### Symlink Setup (in container)
```bash
rm -f /tmp/gr00t_wbc
ln -s /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc /tmp/gr00t_wbc
```

---

## Files Copied to Remote/Container

**Local PC → EC2 Host** (`/tmp/` on host):
- psi0_wbc_policy.py (11KB)
- psi0_wbc_probe.py (9KB)
- psi0_wbc_probe_validated.py (6.3KB)
- psi0_wbc_run.py
- patch_dataclass.py
- fix_visuals.py

**EC2 Host → Docker Container** (`/tmp/` in container):
- Docker cp commands used to copy from host `/tmp/` to container `/tmp/`
- Status: ✓ All files present in container

---

## Current Status

### ✓ Completed
- [x] Policy wrapper (`Psi0WBCPolicy`) created and copied to container
- [x] Probe script created in multiple versions
- [x] All files transferred to remote/container
- [x] gr00t_wbc symlink created in container
- [x] numba/coverage downgraded to compatible versions
- [x] Architecture documented
- [x] Action format conversion implemented

### ⏳ Pending/Blocked
- [ ] Python 3.11 dataclass mutable defaults manually patched in container
  - **Blocker**: Need to manually edit 2 files in container to fix `rgba_a` fields
  - **Action**: Apply fix_visuals.py patch or manually edit visuals_utls.py
- [ ] End-to-end probe execution validated
  - **Blocker**: Waiting for dataclass patch
  - **Expected**: Once patched, `psi0_wbc_probe_validated.py` should run successfully
- [ ] GUI viewer tested with Psi0+WBC

### Next Steps
1. Apply dataclass patch to visuals_utls.py (manually or via script)
2. Run: `python /tmp/psi0_wbc_probe_validated.py --server-url http://127.0.0.1:22085/act --max-steps 3`
3. If successful, test GUI mode: `--viewer --max-steps 100`
4. Create production rollout script for longer episodes

---

## Testing Command Reference

### Headless (fast, validates integration logic)
```bash
bash -lc "
source /opt/conda/bin/activate unitree_sim_env
export PYTHONPATH=/tmp:/workspace/GR00T-WholeBodyControl-dex1:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite:\$PYTHONPATH
cd /workspace/GR00T-WholeBodyControl-dex1
python /tmp/psi0_wbc_probe_validated.py --server-url http://127.0.0.1:22085/act --max-steps 3
"
```

### With GUI Viewer (watch robot move)
```bash
bash -lc "
source /opt/conda/bin/activate unitree_sim_env
export DISPLAY=:1
export PYTHONPATH=/tmp:/workspace/GR00T-WholeBodyControl-dex1:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite:\$PYTHONPATH
cd /workspace/GR00T-WholeBodyControl-dex1
python /tmp/psi0_wbc_probe_validated.py --server-url http://127.0.0.1:22085/act --max-steps 100 --viewer
"
```

---

## Known Issues Unresolved

1. **isaacsim dependency conflicts**: Numerous pip dependencies conflict with isaacsim-kernel version. Non-blocking but could cause issues with OTHER isaac workflows.

2. **robosuite warnings**: Missing macros.py setup and robosuite_models package - not blocking WBC functionality but could improve performance.

3. **MuJoCo version**: Verified as 3.2.6 (required by gr00trobocasa).

---

## References

- Original working probe: GR00T_WHOLEBODYCONTROL_DEX1_WORKING_RUNBOOK.md (section 6)
- WBC observation format: GR00T_WBC_OBSERVATION_STRUCTURE.md
- Policy action format: Psi0 outputs (30, 36), converted to WBC dict with batch=1

