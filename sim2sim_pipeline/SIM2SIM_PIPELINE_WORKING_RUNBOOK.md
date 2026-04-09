# Sim2Sim Pipeline Working Runbook

## Purpose
This runbook captures the real command path that was validated for starting the G1 sim2sim components on the fixed remote instance `54.155.29.100`.

It is not a generic upstream guide. It documents the access and launch sequence that matched the live host in this workspace.

## Scope
- Remote host: `54.155.29.100`
- Access method: SSH with `/Users/dercio.fernandes/dm-isaac-g1.pem`
- Runtime location: active ECS workspace container
- Validated components:
  - `unitree_mujoco`
  - `g1_ctrl --network lo`
- Deferred components:
  - new mimic policy folder creation
  - `config.yaml` mutation for a new policy
  - `tempganga.py`

## Preconditions
- Do not restart the instance.
- Confirm SSH key access works.
- Confirm the workspace container is running.
- Confirm `/tmp/cyclonedds.xml` exists in the container.
- Confirm TurboVNC display `:1` is running in the container.

## Expected Steady-State Outcome
- MuJoCo simulator process starts inside the container and stays alive
- controller process starts inside the container and stays alive with `--network lo`
- logs are available in `/tmp/unitree_mujoco.log` and `/tmp/g1_ctrl.log`

## 1. Connect To The Fixed Host

```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100
```

Do not use password-only SSH as the primary path for this task.

## 2. Discover The Active Workspace Container

```bash
docker ps --format '{{.Names}} {{.Status}}'
```

Validated container during this session:

```bash
ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901
```

For the rest of this runbook, replace `<container>` with the active name from `docker ps`.

## 3. Baseline Discovery Inside The Container

```bash
docker exec <container> bash -lc '
  conda env list
  echo DISPLAY=$DISPLAY
  ls -l /tmp/cyclonedds.xml /etc/cyclonedds.xml
  test -f /workspace/unitree_mujoco/simulate/build/unitree_mujoco && echo MUJOCO_OK
  test -f /workspace/unitree_rl_lab/deploy/robots/g1_29dof/build/g1_ctrl && echo G1_CTRL_OK
  ps -ef | grep -E "Xvnc|Xtigervnc|vncserver" | grep -v grep || true
'
```

Validated findings:
- conda envs present: `base`, `gmr`, `phmr`, `unitree_sim_env`
- `DISPLAY` is not set by default in non-interactive `docker exec` shells
- both binaries are present
- VNC server is running on display `:1`

## 4. Terminal 1: Start MuJoCo Simulator

Interactive form:

```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100

docker exec -it <container> bash -lc '
  unset ROS_DISTRO AMENT_PREFIX_PATH CMAKE_PREFIX_PATH PYTHONPATH
  unset CONDA_PREFIX CONDA_DEFAULT_ENV
  export DISPLAY=:1
  export LD_LIBRARY_PATH=/opt/unitree_robotics/lib:/usr/local/lib
  export CYCLONEDDS_URI='\''<CycloneDDS xmlns="https://cdds.io/config"><Domain><General><Interfaces><NetworkInterface name="lo" multicast="true" /></Interfaces><AllowMulticast>true</AllowMulticast><EnableMulticastLoopback>true</EnableMulticastLoopback></General><SharedMemory><Enable>false</Enable></SharedMemory></Domain></CycloneDDS>'\''
  cd /workspace/unitree_mujoco/simulate/build
  ./unitree_mujoco -r g1 -s scene_29dof.xml -n lo -i 0
'
```

Why the extra flags matter on this instance:
- live `simulate/config.yaml` still contains upstream defaults:
  - `robot: "go2"`
  - `robot_scene: "scene.xml"`
  - `domain_id: 1`
- for G1 sim2sim, use `scene_29dof.xml` and DDS domain `0`
- CycloneDDS shared memory must be disabled for this workflow
- the container's default Python/Conda environment is noisy for this pure C++ binary
- running the simulator through a non-interactive detached shell was not a reliable validation method here

Inspection command:

```bash
docker exec <container> bash -lc 'sed -n "1,40p" /workspace/unitree_mujoco/simulate/config.yaml'
```

Detached form is useful only for short process checks, not as proof that the viewer is healthy:

```bash
docker exec -d <container> bash -lc '
  export DISPLAY=:1
  export CYCLONEDDS_URI=file:///tmp/cyclonedds.xml
  cd /workspace/unitree_mujoco/simulate/build
  exec ./unitree_mujoco -r g1 -s scene_29dof.xml -n lo -i 0 >/tmp/unitree_mujoco.log 2>&1
'
```

Validation:

```bash
docker exec <container> bash -lc '
  ps -ef | grep unitree_mujoco | grep -v grep
  sed -n "1,40p" /tmp/unitree_mujoco.log
'
```

Expected signs:
- process remains alive
- log shows `MuJoCo version 3.2.6`
- log shows robot links/joints loading
- interactive session stays open instead of aborting after sensor enumeration

## 5. Terminal 2: Start The Controller

Interactive form:

```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100

docker exec -it <container> bash -lc '
  export CYCLONEDDS_URI=file:///tmp/cyclonedds.xml
  cd /workspace/unitree_rl_lab/deploy/robots/g1_29dof/build
  ./g1_ctrl --network lo
'
```

Detached validation form used during this session:

```bash
docker exec -d <container> bash -lc '
  export CYCLONEDDS_URI=file:///tmp/cyclonedds.xml
  cd /workspace/unitree_rl_lab/deploy/robots/g1_29dof/build
  exec ./g1_ctrl --network lo >/tmp/g1_ctrl.log 2>&1
'
```

Validation:

```bash
docker exec <container> bash -lc '
  ps -ef | grep g1_ctrl | grep -v grep
  sed -n "1,80p" /tmp/g1_ctrl.log
'
```

Validated signs from this session:
- process remained alive
- startup banner printed
- controller entered `Waiting for connection to robot...`
- warning `Waiting for connection rt/lowstate` remained during this startup-only validation

## 6. Future Policy Preparation
When you are ready to wire in a new mimic policy, use the following target layout:

```text
/workspace/unitree_rl_lab/deploy/robots/g1_29dof/config/policy/mimic/<task_name>/
├── exported/
└── params/
```

Then edit:

```text
/workspace/unitree_rl_lab/deploy/robots/g1_29dof/config/config.yaml
```

Required future changes:
- add a unique mimic FSM ID under `FSM._`
- add the new mimic state block
- point `motion_file` at `params/...`
- point `policy_dir` at `config/policy/mimic/<task_name>/`
- update controller input transitions if the new state needs a distinct trigger

## 7. Future Terminal 3
The user-provided target flow expects:

```bash
python tempganga.py
```

That script was intentionally not modified or validated in this turn.

## Troubleshooting
- `Permission denied (publickey,...)` with password attempts:
  - use the SSH key; password auth is not the validated path on this host
- `DISPLAY=` is empty inside `docker exec`:
  - export `DISPLAY=:1` before starting MuJoCo
- `unitree_mujoco` aborts after sensor listing:
  - inspect `/workspace/unitree_mujoco/simulate/config.yaml`
  - do not rely on upstream defaults (`go2`, `scene.xml`, `domain_id: 1`)
  - launch with `-r g1 -s scene_29dof.xml -n lo -i 0`
  - disable CycloneDDS shared memory
  - unset ROS/AMENT/PYTHONPATH and Conda env vars
  - set `LD_LIBRARY_PATH=/opt/unitree_robotics/lib:/usr/local/lib`
  - run from an interactive `docker exec -it` shell with `DISPLAY=:1`
- `selected interface "lo" is not multicast-capable`:
  - expected warning on loopback; not itself a blocker
- `g1_ctrl` waits on `rt/lowstate`:
  - simulator and controller started, but DDS handshake is not yet confirmed end-to-end in this task
- host paths such as `/workspace/unitree_mujoco` missing:
  - run inside the ECS workspace container, not on the EC2 host directly
