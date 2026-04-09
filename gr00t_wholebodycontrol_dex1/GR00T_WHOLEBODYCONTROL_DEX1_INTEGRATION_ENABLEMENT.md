# GR00T WholeBodyControl Dex1 Integration Enablement

## Objective
Create an operator-ready task folder for running `GR00T-WholeBodyControl-dex1` with a GR00T model against the G1 MuJoCo whole-body-control benchmark on the fixed remote instance `54.155.29.100`.

This task is complete only when the GR00T model is not merely loaded, but actually drives the simulated robot state in the WBC environment.

## Primary Targets
- EC2 instance: `54.155.29.100`
- SSH user: `ec2-user`
- Runtime: ECS workspace container on that host
- WBC repo: `/workspace/GR00T-WholeBodyControl-dex1`
- GR00T repo: `/workspace/Isaac-GR00T`
- Python env: `/opt/conda/envs/unitree_sim_env`
- Selected GR00T model: `nvidia/GR00T-N1.6-G1-PnPAppleToPlate`
- Target env ID: `gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc`

## Required Capability
The remote runtime must support this workflow:
1. discover the live ECS container
2. expose the Dex1 WBC repo and its RoboCasa dependencies to Python
3. build the G1 WBC MuJoCo env
4. load the GR00T G1 model
5. execute a closed-loop policy step
6. verify that the simulator joint state changes after the step

## Acceptance Criteria
Success for this task means all of the following were validated on the live instance:
- `unitree_sim_env` can import `gr00t`, `gymnasium`, `mujoco`, `onnxruntime`, and the WBC env modules
- the G1 loco-manipulation env can be created and reset successfully
- the NVIDIA GR00T G1 model downloads or loads from cache successfully
- GR00T outputs action tensors for waist, arms, hands, base height, and navigation
- after `env.step(actions)`, the robot joint state changes measurably

Validated result from this session:
- `joint_delta_norm 0.49687227606773376`
- `joint_delta_max_abs 0.2770960330963135`
- `joint_delta_nonzero 41`

## Important Environment Reality
The live container did not work out of the box for this benchmark. The following live-only compatibility fixes were required:
- clone the `robosuite` branch expected by NVIDIA's setup flow into `decoupled_wbc/dexmg/gr00trobosuite`
- alias `gr00t_wbc` to the local `decoupled_wbc` checkout
- patch Python 3.11-incompatible dataclass defaults in vendored `gr00trobocasa`
- add a `mink.tasks.exceptions` compatibility shim
- patch `sync_env.py` so it works when imported under the `gr00t_wbc` alias

## Out Of Scope
- permanent cleanup of the remote vendor patches
- packaging the live-only fixes into the Docker image
- validating a full multi-episode benchmark run
- validating the old Unitree `unitree_mujoco + g1_ctrl` sim2sim path for this task

## Completion Statement
This task is complete for the requested scope because the official NVIDIA G1 GR00T model was loaded and used to step the live WBC simulator, and the post-step joint state changed on 41 joints. That is stronger than opening the simulator window alone.
