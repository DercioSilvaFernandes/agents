# Video2Robot Working Runbook

## Purpose
This runbook captures the practical sequence that got `video2robot` working on fresh ECS workspaces.

It is not a generic upstream install guide. It is the dm-isaac-g1 operator procedure that matched the real failures seen on our ECS GPU containers.

## Scope
- Target repo path inside the workspace: `/workspace/video2robot`
- Target runtime: ECS interactive workspace container
- Target workflows:
  - non-GUI pipeline
  - GUI/API pipeline
  - `viser` visualization reachability

## Preconditions
- AWS access works for ECS/EC2 discovery.
- SSH access works with `/Users/dercio.fernandes/dm-isaac-g1.pem`.
- The ECS workspace container is running.
- You have operator access for gated SMPL and SMPL-X downloads.
- You have a local cache for the large PromptHMR checkpoints, or another sanctioned transfer path for them.

## Expected Steady-State Outcome
- `python -m uvicorn web.app:app --host 0.0.0.0 --port 8000` works from `/workspace/video2robot`
- `scripts/run_pipeline.py --video ... --robot unitree_g1 --static-camera` completes
- GUI upload, pose extraction, and retargeting complete on port `8000`
- `viser` is reachable on fixed port `8789`

## 1. Discover The Active Workspace
Do not trust an old public IP. Find the current ECS GPU hosts first.

```bash
AWS_PROFILE=Trainee-260464233120 ./cloud/ecs/run.sh status

AWS_PROFILE=Trainee-260464233120 aws --region eu-west-1 ec2 describe-instances \
  --filters 'Name=tag:Name,Values=dm-isaac-g1-gpu*' \
  --query 'Reservations[].Instances[].{InstanceId:InstanceId,State:State.Name,PublicIp:PublicIpAddress,LaunchTime:LaunchTime}' \
  --output table
```

Pick a reachable public IP, then connect:

```bash
ssh -i /Users/dercio.fernandes/dm-isaac-g1.pem ec2-user@<active-public-ip>
```

Inside the host, identify the running workspace container:

```bash
docker ps --format '{{.Names}}'
```

## 2. Baseline Checks Inside The Container
Run baseline discovery before changing anything:

```bash
docker exec <workspace-container> bash -lc '
  hostname
  cat /etc/os-release
  nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
  which conda
  conda env list
  cd /workspace/video2robot
  git rev-parse HEAD
  ps -ef | grep -E "video2robot|uvicorn|jupyter|code-server" | grep -v grep
'
```

Confirm:
- `/workspace/video2robot` exists
- conda envs `phmr`, `gmr`, and `unitree_sim_env` exist
- the auth wrapper on `8000` is already running, or can be started manually

## 3. Repair Runtime Dependencies
Fresh workspaces were missing pieces needed by upstream bootstrap.

Install the missing system/runtime pieces inside the container:

```bash
docker exec <workspace-container> bash -lc '
  apt-get update
  apt-get install -y ffmpeg
  /opt/conda/bin/pip install gdown
  cd /workspace/video2robot
  conda run -n gmr pip install -e third_party/GMR
'
```

Validate the critical bits:

```bash
docker exec <workspace-container> bash -lc '
  which ffmpeg
  which ffprobe
  /opt/conda/bin/python -c "import gdown"
  conda run -n gmr python -c "import general_motion_retargeting, rich"
'
```

## 4. Provision Gated Body Models
PromptHMR will not run without the gated body-model assets.

Inside the repo:

```bash
docker exec -it <workspace-container> bash -lc '
  cd /workspace/video2robot/third_party/PromptHMR
  bash scripts/fetch_smplx.sh
'
```

Use sanctioned operator credentials at the MPG prompts when asked.

Confirm the required files exist afterward:

```bash
docker exec <workspace-container> bash -lc '
  test -f /workspace/video2robot/third_party/PromptHMR/data/body_models/smplx/SMPLX_NEUTRAL.npz &&
  test -f /workspace/video2robot/third_party/PromptHMR/data/body_models/smpl/SMPL_NEUTRAL.pkl &&
  echo BODY_MODELS_OK
'
```

