# Sim2Sim Pipeline Integration Enablement

## Objective
Create an operator-ready task folder for testing and implementing the G1 sim2sim pipeline on the fixed remote instance `54.155.29.100`, using the user-provided flow as the target logic.

This task is not limited to note-taking. It must capture the real remote access path, the real launch commands that work on this host, and the gap between startup validation and full mimic-policy playback.

## Primary Targets
- EC2 instance: `54.155.29.100`
- SSH user: `ec2-user`
- Active runtime: ECS workspace container on that host
- Simulator binary: `/workspace/unitree_mujoco/simulate/build/unitree_mujoco`
- Controller binary: `/workspace/unitree_rl_lab/deploy/robots/g1_29dof/build/g1_ctrl`
- Policy config root: `/workspace/unitree_rl_lab/deploy/robots/g1_29dof/config/`
- Mimic policy root: `/workspace/unitree_rl_lab/deploy/robots/g1_29dof/config/policy/mimic/`

## User-Provided Target Logic
The intended workflow is:
1. prepare three terminals
2. start the simulator
3. copy a new mimic policy folder with `exported/` and `params/`
4. edit `config.yaml` with a new policy ID and input map
5. run `g1_ctrl --network lo`
6. run the policy script
7. confirm video-based motion plays in sim2sim

## Important Environment Reality
The validated host does not exactly match the pasted instructions:
- `env_isaaclab` is not present in the live container
- available envs are `base`, `gmr`, `phmr`, and `unitree_sim_env`
- the host itself does not contain the repos; the working copies are inside the running Docker container
- password-based SSH is disabled on the validated host; key-based SSH works

## Capabilities In Scope
This folder must document and support:
- safe SSH access without restarting the instance
- discovery of the active ECS workspace container
- simulator startup inside the container with `DISPLAY=:1`
- controller startup inside the container with `--network lo`
- future placement of a new mimic policy directory under `config/policy/mimic/<task_name>/`
- future `config.yaml` extension for a new mimic state and policy directory

## Explicitly Deferred
The user did not ask for full end-to-end policy wiring in this turn. The following are documented but not implemented here:
- creating the actual new mimic policy assets
- editing `tempganga.py`
- validating video-driven motion playback end-to-end

## Success Criteria
Minimum success for this turn:
- a standard task folder exists under `agents/sim2sim_pipeline`
- remote access instructions reflect the real validated host behavior
- the runbook documents the correct simulator and controller startup path
- `unitree_mujoco` is launched successfully on the remote instance
- `g1_ctrl --network lo` is launched successfully on the remote instance
- remediation logs capture what was validated and what remains

Full future success for the overall mission:
- a new mimic policy folder is staged under `config/policy/mimic/<task_name>/`
- `config.yaml` references that policy with a unique FSM ID
- the policy trigger script runs
- video-based motion executes in sim2sim

## Preconditions
- `/Users/dercio.fernandes/dm-isaac-g1.pem` is available locally
- the target instance remains running
- the ECS workspace container remains running
- `/tmp/cyclonedds.xml` exists in the container
- TurboVNC display `:1` exists in the container for MuJoCo viewer startup

## Required Artifacts
- `agents/sim2sim_pipeline/AGENTS.md`
- `agents/sim2sim_pipeline/SIM2SIM_PIPELINE_INTEGRATION_ENABLEMENT.md`
- `agents/sim2sim_pipeline/SIM2SIM_PIPELINE_WORKING_RUNBOOK.md`
- `agents/sim2sim_pipeline/SIM2SIM_PIPELINE_REMEDIATION_LOG.md`
- `agents/sim2sim_pipeline/current_task/SIM2SIM_PIPELINE_REMEDIATION_LOG.md`
