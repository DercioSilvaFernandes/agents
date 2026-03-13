# Video2Robot Integration Enablement Task

## Objective
Integrate and validate the `video2robot` pipeline on this instance so that both:
- the non-GUI pipeline
- the GUI/web pipeline

can run successfully.

The task is not complete when blockers are merely identified.
Fix blockers when possible and document the full fixing process so the environment can be reproduced reliably on future instances.

## Primary Target
Upstream repository:
- `https://github.com/AIM-Intelligence/video2robot`

dm-isaac-g1 context:
- In the workstation/ECS images, `video2robot` is baked into `/workspace/video2robot`.
- Conda envs `phmr` (PromptHMR) and `gmr` (GMR) are created on the workstation/ECS images.
- The web UI is exposed on port `8000` via a small auth wrapper script (`video2robot-server.py`) that wraps the upstream FastAPI app.

Primary target capabilities to make work:
1. non-GUI pipeline (PromptHMR + GMR) using the two-stage CLI that dm-isaac-g1 documents:
   - `conda activate phmr && python scripts/extract_pose.py --video <local_video_path> --output <poses_dir>`
   - `conda activate gmr && python scripts/retarget.py --input <poses_dir> --robot unitree_g1 --output <retarget_dir>`
   - optionally, if present, the upstream wrapper:
     - `python scripts/run_pipeline.py --video <local_video_path>`
2. GUI/web pipeline using the FastAPI app:
   - direct: `uvicorn web.app:app --host 0.0.0.0 --port 8000`
   - in dm-isaac-g1 containers: via `video2robot-server.py` on `http://<host>:8000` with HTTP Basic Auth (password from `SERVICE_PASSWORD`)

## Upstream Expectations to Respect
According to the upstream README:
- the repo uses submodules
- the repo expects two conda environments:
  - `gmr`
  - `phmr`
- the full pipeline can start from an existing local video via `--video`
- the web UI is started with `uvicorn web.app:app`
- `.env` may be required for API-backed features
- PromptHMR and GMR have their own environment/setup requirements

Follow the upstream README first before inventing custom setup paths.

## Success Criteria
Success means all of the following are true:

### Non-GUI success
- the repo is cloned correctly with submodules
- all required environments and dependencies are installed (including `phmr` and `gmr` where applicable)
- a local test video containing a visible person exists in the workspace
- the non-GUI pipeline runs end-to-end using either:
  - the two-stage CLI: `extract_pose.py` (phmr) then `retarget.py` (gmr), as documented in `cloud/ecs/GUIDE.md`, or
  - the upstream wrapper: `python scripts/run_pipeline.py --video <local_video_path>`
- produced outputs and project artifacts are created as expected (pose PKL + retargeted motion)

### GUI success
- the web server starts successfully:
  - either via `uvicorn web.app:app` or
  - via the `video2robot-server.py` auth wrapper on port `8000`
- the UI is reachable from the intended access path for this instance
- the GUI path can accept or use a local video and run the pipeline path successfully
- any GUI-specific dependency, serving, path, or runtime issue is fixed

The task is not complete if only one of the two modes works.

## Required Artifacts
Continuously maintain this remediation log during the task:

- `current_task/VIDEO2ROBOT_REMEDIATION_LOG.md`

Use `agents/video2robot/VIDEO2ROBOT_REMEDIATION_LOG.md` as the template when creating the `current_task/` copy.

That file is the handoff artifact and must remain up to date throughout the debugging session, not only at the end.

## Source of Truth
- This file defines the mission and acceptance criteria.
- The remediation log is the chronological execution history.
- After every meaningful action, update the remediation log first.

## Operating Rules
- Start with environment discovery.
- Read the upstream README before making major changes.
- Prefer diagnosis before mutation, but keep momentum toward a working result.
- Use the smallest fix that unblocks the current failure.
- Keep non-GUI and GUI validation separate so failures are attributable.
- Do not declare success based only on server startup, imports, or package installation.
- Require real validation of both target workflows.

## Mandatory Workflow

### Phase 1 — Discovery
1. Inspect the instance state:
   - OS
   - Python
   - Conda
   - GPU
   - CUDA
   - available disk
   - open ports
   - shell startup behavior
2. Confirm whether the upstream repo is already present.
3. If missing, clone the repo with submodules.
4. Inspect:
   - submodule state
   - existing conda environments
   - system packages that may be needed
   - any existing `.env`
   - whether model weights or caches are already present