## 5. Stage PromptHMR Checkpoints And Public Assets
The public PromptHMR downloads were not enough on their own, and some Google Drive fetches were rate-limited.

Required cached assets used during remediation:
- `droidcalib.pth`
- `phmr-config.yaml`
- `prhmr_release_002.ckpt`
- `prhmr_release_002.yaml`
- `smplx2smpl.pkl`
- `smplx2smpl_joints.npy`
- `vitpose-h-coco_25.pth`
- `video2robot-checkpoint.ckpt`

Copy them onto the host, then into the container, then stage them into the upstream locations expected by PromptHMR and `video2robot`.

At minimum, make sure these destinations are populated:
- `/workspace/video2robot/third_party/PromptHMR/data/pretrain/`
- `/workspace/video2robot/checkpoints/`

Also mirror PromptHMR SMPL-X assets into GMR:

```bash
docker exec <workspace-container> bash -lc '
  mkdir -p /workspace/video2robot/third_party/GMR/assets/body_models/smplx
  cp -r /workspace/video2robot/third_party/PromptHMR/data/body_models/smplx/. \
    /workspace/video2robot/third_party/GMR/assets/body_models/smplx/
'
```

## 6. Apply The Live Compatibility Overlay
These were the live code fixes required to make the current upstream checkout work in this environment.

### 6.1 PromptHMR tracker for static-camera flow
File: `third_party/PromptHMR/pipeline/config.yaml`

Change:
- `tracker: sam2`
- to `tracker: bytetrack`

Reason:
- the validated static-camera path worked with ByteTrack in this environment

### 6.2 Non-strict PromptHMR checkpoint loading
File: `third_party/PromptHMR/prompt_hmr/__init__.py`

Change:
- make both relevant `load_state_dict(...)` calls use `strict=False`

Reason:
- checkpoint/key drift blocked startup otherwise

### 6.3 Optional `smplx2smpl` auxiliary assets
File: `third_party/PromptHMR/prompt_hmr/smpl_family/smpl_wrapper.py`

Change:
- import `os`
- guard the `smplx2smpl_joints.npy` dependency so startup does not hard-fail when that side asset is missing

File: `third_party/PromptHMR/prompt_hmr/models/phmr.py`

Change:
- import `os`
- make SMPL and `smplx2smpl.pkl` loading optional
- guard SMPL-derived outputs when those side assets are absent

Reason:
- the environment could proceed with the validated flow once hard assertions were removed

### 6.4 GMR shape/expression compatibility
File: `third_party/GMR/general_motion_retargeting/utils/smpl.py`

Change:
- pad or truncate `betas` and `expression` to match the model dimensions

Reason:
- PromptHMR and GMR shape payloads did not line up cleanly on the tested assets

### 6.5 Compatibility symlink expected by PromptHMR
Create:

```bash
docker exec <workspace-container> bash -lc '
  ln -sfn /workspace/video2robot/third_party/PromptHMR /code
'
```

Reason:
- some upstream paths still expected `/code`

### 6.6 Fixed `viser` port and visible video frame
File: `web/viser_manager.py`

Change:
- force `viser` to use fixed port `8789` instead of a random high port

File: `video2robot/visualization/robot_viser.py`

Change:
- add a visible GUI image for the current decoded frame, not only the textured camera frustum

Reason:
- random `viser` ports were unreachable externally through the EC2 security group
- the video was decoding, but the presentation was too easy to miss

## 7. Ensure Network Exposure For Viser
The security group must expose the fixed `viser` port.

Required inbound rule:
- TCP `8789`

Without that rule, the GUI can look idle even when the backend thinks the `viser` session is healthy.

## 8. Use The Correct Manual Server Command
From `/workspace/video2robot`, the working direct command is:

```bash
python -m uvicorn web.app:app --host 0.0.0.0 --port 8000
```

