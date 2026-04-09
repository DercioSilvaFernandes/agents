# Psi0 WholeBodyControl G1 Integration

## Overview
This integration replaces the GR00T policy with Psi0 server inference in the GR00T WholeBodyControl framework. The system maintains balance through WBC while Psi0 generates arm/hand commands from natural language instructions and egocentric vision.

## Architecture Diagram
```
Observation (WBC SyncVectorEnv)
    ├── Images: ego_view_image (256x256 RGB)
    ├── State: body_q (joint positions)
    └── Instruction: language_instruction (task string)
                  ↓
        [Psi0 Policy Wrapper]
                  ↓
    Psi0 Server HTTP Request
    ├── image: egocentric RGB
    ├── state: joint positions (14)
    ├── instruction: task description
    └── prev_actions, inference_delay, max_delay
                  ↓
        Psi0 Response: (30, 36)
    [arm(14) | hand(14) | torso(8)]
                  ↓
        [Action Converter]
                  ↓
    WBC Action Dict
    ├── action.left_arm: (1, 30, 7)
    ├── action.right_arm: (1, 30, 7)
    ├── action.left_hand: (1, 30, 7)
    ├── action.right_hand: (1, 30, 7)
    ├── action.waist: (1, 30, 3)
    ├── action.base_height_command: (1, 30, 1)
    └── action.navigate_command: (1, 30, 3)
                  ↓
        WBC Environment
    ├── Inverse kinematics
    ├── Balance controller
    ├── Whole-body control
    └── MuJoCo physics
                  ↓
        Actuated Robot State
```

## Files

### Core Integration
- **`psi0_wbc_policy.py`**: Policy wrapper class `Psi0WBCPolicy`
  - Implements GR00T-compatible interface (`get_action()`)
  - Calls Psi0 HTTP server
  - Converts (30, 36) output → WBC action format
  - Handles batching and serialization

### Validation & Testing
- **`psi0_wbc_probe.py`**: Integration test script
  - Creates WBC environment
  - Initializes Psi0 policy
  - Executes 1+ steps and validates state changes
  - Reports action shapes and joint deltas

### Documentation (this folder)
- **`GR00T_WHOLEBODYCONTROL_DEX1_WORKING_RUNBOOK.md`**: Original GR00T setup guide
- **`GR00T_WHOLEBODYCONTROL_DEX1_MINIMAL_WORKING_STEPS.md`**: Quick reference
- **`PSI0_WBC_INTEGRATION.md`**: This file

## Quick Start

### 1. Prerequisites
Ensure these are installed/available on remote:
- GR00T-WholeBodyControl-dex1 repo cloned
- All Python compatibility patches applied (see main RUNBOOK)
- Psi0 server running and accessible at `http://127.0.0.1:22085/act`
- unitree_sim_env conda environment with all dependencies

### 2. SSH to Remote and Discover Container
```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100
docker ps --format '{{.Names}} {{.Status}}'
```
Use the active container name in following commands.

### 3. Copy Policy Files to Remote
```bash
scp -i /Users/dercio.fernandes/dm-isaac-g1.pem \
  /Users/dercio.fernandes/dm-isaac-g1/agents/gr00t_wholebodycontrol_dex1/psi0_wbc_policy.py \
  ec2-user@54.155.29.100:/tmp/

scp -i /Users/dercio.fernandes/dm-isaac-g1.pem \
  /Users/dercio.fernandes/dm-isaac-g1/agents/gr00t_wholebodycontrol_dex1/psi0_wbc_probe.py \
  ec2-user@54.155.29.100:/workspace/GR00T-WholeBodyControl-dex1/
```

### 4. Run Integration Probe
```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100 \
  'docker exec <container_name> bash -lc "
    export PYTHONPATH=/tmp:/workspace/GR00T-WholeBodyControl-dex1:...
    export MUJOCO_GL=egl
    export PYOPENGL_PLATFORM=egl
    cd /workspace/GR00T-WholeBodyControl-dex1
    /opt/conda/envs/unitree_sim_env/bin/python psi0_wbc_probe.py \
      --server-url http://127.0.0.1:22085/act \
      --max-steps 5
  "'
```

**Or with GUI viewer** (requires X11 DISPLAY):
```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100 \
  'docker exec <container_name> bash -lc "
    export DISPLAY=:1
    export PYTHONPATH=/tmp:/workspace/GR00T-WholeBodyControl-dex1:...
    cd /workspace/GR00T-WholeBodyControl-dex1
    /opt/conda/envs/unitree_sim_env/bin/python psi0_wbc_probe.py \
      --server-url http://127.0.0.1:22085/act \
      --max-steps 100 \
      --viewer
  "'
```

Expected output if successful:
```
[PSI0-WBC-PROBE] Starting integration validation
[PSI0-WBC-PROBE] Environment created successfully
[PSI0-WBC-PROBE] Policy created and reset
[PSI0-WBC-PROBE] Action received successfully
[PSI0-WBC-PROBE] Action keys: ['action.base_height_command', 'action.left_arm', ...]
[PSI0-WBC-PROBE] Step 1: delta_norm=0.XXXXXXX
[PSI0-WBC-PROBE] ✓ Step   2/100: delta_norm=0.XXXXXX | nonzero=NNN | time=XX.Xms
[PSI0-WBC-PROBE] ✓ Step   3/100: delta_norm=0.XXXXXX | nonzero=NNN | time=XX.Xms
```

