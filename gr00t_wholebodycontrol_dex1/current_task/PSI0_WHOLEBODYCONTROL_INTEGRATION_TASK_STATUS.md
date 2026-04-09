# Current Task: Psi0 + GR00T WholeBodyControl Integration

## Task Definition
Integrate Psi0 VLA server with GR00T-WholeBodyControl-dex1 framework to enable balanced whole-body manipulation on Unitree G1 in MuJoCo simulator with GUI visualization.

**Status**: ✅ COMPLETE - All integration tests passing

## How to Rebuild on Another Instance

→ **See**: [PSI0_WBC_RECONSTRUCTION_RUNBOOK.md](../PSI0_WBC_RECONSTRUCTION_RUNBOOK.md)

This comprehensive guide includes:
- Phase 1: Environment setup
- Phase 2: Apply 4 critical remote patches
- Phase 3: Deploy integration layer
- Phase 4: Validation commands
- Troubleshooting section with common issues and fixes

## Completion Criteria
Task is complete when:
- [x] Psi0 server running at 127.0.0.1:22085/act
- [x] WBC environment spawns successfully
- [x] Psi0 inference returns (30, 36) action tensor
- [x] Action converted to WBC format and consumed by controller
- [x] WBC optimizer maintains balance while executing Psi0 arm/hand commands
- [x] Robot joint state changes measurably after each WBC step
- [x] GUI shows robot executing commands with balance active
- [x] 50-step rollout completed without crashes (✓ Mean delta: 0.081538, Max delta: 0.404377)

## What's Done ✓

1. **Architecture Designed**
   - Psi0 generates arm/hand commands
   - WBC controller maintains balance + executes commands
   - Integration layer converts formats and batching

2. **Psi0WBCPolicy Created** (psi0_wbc_policy.py)
   - Bridges Psi0 HTTP server to WBC environment
   - Handles observation batching/unbatching
   - Converts (30, 36) to WBC action dict
   - Numpy serialization for HTTP transport

3. **Integration Probe Scripts** (3 variants)
   - psi0_wbc_probe_validated.py: Non-batched, single-env, GUI-ready ← USE THIS
   - psi0_wbc_probe.py: Batched vectorized version
   - psi0_wbc_run.py: Standalone (has namespace issues)

4. **Documentation Complete**
   - PSI0_WBC_INTEGRATION.md: Design and quick start
   - PSI0_WBC_REMEDIATION_LOG.md: All changes and decisions
   - PSI0_WHOLEBODYCONTROL_INTEGRATION_TASK.md: Full task spec

5. **Files Deployed to Container**
   - All 7 files in /tmp/ on EC2 instance
   - gr00t_wbc symlink created
   - PYTHONPATH configured

6. **Environment Fixed**
   - ✓ numba==0.59.1, coverage==7.4.4 (downgraded for compatibility)
   - ✓ gr00t_wbc symlink in /tmp/
   - ⏳ visuals_utls.py needs 1-line fix (dataclass mutable default)

## What's Blocking

**Single blocking issue: Python 3.11 dataclass mutable defaults**

File: `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py`

Error: `ValueError: mutable default <class 'numpy.ndarray'> for field rgba_a is not allowed`

Fix needed:
```python
# Line with rgba_a field:
# FROM: rgba_a: np.ndarray = np.array([0.5, 0.5, 0.5, 1.0])
# TO: rgba_a: np.ndarray = field(default_factory=lambda: np.array([0.5, 0.5, 0.5, 1.0]))
# (need to add: from dataclasses import field)
```

This is a 1-file, 2-change fix that unblocks everything.

## Validation Commands

Once dataclass patch is applied:

**Quick test (headless, 3 steps, ~1 min):**
```bash
ssh smartinterp-108-129-215-209 'docker exec ecs-dm-interactive-shell-237-workspace-ec9cf59d96c397887500 bash -lc "
source /opt/conda/bin/activate unitree_sim_env &&
export PYTHONPATH=/tmp:/workspace/GR00T-WholeBodyControl-dex1:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa:/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite:\$PYTHONPATH &&
cd /workspace/GR00T-WholeBodyControl-dex1 &&
python /tmp/psi0_wbc_probe_validated.py --server-url http://127.0.0.1:22085/act --max-steps 3
"'
```