Do not use:

```bash
uvicorn app:app
```

That fails because `web/app.py` uses package-relative imports and must be imported as `web.app`.

## 9. Validate The Non-GUI Flow
Create a stable local test input path:

```bash
mkdir -p /workspace/video2robot/data/test_inputs
curl -L --fail \
  --output /workspace/video2robot/data/test_inputs/upstream_demo_dance.mp4 \
  https://github.com/user-attachments/assets/94e6d12d-afae-4300-8c5c-c244ad208bdb
```

Run the validated CLI path:

```bash
cd /workspace/video2robot
conda run -n gmr python scripts/run_pipeline.py \
  --video /workspace/video2robot/data/test_inputs/upstream_demo_dance.mp4 \
  --name integration_demo_static \
  --robot unitree_g1 \
  --force \
  --static-camera
```

Expected outputs under `/workspace/video2robot/data/integration_demo_static` include:
- `results.pkl`
- `world4d.glb`
- `smplx.npz`
- `smplx_track_*.npz`
- `robot_motion.pkl`
- `robot_motion_twist.pkl`

## 10. Validate The GUI/API Flow
If the wrapper is already running on `8000`, use it. Otherwise start the app manually with the command in section 8.

Authenticated API validation sequence:

```bash
BASE_URL=http://<active-public-ip>:8000
AUTH="operator:${SERVICE_PASSWORD}"

curl -u "$AUTH" "$BASE_URL/health"

curl -u "$AUTH" -X POST "$BASE_URL/api/projects" \
  -H "Content-Type: application/json" \
  -d '{"name":"gui_integration_static"}'

curl -u "$AUTH" -X POST "$BASE_URL/api/files/upload/gui_integration_static" \
  -F "file=@/workspace/video2robot/data/test_inputs/upstream_demo_dance.mp4"

curl -u "$AUTH" -X POST "$BASE_URL/api/pipeline/extract-pose" \
  -H "Content-Type: application/json" \
  -d '{"project":"gui_integration_static","static_camera":true}'

curl -u "$AUTH" -X POST "$BASE_URL/api/pipeline/retarget" \
  -H "Content-Type: application/json" \
  -d '{"project":"gui_integration_static","robot_type":"unitree_g1","all_tracks":true}'

curl -u "$AUTH" "$BASE_URL/api/pipeline/tasks?project=gui_integration_static"
```

Success means:
- `/health` returns `200`
- upload succeeds
- `extract-pose` completes
- `retarget` completes

## 11. Validate Viser
After a successful project run, start the viewer through the API:

```bash
curl -u "$AUTH" -X POST "$BASE_URL/api/viser/start" \
  -H "Content-Type: application/json" \
  -d '{"project":"integration_demo_static"}'

curl -u "$AUTH" "$BASE_URL/api/viser/status"
```

Expected:
- backend reports `running`
- the browser can actually reach `http://<active-public-ip>:8789`
- the `Video frame` panel shows decoded frames

## 12. Operational Warnings
- Do not assume the previous ECS public IP is still valid.
- Do not assume the previous workspace password is still valid after task rotation.
- Do not casually restart the auth wrapper inside the ECS workspace. One live attempt killed the running workspace task and forced ECS to reschedule it elsewhere.
- Keep the remediation log current while you work. The runbook is the stable procedure; the log is the execution evidence.

## 13. Durable Repo Follow-Ups
These repo-side fixes were already identified as worth keeping:
- install system `ffmpeg` and `ffprobe`
- install `gdown`
- install `third_party/GMR` editable into the `gmr` env
- keep the ECS guide aligned with `python -m uvicorn web.app:app`

These still need a durable upstream/bootstrap strategy outside this runbook:
- sanctioned provisioning for gated SMPL/SMPL-X assets
- sanctioned provisioning for the large PromptHMR checkpoints
- a reproducible way to apply the live PromptHMR/GMR compatibility overlay on fresh workspaces
- a durable fixed-port `viser` configuration in the upstream workspace bootstrap
