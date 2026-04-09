# SIM2SIM_PIPELINE Remediation Log

## Minimal Working Procedure
> This section reflects the validated startup scope from this session, not full end-to-end mimic playback.

### Environment Summary
- Timestamp: 2026-03-16 14:58:40 WET
- Target instance: `54.155.29.100`
- SSH user: `ec2-user`
- Verified access path: `ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100`
- Active container during validation: `ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901`
- Repo path in container: `/workspace/dm-isaac-g1`
- Repo commit: `980e1e4`
- Conda envs: `base`, `gmr`, `phmr`, `unitree_sim_env`
- DDS config: `/tmp/cyclonedds.xml`
- Display for MuJoCo: `:1`

### Simulator Startup
```bash
ssh -o StrictHostKeyChecking=no -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100

docker exec -it ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc '
  export DISPLAY=:1
  export CYCLONEDDS_URI=file:///tmp/cyclonedds.xml
  cd /workspace/unitree_mujoco/simulate/build
  ./unitree_mujoco -r g1 -s scene_29dof.xml -n lo -i 0
'
```

Result:
- interactive simulator session stayed alive until manually interrupted
- terminal showed `MuJoCo version 3.2.6`
- terminal showed G1 links, joints, actuators, and sensors loading
- required correction discovered: live `simulate/config.yaml` is still on upstream defaults (`go2`, `scene.xml`, `domain_id: 1`)
- stronger stable launch recipe discovered later:
  - disable CycloneDDS shared memory
  - unset ROS/AMENT/Python/Conda env vars
  - set `LD_LIBRARY_PATH=/opt/unitree_robotics/lib:/usr/local/lib`

### Controller Startup
```bash
docker exec -d ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc '
  export CYCLONEDDS_URI=file:///tmp/cyclonedds.xml
  cd /workspace/unitree_rl_lab/deploy/robots/g1_29dof/build
  exec ./g1_ctrl --network lo >/tmp/g1_ctrl.log 2>&1
'
```

Result:
- process stayed alive
- banner printed for `G1-29dof Controller`
- controller remained at `Waiting for connection to robot...`
- no policy trigger or `tempganga.py` validation was attempted in this turn

## Chronological Log

### 2026-03-16 14:40-14:48 WET
- Action: Read `agents/FOLDER_CREATION_GUIDE.md`, `agents/video2robot/*`, `cloud/ecs/GUIDE.md`, `docs/SSH.md`, and local sim2sim references.
- Reason: Build the new task folder from the repo's established structure and reuse validated sim2sim conventions.
- Result: Confirmed the folder template, existing sim2sim docs, and current `g1_29dof` config structure.
- Classification: local documentation discovery

### 2026-03-16 14:49 WET
- Command:
```bash
nc -vz 54.155.29.100 22
```
- Reason: Confirm basic SSH reachability before attempting remote validation.
- Result: Port `22` reachable.
- Classification: live-only

### 2026-03-16 14:50 WET
- Commands attempted:
```bash
ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no ec2-user@54.155.29.100
ssh -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no datamentors@54.155.29.100
```
- Reason: Test whether the operator-provided password path was usable.
- Result: Both failed with `Permission denied (publickey,gssapi-keyex,gssapi-with-mic)`.
- Conclusion: Password-based SSH is not enabled on the validated host.
- Classification: live-only failed attempt

### 2026-03-16 14:51 WET
- Command:
```bash
ssh -o StrictHostKeyChecking=no -o BatchMode=yes -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@54.155.29.100 'hostname'
```
- Reason: Test the project SSH key as a fallback access path.
- Result: Success. Verified key-based SSH access to the instance.
- Classification: live-only

### 2026-03-16 14:52-14:54 WET
- Commands: remote discovery via `docker ps`, `conda env list`, binary presence checks, and DDS/display checks inside the active container.
- Reason: Determine whether sim2sim runs on the EC2 host or inside the container, and verify prerequisites before launch.
- Result:
  - host itself does not contain the working repos
  - active workspace runs inside `ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901`
  - conda envs present: `base`, `gmr`, `phmr`, `unitree_sim_env`
  - `DISPLAY` unset by default in `docker exec`
  - TurboVNC `:1` present
  - `/tmp/cyclonedds.xml` present
  - `unitree_mujoco` and `g1_ctrl` binaries present
- Classification: live-only

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
- Reason: Validate simulator startup over SSH without opening an interactive GUI session locally.
- Result: This was an incomplete validation method. Later retesting showed detached startup was not sufficient proof that the viewer/process was healthy.
- Classification: live-only superseded validation

