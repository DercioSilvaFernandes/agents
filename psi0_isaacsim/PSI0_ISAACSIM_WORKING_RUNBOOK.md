# Psi0 IsaacSim Working Runbook

## Purpose
This runbook captures the practical sequence to get Psi0 inference running through the Isaac Sim evaluation path on the validated remote instance `108.129.215.209`.

It is not a generic upstream summary. It is the operator checklist for turning the partial Psi0 plus SIMPLE instructions into a working, testable flow.

## Scope
- Remote host: `108.129.215.209`
- Access method: `ssh smartinterp-108-129-215-209`
- Known active runtime during setup: `ecs-dm-interactive-shell-237-workspace-ec9cf59d96c397887500`
- Upstream repo: `physical-superintelligence-lab/Psi0`
- Target validation path:
  - repo setup
  - checkpoint serving
  - SIMPLE eval client
  - `--sim-mode=mujoco_isaac`

## Preconditions
- Do not restart the instance unless the mission explicitly requires it.
- Confirm SSH access works.
- Confirm GPU access works where inference will run.
- Confirm the active container or workspace path before cloning or installing.
- Confirm whether Isaac Sim requirements live in the host, the container, or a sibling container.
- Confirm availability of the required checkpoint and SIMPLE evaluation data.

## Expected Steady-State Outcome
- Psi0 repo is available in the working environment
- Python environment is healthy and `import psi` succeeds
- `serve_psi0` is reachable on the expected port
- SIMPLE evaluation client completes a rollout in `mujoco_isaac` mode
- evaluation outputs are written to the expected output directory

## 1. Connect To The Target Host

```bash
ssh smartinterp-108-129-215-209
```

Quick baseline:

```bash
hostname
nvidia-smi
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
```

## 2. Identify The Actual Execution Environment

If the runtime is containerized, discover the active workspace container first:

```bash
docker ps --format '{{.Names}} {{.Image}} {{.Status}}'
```

Known container at folder creation time:

```bash
ecs-dm-interactive-shell-237-workspace-ec9cf59d96c397887500
```

Inspect likely workspace roots before installing anything:

```bash
docker exec <container> bash -lc '
  pwd
  ls -la /workspace /home/ec2-user 2>/dev/null
  nvidia-smi || true
'
```

## 3. Clone Or Reuse The Psi0 Repo

If the repo is not already present in the active runtime:

```bash
docker exec -it <container> bash -lc '
  cd /workspace
  git clone https://github.com/physical-superintelligence-lab/Psi0.git
'
```

If the repo already exists, inspect instead of recloning:

```bash
docker exec <container> bash -lc '
  cd /workspace/Psi0
  git remote -v
  git status --short
  git rev-parse HEAD
'
```

## 4. Create The Psi0 Environment

The upstream README uses `uv` and Python `3.10`:

```bash
docker exec -it <container> bash -lc '
  cd /workspace/Psi0
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH=$HOME/.local/bin:$PATH
  uv venv .venv-psi --python 3.10
  source .venv-psi/bin/activate
  GIT_LFS_SKIP_SMUDGE=1 uv sync --all-groups --index-strategy unsafe-best-match --active
  uv pip install flash_attn==2.7.4.post1 --no-build-isolation
  python -c "import psi; print(psi.__version__)"
'
```

If dependency resolution differs on the live machine, log the exact delta and the exact fix.

## 5. Resolve Simulation Assets And Data

The upstream README documents SIMPLE-based evaluation but leaves installation details incomplete. Before serving the model, verify:

```bash
docker exec <container> bash -lc '
  cd /workspace/Psi0
  ls -la third_party
  find . -maxdepth 3 \\( -iname "*simple*" -o -iname "docker-compose*" \\) | sort
'
```

Then identify:
- where SIMPLE is installed
- whether Isaac Sim dependencies are already baked into the container image
- which task dataset will be used
- where checkpoints are stored

Expected upstream eval data location shape:

```text
data/<task_name>
```

## 6. Start Psi0 Model Serving

The upstream README documents the serving flow:

```bash
docker exec -it <container> bash -lc '
  cd /workspace/Psi0
  export PATH=$HOME/.local/bin:$PATH
  source .venv-psi/bin/activate
  export run_dir=<run_dir_under_.runs>
  export ckpt_step=<checkpoint_step>
  uv run --active --group psi --group serve serve_psi0 \
    --host 0.0.0.0 \
    --port 22085 \
    --run-dir=$run_dir \
    --ckpt-step=$ckpt_step \
    --action-exec-horizon=24 \
    --rtc
'
```

Health check from the same environment or a forwarded local port:

```bash
curl -i http://localhost:22085/health
```

If the service runs remotely in a detached shell, capture logs explicitly.

## 7. Run The SIMPLE Evaluation Client In Isaac Sim Mode

The upstream README documents this eval form:

```bash
docker exec -it <container> bash -lc '
  cd /workspace/Psi0
  GPUs=1 docker compose run eval <task_name> psi0 \
    --host=localhost \
    --port=22085 \
    --sim-mode=mujoco_isaac \
    --headless \
    --max-episode-steps=360 \
    --num-episodes=10 \
    --data-format=lerobot \
    --data-dir=data/<task_name>
'
```

If the evaluation client must target a different hostname from inside Docker, record the exact networking change.

## 8. Validate Outputs

The upstream README says rollout videos should land under:

```text
third_party/SIMPLE/data/evals/psi0
```

Validate with:

```bash
docker exec <container> bash -lc '
  cd /workspace/Psi0
  find third_party/SIMPLE/data/evals/psi0 -maxdepth 3 -type f | sort | sed -n "1,120p"
'
```

Also capture:
- server logs
- eval client logs
- whether Isaac Sim ran headless or required a display
- total runtime per episode

## 9. Define Completion

Do not mark the mission complete until all of the following are true:
- serve endpoint responds successfully
- eval client completes at least one run in `mujoco_isaac`
- output artifacts are present
- the exact working command sequence is preserved in the logs

## Troubleshooting
- `uv` not found:
  - install it in the active runtime and export `PATH=$HOME/.local/bin:$PATH`
- `import psi` fails:
  - verify the correct venv is active and `uv sync` finished without skipped core groups
- checkpoint not found:
  - inspect `.runs`, external mounts, and documented download sources before changing code
- `curl /health` fails:
  - confirm the serve process is still alive, bound to `0.0.0.0`, and reachable from the eval client network namespace
- `docker compose run eval` cannot reach the server:
  - use the correct hostname for container-to-container networking instead of assuming `localhost`
- Isaac Sim path fails while MuJoCo works:
  - isolate whether the blocker is rendering, licensing/assets, DISPLAY/headless setup, or SIMPLE installation
- upstream README gaps:
  - record the exact missing step and the discovered working replacement in the remediation logs
