# Psi0 + GR00T WholeBodyControl Integration Task

## Objective
Create an operator-ready integration where Psi0 VLA server inference is plugged into the GR00T-WholeBodyControl-dex1 framework for balanced whole-body manipulation on Unitree G1 in MuJoCo simulation.

This task is complete ONLY when:
1. Psi0 server is running and reachable
2. WBC environment creates successfully
3. Psi0 generates action outputs via HTTP API
4. Actions are converted to WBC format and consumed by the controller
5. WBC optimizer maintains balance while executing Psi0-generated arm/hand commands
6. Simulator joint state changes measurably after WBC processes Psi0 actions
7. GUI viewer displays robot executing Psi0 queries with balance control active

## Architecture
```
Psi0 Server (arm/hand policy)
    ↓ HTTP request with egocentric image + state
    ↓ Returns (30, 36) action tensor
    
Psi0WBCPolicy Wrapper (integration layer)
    ↓ Converts to WBC action dict format
    ↓ Adds batch dimension
    
WBC Environment (whole-body control)
    ├─ Inverse kinematics
    ├─ Balance controller (maintains stability)
    ├─ Whole-body constraint optimization
    └─ MuJoCo simulator
    
Result: Robot moves arms/hands from Psi0 while balance maintained by WBC
```

## Acceptance Criteria

### Functional Requirements
- ✓ Psi0 policy wrapper (`Psi0WBCPolicy` class) created
- ✓ Action conversion implemented (30×36 → WBC dict)
- ⏳ Full integration probe executes headless without errors
- ⏳ GUI viewer shows robot moving with balance control
- ⏳ Joint state delta > 0 after WBC processes Psi0 actions
- ⏳ Multiple steps (100+) execute without crashes

### Technical Requirements
- ✓ Integration layer works with GR00T-WholeBodyControl-dex1 repo structure
- ✓ Compatible with unitree_sim_env conda environment
- ✓ HTTP client error handling implemented
- ✓ Observation batching/unbatching handled correctly
- ⏳ Dataclass compatibility issues resolved
- ⏳ Tested on live EC2 container (54.155.29.100)

### Success Metrics
When task is complete, running this command should succeed:

```bash
python psi0_wbc_probe_validated.py \
  --server-url http://127.0.0.1:22085/act \
  --max-steps 100 \
  --viewer
```

Expected output:
```
[INIT] ✓ Environment created
[INIT] ✓ Policy initialized

[1/100] ✓ delta=0.XXXXXX | nonzero=NN joints
[2/100] ✓ delta=0.XXXXXX | nonzero=NN joints
...

SUMMARY
  Steps completed: 100
  Mean delta: 0.XXXXXX
  Max delta: 0.XXXXXX
  ✓ WBC + Psi0 integration working!
```

And MuJoCo GUI window should display G1 robot:
- Standing with WBC balance active
- Executing arm/hand movements from Psi0 queries  
- No falls or instability
- Smooth motion across all 100 steps

## Current Status

### Completed
- ✓ Architecture designed and documented
- ✓ Policy wrapper created and tested locally
- ✓ Action format conversion implemented
- ✓ Integration probe scripts created (3 versions)
- ✓ All files transferred to remote container
- ✓ Environment setup validated
- ✓ Known issues documented with fixes

### Blocked (Non-Blocking)
- ⏳ Python 3.11 dataclass mutable defaults need manual patch in 1 file
  - File: `/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py`
  - Fix: Change `rgba_a: np.ndarray = np.array([...])` to use `field(default_factory=...)`

### Remaining Work
1. Apply dataclass patch to visuals_utls.py in container
2. Run headless probe to validate integration
3. Run with GUI to validate visualization and balance control
4. Verify 100-step rollout stability
5. Document final validation results

## Files Involved

**Created/Modified Local**:
- psi0_wbc_policy.py (policy wrapper, 11KB)
- psi0_wbc_probe_validated.py (integration probe, 6.3KB)
- PSI0_WBC_INTEGRATION.md (documentation)
- PSI0_WBC_REMEDIATION_LOG.md (development log)
- PSI0_WHOLEBODYCONTROL_INTEGRATION_TASK.md (this file)

**Deployed to Container**:
- /tmp/psi0_wbc_policy.py
- /tmp/psi0_wbc_probe_validated.py
- /tmp/gr00t_wbc (symlink)

**Modified in Container**:
- numba==0.59.1, coverage==7.4.4 (versions downgraded)
- /workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa/robocasa/utils/visuals_utls.py (needs patch)

## Key Differences from Solo Psi0

### Before Integration
- Psi0 runs standalone on G1 robot model in MuJoCo
- No balance control or WBC optimization
- Raw Psi0 actions applied directly to joints
- Robot likely unstable during arm movements
- Limited dexterous capability

### After Integration
- Psi0 feeds arm/hand commands to WBC controller
- WBC maintains balance through IK + whole-body optimization
- Base, waist, and navigation controlled by WBC (not Psi0)
- Robot stable during complex manipulations
- Full whole-body coordination

## Validation Path

1. **Quick Check** (2-3 min headless):
   ```bash
   python psi0_wbc_probe_validated.py --max-steps 1
   ```
   Expected: 1 successful inference step, no crashes

2. **Stability Check** (5 min headless):
   ```bash
   python psi0_wbc_probe_validated.py --max-steps 10
   ```
   Expected: Consistent joint deltas, no failures

3. **GUI Check** (10 min with viewer):
   ```bash
   python psi0_wbc_probe_validated.py --max-steps 50 --viewer
   ```
   Expected: MuJoCo window opens, robot moves smoothly, balance maintained

4. **Full Episode** (30 min with viewer):
   ```bash
   python psi0_wbc_probe_validated.py --max-steps 100 --viewer
   ```
   Expected: 100 consecutive steps, no falls, smooth execution

## References
- Original WBC working probe: GR00T_WHOLEBODYCONTROL_DEX1_WORKING_RUNBOOK.md
- Policy wrapper source: psi0_wbc_policy.py
- Integration documentation: PSI0_WBC_INTEGRATION.md
- Development log: PSI0_WBC_REMEDIATION_LOG.md