### 2026-03-16 14:56-14:57 WET
- Command:
```bash
docker exec -d ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc '
  export CYCLONEDDS_URI=file:///tmp/cyclonedds.xml
  cd /workspace/unitree_rl_lab/deploy/robots/g1_29dof/build
  exec ./g1_ctrl --network lo >/tmp/g1_ctrl.log 2>&1
'
```
- Reason: Validate controller startup from the user-requested build directory.
- Result: Controller process remained alive and printed startup banner, but stayed at `Waiting for connection rt/lowstate`.
- Classification: live-only partial validation

### 2026-03-16 14:58-15:00 WET
- Action: Created `agents/sim2sim_pipeline/` with the standard five-file structure and documented the validated remote access and launch path.
- Reason: Deliver the requested task folder in the repo's required format.
- Result: New task folder created with operator instructions, mission scope, runbook, and logs.
- Classification: persistent repo change

### 2026-03-16 15:01 WET
- Command:
```bash
docker exec ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc 'kill 1711 1774'
```
- Reason: Leave the remote instance in a neutral state after startup validation instead of keeping detached simulator/controller processes running.
- Result: Validation processes stopped cleanly.
- Classification: live-only cleanup

### 2026-03-16 15:36-15:40 WET
- Commands:
```bash
docker exec ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc 'sed -n "1,40p" /workspace/unitree_mujoco/simulate/config.yaml'

docker exec -it ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc '
  export DISPLAY=:1
  export CYCLONEDDS_URI=file:///tmp/cyclonedds.xml
  cd /workspace/unitree_mujoco/simulate/build
  ./unitree_mujoco -r g1 -s scene_29dof.xml -n lo -i 0
'
```
- Reason: Re-check the user-reported simulator abort more rigorously.
- Result:
  - confirmed live `simulate/config.yaml` still has upstream defaults: `go2`, `scene.xml`, `domain_id: 1`
  - confirmed interactive simulator startup with `DISPLAY=:1`, `scene_29dof.xml`, and domain `0` stays alive until manually interrupted
  - conclusion: the earlier detached test overstated confidence, and the simulator should be treated as requiring corrected G1 launch arguments or a config patch
- Classification: live-only corrected validation

### 2026-03-16 15:48-15:55 WET
- Commands:
```bash
docker exec ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc '
  printf %s "<?xml version=\"1.0\" encoding=\"UTF-8\"?><CycloneDDS xmlns=\"https://cdds.io/config\"><Domain><General><Interfaces><NetworkInterface name=\"lo\" multicast=\"true\" /></Interfaces><AllowMulticast>true</AllowMulticast><EnableMulticastLoopback>true</EnableMulticastLoopback></General><SharedMemory><Enable>false</Enable></SharedMemory></Domain></CycloneDDS>" > /tmp/cyclonedds_noshm.xml
'

docker exec ecs-dm-interactive-shell-138-workspace-98a4da9dbeacedd8f901 bash -lc '
  env -i \
    HOME=/root \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    DISPLAY=:1 \
    LD_LIBRARY_PATH=/opt/unitree_robotics/lib:/usr/local/lib \
    CYCLONEDDS_URI=file:///tmp/cyclonedds_noshm.xml \
    bash -lc "cd /workspace/unitree_mujoco/simulate/build && timeout -s INT 12 ./unitree_mujoco -r g1 -s scene_29dof.xml -n lo -i 0"
'
```
- Reason: Investigate later heap-corruption-style crashes (`corrupted size vs. prev_size`) with the most conservative runtime environment.
- Result:
  - simulator stayed alive until timeout `124`
  - no heap-corruption or DDS assertion occurred during this validation window
  - conclusion: the safest known launch path is a clean environment plus disabled CycloneDDS shared memory plus corrected G1 scene/domain
- Classification: live-only corrected validation

### 2026-03-16 16:05-16:10 WET
- Actions:
  - added local script `unitree_rl_lab/deploy/tools/trigger_velocity.py`
  - added concise note file `agents/sim2sim_pipeline/SIM2SIM_PIPELINE_MINIMAL_WORKING_NOTES.md`
  - copied `trigger_velocity.py` into the live container at `/workspace/unitree_rl_lab/deploy/tools/trigger_velocity.py`
  - verified the script with `python3 -m py_compile` and `--help`
- Reason: Provide a minimal UDP trigger to test the `g1_ctrl` joystick-injector path and capture only the steps that actually worked.
- Result:
  - script is available on the instance
  - script supports full `Passive -> FixStand -> Velocity` and `--velocity-only`
  - validation in this turn was syntax/help-level only; live FSM transition was not forced by me
- Classification: persistent repo change plus live-only container sync

## Current Status
- Completed for this turn:
  - task folder creation
  - remote host access validation
  - simulator startup validation
  - controller startup validation
- Not completed in this turn:
  - new mimic policy folder creation under `config/policy/mimic/<task_name>/`
  - `config.yaml` edits for a new policy ID
  - `tempganga.py` execution
  - end-to-end video-based motion playback in sim2sim