With `--viewer`, a MuJoCo window will appear showing the robot in real-time as it executes the actions.

## Using Psi0 Policy in Your Own Code

```python
import gymnasium as gym
from functools import partial
from psi0_wbc_policy import Psi0WBCPolicy
import gr00t_wbc.control.envs.robocasa.sync_env

# Create WBC environment
env = gym.vector.SyncVectorEnv([
    partial(
        lambda: gym.make(
            "gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc",
            onscreen=False,
            offscreen=True,
        )
    )
])

# Create policy (drop-in replacement for GR00T)
policy = Psi0WBCPolicy(
    server_url="http://127.0.0.1:22085/act",
    timeout_s=10.0,
    action_horizon=30,
)

# Run inference loop
obs, info = env.reset()
policy.reset()

for step in range(100):
    actions, action_info = policy.get_action(obs)
    obs, rewards, terminations, truncations, env_infos = env.step(actions)
    
    if truncations.any() or terminations.any():
        break

env.close()
```

## Action Format Details

### Psi0 Output (raw from server)
Tensor shape: **(30, 36)** with structure:
- **[0:7]** - left arm joints (7 DOF)
- **[7:14]** - right arm joints (7 DOF)
- **[14:21]** - left hand joints (7 DOF)
- **[21:28]** - right hand joints (7 DOF)
- **[28:31]** - waist XYZ or position (3 DOF)
- **[31:32]** - base height command (1 DOF)
- **[32:35]** - navigate command VX/VY/VYAW (3 DOF)
- **[35]** - reserved

### WBC Action Dict (converted output)
Dict with keys matching WBC environment expectation:
```python
{
    "action.left_arm": np.ndarray(shape=(1, 30, 7), dtype=float32),
    "action.right_arm": np.ndarray(shape=(1, 30, 7), dtype=float32),
    "action.left_hand": np.ndarray(shape=(1, 30, 7), dtype=float32),
    "action.right_hand": np.ndarray(shape=(1, 30, 7), dtype=float32),
    "action.waist": np.ndarray(shape=(1, 30, 3), dtype=float32),
    "action.base_height_command": np.ndarray(shape=(1, 30, 1), dtype=float32),
    "action.navigate_command": np.ndarray(shape=(1, 30, 3), dtype=float32),
}
```

Shape breakdown:
- **First dimension (1)**: Batch size (SyncVectorEnv always = 1)
- **Second dimension (30)**: Action horizon (number of timesteps)
- **Third dimension (N)**: DOF count for that action type

## Troubleshooting

### Error: "Connection refused" to Psi0 server
**Cause**: Psi0 server not running or wrong URL
**Fix**: 
- Verify Psi0 server is running: `docker ps | grep psi0`
- Check URL matches server binding: `--server-url http://127.0.0.1:22085/act`
- Confirm network connectivity from container to server

### Error: "Unexpected Psi0 response" or malformed JSON
**Cause**: Server crash or invalid request payload
**Fix**:
- Check Psi0 server logs: `docker logs <psi0_container>`
- Validate request image is uint8, state is float32
- Check instruction string is valid UTF-8

### Error: Module "gr00t_wbc" not found
**Cause**: PYTHONPATH not set correctly
**Fix**: Ensure all paths from MINIMAL_WORKING_STEPS are in PYTHONPATH

### Error: "Expected action shape (30, 36), got X"
**Cause**: Psi0 server config mismatch or old model
**Fix**:
- Verify Psi0 server is correctly configured for 30-timestep horizon
- Restart Psi0 server with correct horizon setting
- Check which Psi0 checkpoint is loaded

## Development Notes

### Why Batch Dimension?
The WBC environment uses `gym.vector.SyncVectorEnv`, which wraps observations with a batch dimension. Even for a single environment (batch=1), all observations and actions must have this batch dimension.

### Why 30 Timesteps?
The WBC wrapper `MultiStepConfig(n_action_steps=4, ...)` chunks actions into 30-step horizons. Psi0 must output 30 timesteps to match this. The value is configurable but must match across both systems.

### Converting Between Systems
When integrating with other policy systems or running pure Psi0 inference, use `_convert_psi0_to_wbc_actions()` method to transform output format.

## Next Steps

1. **Longer Rollouts**: Extend probe to run full episodes (100+ steps)
2. **Video Recording**: Add rendering to capture whole-body control in action
3. **Multi-Instruction**: Test with different task descriptions
4. **Performance Metrics**: Add latency/throughput logging
5. **Real Robot Transfer**: Validate control on physical Unitree G1

## References

- GR00T WholeBodyControl: `/workspace/GR00T-WholeBodyControl-dex1/`
- Psi0 Policy: Running on separate server at `http://127.0.0.1:22085/act`
- WBC Environment Docs: See `GR00T_WHOLEBODYCONTROL_DEX1_WORKING_RUNBOOK.md`