### Phase 2 — Upstream Setup
5. Read the upstream README carefully and extract the exact expected install flow.
6. Create or repair the required environments:
   - `gmr`
   - `phmr`
7. Install all package and system dependencies required for:
   - core pipeline
   - PromptHMR
   - GMR
   - GUI/web serving
   - video processing
   - visualization
8. Resolve any incompatibilities specific to:
   - Python version
   - CUDA / torch
   - GPU architecture
   - missing compilers or native libraries
   - missing submodule content

### Phase 3 — Test Input
9. Acquire a small test video from the web that contains a clearly visible human.
10. Save it into a stable local path inside the workspace.
11. Record:
   - source URL
   - download method
   - local path
   - why it is a suitable test input
12. If the first chosen video is unsuitable, replace it and keep the failed attempt in the remediation log.

### Phase 4 — Non-GUI Validation
13. Run baseline checks for the non-GUI path.
14. Run the non-GUI pipeline:
   - Preferred (matches dm-isaac-g1 docs):
     - `conda activate phmr && python scripts/extract_pose.py --video <local_video_path> --output <poses_dir>`
     - `conda activate gmr && python scripts/retarget.py --input <poses_dir> --robot unitree_g1 --output <retarget_dir>`
   - Or, if supported by the checked-out revision:
     - `python scripts/run_pipeline.py --video <local_video_path>`
15. If it fails:
   - identify the failing stage exactly
   - apply the smallest plausible fix
   - rerun the relevant validation immediately
16. Continue until the non-GUI path works end-to-end.

### Phase 5 — GUI Validation
17. Start the web server with either:
   - `uvicorn web.app:app --host 0.0.0.0 --port 8000`, or
   - the dm-isaac-g1 wrapper: `video2robot-server.py` (exposed as `http://<host>:8000` with HTTP Basic Auth)
18. Verify:
   - bind success
   - route availability
   - port accessibility
   - static/assets behavior
   - any upload or project-path expectations
19. Run the GUI workflow using the test video.
20. If it fails:
   - isolate whether the issue is:
     - backend pipeline
     - frontend/UI
     - server binding
     - file upload/path handling
     - visualization dependency
     - environment switching
   - apply the smallest plausible fix
   - rerun validation immediately
21. Continue until the GUI path works end-to-end.

## Required Validation
Use repo checks if they help, but prioritize the real target workflows.

Minimum validation layers:

### Baseline validation
- repo present and clean enough to operate
- submodules initialized
- required conda environments exist
- key imports succeed in the correct environments

### Non-GUI validation
- real local video input exists
- either the two-stage CLI (`extract_pose.py` + `retarget.py`) or `run_pipeline.py --video ...` executes successfully
- expected output/project artifacts are generated (pose PKL + retargeted motion)

### GUI validation
- `uvicorn` server starts successfully
- the UI is reachable through the intended access path
- the GUI path can process a local video through the backend pipeline successfully

## Blocker Standard
Do not stop at “found blocker”.
If a blocker remains, the remediation log must include:
- exact failing command or action
- exact error
- affected layer
- evidence
- smallest viable workaround
- exact persistent fix to integrate later

Classify the blocker as one of:
- missing credential or API key
- missing model weights or gated assets
- Python dependency conflict
- CUDA / torch / GPU mismatch
- missing system package or compiler
- submodule or upstream repo issue
- GUI serving / network access issue
- unsupported runtime assumption in upstream docs
- genuinely external or inaccessible dependency

## Logging Requirements
For every attempt, record:
- timestamp
- exact command run or exact change made
- short reason
- result
- success or failure
- why it worked or failed
- whether it should be integrated permanently
- whether it affected:
  - non-GUI
  - GUI
  - both

Failed attempts must remain in the final log.

## End-of-Task Documentation Requirement
Once both workflows are working:

Place at the top of `current_task/VIDEO2ROBOT_REMEDIATION_LOG.md`:
1. the minimal working procedure
2. exact environment summary
3. exact commands to run non-GUI
4. exact commands to run GUI
5. local test video path used
6. required env vars or secrets
7. persistent fixes that should be integrated into future instances

## Anti-Drift Rules
- Do not refactor unrelated code.
- Do not replace upstream architecture unless necessary.
- Do not broaden the mission beyond getting both supported paths working.
- Do not remove failed attempts from the log.
- Do not claim success until both modes are validated.

## Definition of Done
Done means:
- non-GUI pipeline works with a local human video
- GUI/web pipeline works
- the remediation log is complete
- the minimal working procedure is documented
- persistent follow-ups are clearly separated from live-only fixes
