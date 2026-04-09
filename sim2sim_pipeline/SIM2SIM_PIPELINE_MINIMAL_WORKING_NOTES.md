# Sim2Sim Pipeline Minimal Working Notes

This file records only the steps that were actually needed and worked on `54.155.29.100`.

## What Worked

### 1. `unitree_mujoco`
Run it inside the ECS workspace container, not on the EC2 host directly.

Use:

```bash
unset ROS_DISTRO AMENT_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH
unset CONDA_PREFIX CONDA_DEFAULT_ENV

cat >/tmp/cyclonedds_noshm.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<CycloneDDS xmlns="https://cdds.io/config">
  <Domain>
    <General>
      <Interfaces>
        <NetworkInterface name="lo" multicast="true" />
      </Interfaces>
      <AllowMulticast>true</AllowMulticast>
      <EnableMulticastLoopback>true</EnableMulticastLoopback>
    </General>
    <SharedMemory>
      <Enable>false</Enable>
    </SharedMemory>
  </Domain>
</CycloneDDS>
EOF

export DISPLAY=:1
export LD_LIBRARY_PATH=/opt/unitree_robotics/lib:/usr/local/lib
export CYCLONEDDS_URI=file:///tmp/cyclonedds_noshm.xml

cd /workspace/unitree_mujoco/simulate/build
./unitree_mujoco -r g1 -s scene_29dof.xml -n lo -i 0
```

Why this fixed it:
- the live `simulate/config.yaml` was still using upstream defaults, so `./unitree_mujoco` by itself was not launching the intended G1 29-DOF sim setup
- `-r g1 -s scene_29dof.xml -i 0 -n lo` forced the robot, scene, DDS domain, and interface to match the G1 sim2sim pipeline
- disabling CycloneDDS shared memory avoided the DDS transport assertion path seen earlier
- removing Conda/ROS/Python environment noise avoided the heap-corruption-style crashes from loading the wrong runtime libraries into a pure C++ binary

### 2. `g1_ctrl --network lo`
It worked only after:
- removing `Military_March` from `config.yaml`
- not running from the active Conda runtime
- using the same no-SHM CycloneDDS config

Use:

```bash
unset ROS_DISTRO AMENT_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH
unset CONDA_PREFIX CONDA_DEFAULT_ENV
export LD_LIBRARY_PATH=/opt/unitree_robotics/lib:/usr/local/lib
export CYCLONEDDS_URI=file:///tmp/cyclonedds_noshm.xml

cd /workspace/unitree_rl_lab/deploy/robots/g1_29dof/build
./g1_ctrl --network lo
```

Why this fixed it:
- launching from `(unitree_sim_env)` made `g1_ctrl` resolve `libstdc++.so.6` and `libgcc_s.so.1` from the Conda env instead of the system runtime, which is what produced the `free(): invalid pointer` crash
- using the reduced `LD_LIBRARY_PATH` forced the controller onto the system C++ runtime plus the Unitree/ONNX libraries it actually needs
- using the same no-SHM CycloneDDS config as `unitree_mujoco` kept both processes on a consistent DDS transport
- removing `Military_March` from `config.yaml` stopped `g1_ctrl` from trying to initialize a policy that was enabled in config but missing its files on disk

### 3. Velocity trigger script
This script was added for the instance workflow:

```bash
python /workspace/unitree_rl_lab/deploy/tools/trigger_velocity.py
```

If already in `FixStand`:

```bash
python /workspace/unitree_rl_lab/deploy/tools/trigger_velocity.py --velocity-only
```

Why this exists:
- it uses the repo’s existing UDP joystick-injector path rather than depending on a physical controller
- it is the smallest way to test whether `g1_ctrl` is receiving control inputs and transitioning state

## Errors And Causes

### `unitree_mujoco` errors
- `dds_writecdr_impl_common: Assertion ...`
  - cause: CycloneDDS shared-memory transport was unstable for this local sim2sim setup
  - fix: disable shared memory in the DDS config
- `corrupted size vs. prev_size`
  - cause: the simulator was being launched from a polluted runtime environment with Conda/ROS/Python library state mixed into a pure C++ process
  - fix: unset those env vars and use a minimal `LD_LIBRARY_PATH`
- aborts/crashes when using just `./unitree_mujoco`
  - cause: the live config file still had upstream defaults instead of the G1 29-DOF settings
  - fix: explicitly pass `-r g1 -s scene_29dof.xml -n lo -i 0`

### `g1_ctrl` errors
- `free(): invalid pointer`
  - cause: `g1_ctrl` was loading the Conda C++ runtime (`libstdc++`, `libgcc_s`) instead of the system one
  - fix: launch outside the active Conda runtime and reduce `LD_LIBRARY_PATH`
- `YAML::BadFile ... military_march/params/deploy.yaml`
  - cause: `Military_March` was enabled in `config.yaml`, but its policy folder on the instance was empty
  - fix: remove `Military_March` from the enabled FSMs and transitions, or restore the missing policy assets

## How To Make This Minimal Later

### Option 1. Patch runtime defaults on the instance
- patch `unitree_mujoco/simulate/config.yaml` to:
  - `robot: "g1"`
  - `robot_scene: "scene_29dof.xml"`
  - `domain_id: 0`
  - `interface: "lo"`
- patch `/tmp` or `/etc` CycloneDDS config to disable shared memory
- keep `Military_March` disabled unless its assets are restored

Result:
- `unitree_mujoco` could become close to:
  - `./unitree_mujoco`
- `g1_ctrl` could become close to:
  - `./g1_ctrl --network lo`

### Option 2. Add wrapper launch scripts
Create two tiny launchers that:
- clean the environment
- set the correct DDS config
- set the correct library path
- call the binaries with the correct defaults

Result:
- operators run one stable command without remembering the exports
- avoids patching system-wide shell state

### Option 3. Make it durable in the image/build
Bake these into the workstation/container build:
- corrected `unitree_mujoco` config
- no-SHM CycloneDDS config for sim2sim
- policy tree consistency checks
- a `launch_sim2sim_*` script pair

This is the cleanest long-term fix.
