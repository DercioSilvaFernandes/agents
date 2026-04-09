# SIM2SIM_PIPELINE Current Task Remediation Log

Reference: follow `agents/sim2sim_pipeline/AGENTS.md` as the operating source of truth for this task.

## Active Scope
- Create the standard task folder for sim2sim work
- Validate safe access to the fixed instance `54.155.29.100`
- Validate startup of `unitree_mujoco` and `g1_ctrl --network lo`
- Do not restart the instance
- Do not modify the policy script in this turn

## Current Working Snapshot
- SSH access works with `/Users/dercio.fernandes/dm-isaac-g1.pem` as `ec2-user`
- Password-based SSH was not accepted by the host
- Active container during validation: `ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901`
- `unitree_mujoco` launched with `DISPLAY=:1` and `CYCLONEDDS_URI=file:///tmp/cyclonedds.xml`
- corrected interactive simulator command is `./unitree_mujoco -r g1 -s scene_29dof.xml -n lo -i 0`
- safest known simulator environment is:
  - disable CycloneDDS shared memory
  - unset ROS/AMENT/PYTHONPATH and Conda env vars
  - set `LD_LIBRARY_PATH=/opt/unitree_robotics/lib:/usr/local/lib`
- `g1_ctrl --network lo` launched from `/workspace/unitree_rl_lab/deploy/robots/g1_29dof/build`
- Controller remained in `Waiting for connection rt/lowstate` during this startup-only validation

## Chronological Entries

### 2026-03-16 14:49 WET
- Command: `nc -vz 54.155.29.100 22`
- Result: SSH port reachable.

### 2026-03-16 14:50 WET
- Commands:
  - `ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no ec2-user@54.155.29.100`
  - `ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no datamentors@54.155.29.100`
- Result: Password-based SSH not accepted on this host.

### 2026-03-16 14:51 WET
- Command: `ssh -o StrictHostKeyChecking=no -o BatchMode=yes -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100 'hostname'`
- Result: Verified SSH key access.

### 2026-03-16 14:52-14:54 WET
- Action: Discovered active container, conda envs, display state, DDS config, and binary presence.
- Result: Containerized runtime confirmed; VNC `:1`, `/tmp/cyclonedds.xml`, `unitree_mujoco`, and `g1_ctrl` all present.

### 2026-03-16 14:56 WET
- Command:
```bash
docker exec -d ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc '
  export DISPLAY=:1
  export CYCLONEDDS_URI=file:///tmp/cyclonedds.xml
  cd /workspace/unitree_mujoco/simulate/build
  exec ./unitree_mujoco -r g1 -n lo >/tmp/unitree_mujoco.log 2>&1
'
```
- Result: Simulator started and stayed alive.

### 2026-03-16 14:56-14:57 WET
- Command:
```bash
docker exec -d ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc '
  export CYCLONEDDS_URI=file:///tmp/cyclonedds.xml
  cd /workspace/unitree_rl_lab/deploy/robots/g1_29dof/build
  exec ./g1_ctrl --network lo >/tmp/g1_ctrl.log 2>&1
'
```
- Result: Controller started and stayed alive, but full DDS handshake was not yet confirmed.

### 2026-03-16 14:58-15:00 WET
- Action: Created the task folder files and captured the validated startup path in the runbook.
- Result: Persistent documentation added under `agents/sim2sim_pipeline/`.

### 2026-03-16 15:01 WET
- Command: `docker exec ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc 'kill 1711 1774'`
- Result: Stopped the detached validation processes so the instance was not left with background sim/controller jobs.

### 2026-03-16 15:36-15:40 WET
- Actions:
  - inspected `/workspace/unitree_mujoco/simulate/config.yaml`
  - re-ran `unitree_mujoco` interactively with `-r g1 -s scene_29dof.xml -n lo -i 0`
- Result:
  - found config defaults were still `go2`, `scene.xml`, `domain_id: 1`
  - interactive G1 launch with corrected scene/domain stayed alive until manually interrupted
  - previous detached-only simulator validation was too weak

### 2026-03-16 15:48-15:55 WET
- Actions:
  - created a temporary DDS config with `<SharedMemory><Enable>false</Enable></SharedMemory>`
  - launched `unitree_mujoco` under a clean `env -i` environment with only `DISPLAY`, `LD_LIBRARY_PATH`, and `CYCLONEDDS_URI`
- Result:
  - simulator survived until timeout without allocator or DDS assertion failures during the test window
  - current best-known workaround is to strip the environment and disable DDS shared memory before launch

### 2026-03-16 16:05-16:10 WET
- Actions:
  - created `unitree_rl_lab/deploy/tools/trigger_velocity.py`
  - created `agents/sim2sim_pipeline/SIM2SIM_PIPELINE_MINIMAL_WORKING_NOTES.md`
  - copied `trigger_velocity.py` into `/workspace/unitree_rl_lab/deploy/tools/trigger_velocity.py` inside the active container
  - verified script syntax and CLI help remotely
- Result:
  - instance now has a minimal UDP trigger script for `Passive -> FixStand -> Velocity`
  - minimal notes file now exists with only the validated working steps and the shortest path toward durable wrappers/defaults