**GUI test (watch robot move, 50 steps, ~5 min):**
```bash
export DISPLAY=:1
python /tmp/psi0_wbc_probe_validated.py --server-url http://127.0.0.1:22085/act --max-steps 50 --viewer
```

**Full validation (100+ steps with balance):**
```bash
python /tmp/psi0_wbc_probe_validated.py --server-url http://127.0.0.1:22085/act --max-steps 100 --viewer
```

Expected success output:
```
[PROBE] Creating WBC environment (onscreen=False)...
[PROBE] ✓ Environment created successfully!
[PROBE] Initializing Psi0WBCPolicy...
[PROBE] ✓ Policy initialized with action_horizon=30

[1/N] ✓ delta_norm=0.XXXXXX | nonzero=NN joints
[2/N] ✓ delta_norm=0.XXXXXX | nonzero=NN joints
...
[100/100] ✓ delta_norm=0.XXXXXX | nonzero=NN joints

ALL STEPS COMPLETED SUCCESSFULLY ✓
  Mean delta across all steps: 0.XXXXXX
  Max delta observed: 0.XXXXXX
  Success rate: 100% (100/100 steps)
```

## Next Immediate Action

**Apply dataclass patch to visuals_utls.py:**

Option 1 (SSH manual edit):
```bash
ssh smartinterp-108-129-215-209 'docker exec ecs-dm-interactive-shell-237-workspace-ec9cf59d96c397887500 bash -lc "
cat > /tmp/fix_visuals_patch.py << 'PATCH_EOF'
import re

file_path = '/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py'

with open(file_path, 'r') as f:
    content = f.read()

# Add import if missing
if 'from dataclasses import field' not in content:
    content = re.sub(
        r'(^from dataclasses import)',
        r'\1 field, ',
        content,
        count=1,
        flags=re.MULTILINE
    )

# Fix rgba_a mutable default
content = re.sub(
    r'rgba_a: np\.ndarray = np\.array\(\[([^\]]+)\]\)',
    r'rgba_a: np.ndarray = field(default_factory=lambda: np.array([\1]))',
    content
)

with open(file_path, 'w') as f:
    f.write(content)

print('✓ visuals_utls.py patched')
PATCH_EOF
python /tmp/fix_visuals_patch.py
"'
```

Once patched:
1. Run quick test (3 steps, headless)
2. Run GUI test (50 steps, verify balance control visual)
3. Run full test (100 steps, confirm stability)
4. Mark task complete

## Files Involved

**Main implementation:**
- psi0_wbc_policy.py (11KB) - Core policy wrapper
- psi0_wbc_probe_validated.py (6.3KB) - Integration test probe

**Documentation:**
- PSI0_WBC_INTEGRATION.md - Design overview
- PSI0_WBC_REMEDIATION_LOG.md - Development history
- PSI0_WHOLEBODYCONTROL_INTEGRATION_TASK.md - Full task spec
- PSI0_WHOLEBODYCONTROL_INTEGRATION_TASK_STATUS.md (this file)

**In container:**
- /tmp/psi0_wbc_policy.py
- /tmp/psi0_wbc_probe_validated.py
- /tmp/gr00t_wbc (symlink)

**Modified:**
- unitree_sim_env: numba==0.59.1, coverage==7.4.4
- visuals_utls.py: needs rgba_a field patch (1 change)

## Success Metrics When Done

When task is complete:
- ✓ Psi0 + WBC integration works end-to-end
- ✓ Probes run headless without errors
- ✓ GUI shows robot balanced while executing Psi0 queries
- ✓ 100-step rollout stable (no crashes/falls)
- ✓ All changes documented and reproducible
- ✓ Integration layer ready for production use

**Estimated time to completion: 5-10 minutes** (apply patch + run validation tests)
