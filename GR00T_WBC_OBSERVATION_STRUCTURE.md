# GR00T Whole Body Control - WBC Environment Observation Structure

## Environment: `gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc`

This document describes the complete observation structure for the GR00T locomotion-manipulation environment when using the WBC (Whole Body Control) setup.

---

## Overview

The environment uses a **hierarchical observation system** with two main components:

1. **Core Robot State Observations** - Joint, velocity, acceleration, and torque data
2. **Task-Specific Observations** - Object state, images, language instructions, and privileged data

---

## Core Robot State Observations

All observations are returned as **numpy arrays** with specific data types and shapes.

### Floating Base (Base/Root Joint)

| Key | Shape | Data Type | Description |
|-----|-------|-----------|-------------|
| `floating_base_pose` | (7,) | float32 | Position (3) + Quaternion in wxyz format (4) of robot base |
| `floating_base_vel` | (6,) | float32 | Linear (3) + Angular (3) velocities of base in body frame |
| `floating_base_acc` | (6,) | float32 | Linear (3) + Angular (3) accelerations of base in body frame |

### Body (Torso, Waist, Legs, Arms) Joint State

| Key | Shape | Data Type | Description |
|-----|-------|-----------|-------------|
| `body_q` | (N_body,) | float32 | Body joint positions (in **joint order**, not actuator order) |
| `body_dq` | (N_body,) | float32 | Body joint velocities |
| `body_ddq` | (N_body,) | float32 | Body joint accelerations |
| `body_tau_est` | (N_body_nu,) | float32 | Estimated body joint torques (actuator forces) |

**Note:** For G1 robot:
- `N_body` = typically 19-23 joints (depending on configuration)
- `N_body_nu` = number of actuated DOFs in body

### Left Hand/Gripper Joint State

| Key | Shape | Data Type | Description |
|-----|-------|-----------|-------------|
| `left_hand_q` | (N_gripper,) | float32 | Left gripper joint positions |
| `left_hand_dq` | (N_gripper,) | float32 | Left gripper joint velocities |
| `left_hand_ddq` | (N_gripper,) | float32 | Left gripper joint accelerations |
| `left_hand_tau_est` | (N_gripper_nu,) | float32 | Estimated left gripper torques |

### Right Hand/Gripper Joint State

| Key | Shape | Data Type | Description |
|-----|-------|-----------|-------------|
| `right_hand_q` | (N_gripper,) | float32 | Right gripper joint positions |
| `right_hand_dq` | (N_gripper,) | float32 | Right gripper joint velocities |
| `right_hand_ddq` | (N_gripper,) | float32 | Right gripper joint accelerations |
| `right_hand_tau_est` | (N_gripper_nu,) | float32 | Estimated right gripper torques |

**Note:** Grippers typically have `N_gripper ≈ 12-16` DOFs each for dexterous hands.

### End-Effector (Wrist) Observations

| Key | Shape | Data Type | Description |
|-----|-------|-----------|-------------|
| `wrist_pose` | (14,) | float32 | Left wrist (7) + Right wrist (7) poses: position (3) + quaternion wxyz (4) each |

---

## Image Observations (Camera Data)

### Default Cameras for G1 Robot

The default camera configuration for G1 includes:

| Camera Name | Mapped Key | Resolution | Format | Description |
|------------|-----------|-----------|--------|-------------|
| `robot0_oak_egoview_image` | `ego_view_image` | 256×256 | RGB uint8 | Egocentric view from robot's head |
| `robot0_oak_left_monoview_image` | `ego_view_left_mono_image` | 256×256 | RGB uint8 | Left monocular view (e.g., arm camera) |
| `robot0_oak_right_monoview_image` | `ego_view_right_mono_image` | 256×256 | RGB uint8 | Right monocular view (e.g., arm camera) |

**Additional recorded format for evaluation:**
- `video.{camera_name}` - Same as `{camera_name}_image` but explicitly marked for video recording

### Runtime Camera Configuration

In `sync_env.py`, you can configure cameras at runtime:

```python
env = SyncEnv(
    env_name="gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc",
    robot_name="G1",
    camera_names=["robot0_oak_egoview"],  # Select which cameras to include
    camera_heights=[256],                 # Height per camera
    camera_widths=[256],                  # Width per camera
)
```

---

## Task-Specific Observations

### Language Instruction

| Key | Data Type | Description |
|-----|-----------|-------------|
| `annotation.human.task_description` or `language.language_instruction` | String | Task instruction, e.g., "pick up the apple, walk left and place the apple on the plate." |

### Privileged Observations (Object State)

These observations provide ground-truth information about manipulated objects:

| Key | Shape | Data Type | Description |
|-----|-------|-----------|-------------|
| `obj_pos` | (3,) | float32 | World position of the object (apple) [x, y, z] |
| `obj_quat` | (4,) | float32 | Quaternion orientation of object in wxyz format |
| `obj_linear_vel` | (3,) | float32 | Linear velocity of object in world frame |
| `obj_angular_vel` | (3,) | float32 | Angular velocity of object in world frame |

**Note:** Privileged observations are only available during training/simulation. They are NOT available in real-robot deployments.

### Time Information

| Key | Data Type | Description |
|-----|-----------|-------------|
| `time` | float32 | Current simulation time |

---

## Complete Observation Dictionary Structure

Here's the complete hierarchy as returned by `env.reset()` or `env.step()`:

```python
observation = {
    # Robot state (core)
    "floating_base_pose": np.array([...]),      # (7,) - pos + quat
    "floating_base_vel": np.array([...]),       # (6,) - lin_vel + ang_vel
    "floating_base_acc": np.array([...]),       # (6,) - lin_acc + ang_acc
    
    # Body joints
    "body_q": np.array([...]),                  # (N,) joint positions
    "body_dq": np.array([...]),                 # (N,) joint velocities
    "body_ddq": np.array([...]),                # (N,) joint accelerations
    "body_tau_est": np.array([...]),            # (M,) joint torques
    
    # Left gripper
    "left_hand_q": np.array([...]),             # (K,) gripper positions
    "left_hand_dq": np.array([...]),            # (K,) gripper velocities
    "left_hand_ddq": np.array([...]),           # (K,) gripper accelerations
    "left_hand_tau_est": np.array([...]),       # (L,) gripper torques
    
    # Right gripper
    "right_hand_q": np.array([...]),            # (K,) gripper positions
    "right_hand_dq": np.array([...]),           # (K,) gripper velocities
    "right_hand_ddq": np.array([...]),          # (K,) gripper accelerations
    "right_hand_tau_est": np.array([...]),      # (L,) gripper torques
    
    # End-effectors
    "wrist_pose": np.array([...]),              # (14,) - left(7) + right(7)
    
    # Images
    "ego_view_image": np.uint8([...]),          # (256, 256, 3) RGB
    "ego_view_left_mono_image": np.uint8([...]),# (256, 256, 3) RGB
    "ego_view_right_mono_image": np.uint8([...]),# (256, 256, 3) RGB
    
    # Video duplicates (for evaluation)
    "video.ego_view": np.uint8([...]),          # (256, 256, 3)
    "video.ego_view_left_mono": np.uint8([...]),# (256, 256, 3)
    "video.ego_view_right_mono": np.uint8([...]),# (256, 256, 3)
    
    # Task-specific
    "annotation.human.task_description": "pick up the apple...",  # String
    "language.language_instruction": "pick up the apple...",      # String
    
    # Privileged observations (training only)
    "obj_pos": np.array([...]),                 # (3,) object position
    "obj_quat": np.array([...]),                # (4,) object orientation
    "obj_linear_vel": np.array([...]),          # (3,) object linear velocity
    "obj_angular_vel": np.array([...]),         # (3,) object angular velocity
    
    # Time
    "time": float32,                            # Simulation time
}
```

---

## Important Notes

### 1. **Joint Order Convention**
- Observations `body_q`, `body_dq`, `body_ddq` are in **joint order** (Pinocchio convention)
- They are automatically converted from the internal MuJoCo/RoboSuite **actuator order**
- This conversion happens in `SyncEnv.observe()`

### 2. **Quaternion Format**
- All quaternions are in **wxyz format** (scalar first), not xyzw
- This matches MuJoCo's internal representation

### 3. **Image Data Type**
- Images are returned as **uint8** in range [0, 255]
- Color format is **RGB** (not BGR)

### 4. **State Conversions**
The `SyncEnv` class converts observations:
- From RoboSuite's internal format
- To Pinocchio joint ordering (to match robot model)
- Body and gripper observations are handled separately then combined

### 5. **Privileged Information**
- Object state observations (`obj_*`) are **only available in simulation**
- Real robot won't have these keys
- Always check if key exists before accessing: `if "obj_pos" in obs:`

### 6. **Floating Base Handling**
If robot uses floating base (free joint):
- Position from MuJoCo qpos[0:3]
- Orientation from MuJoCo qpos[3:7]
If robot uses fixed base or non-free-joint base:
- Position from body frame kinematics
- Velocity/Acceleration set to zero

---

## File References

The observation structure is defined in:

1. **Environment Definition:**
   - `decoupled_wbc/dexmg/gr00trobocasa/robocasa/environments/locomanipulation/locomanip_basic.py`
   - `decoupled_wbc/dexmg/gr00trobocasa/robocasa/environments/locomanipulation/locomanip_dc.py`

2. **Synchronous Environment Wrapper:**
   - `decoupled_wbc/control/envs/robocasa/sync_env.py` - Main observation conversion

3. **RoboCasa Environment:**
   - `decoupled_wbc/control/envs/robocasa/utils/robocasa_env.py` - Raw observation collection

4. **Base Environment (LocoManipulation):**
   - `decoupled_wbc/dexmg/gr00trobocasa/robocasa/environments/locomanipulation/base.py` - Base structure

5. **Camera Configuration:**
   - `decoupled_wbc/control/envs/robocasa/utils/cam_key_converter.py` - Camera name mapping

---

## Usage Example

```python
from decoupled_wbc.control.envs.robocasa.sync_env import SyncEnv

# Create environment
env = SyncEnv(
    env_name="gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc",
    robot_name="G1",
)

# Reset and get initial observation
obs, info = env.reset()

# Access specific observations
robot_pose = obs["floating_base_pose"]      # (7,)
joint_pos = obs["body_q"]                   # (N_body,)
gripper_q = obs["left_hand_q"]              # (12-16,)
image = obs["ego_view_image"]               # (256, 256, 3) uint8
task_instruction = obs["annotation.human.task_description"]
object_position = obs["obj_pos"]            # (3,) - privileged

# Step environment
action = {"q": action_q, "tau": action_tau}  # Both optional
obs, reward, terminated, truncated, info = env.step(action)
```

---

## Key Dimensions for G1 Robot (Typical)

| Component | DOFs | Notes |
|-----------|------|-------|
| Floating Base | 7 | 3 position + 4 quaternion |
| Body Joints | ~19-23 | Waist, legs, torso, neck, etc. |
| Left Gripper | ~12-16 | Dexterous hand with multiple fingers |
| Right Gripper | ~12-16 | Dexterous hand with multiple fingers |
| **Total DOFs** | **~55-65** | Depends on specific configuration |

