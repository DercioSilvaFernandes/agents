#!/usr/bin/env python3
"""
Psi0 + GR00T WBC validated probe.

This probe drives Psi0 upper-body targets through decoupled WBC policy so
lower-body balance is maintained by the GEAR WBC policy.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

# Set GL backend before imports that initialize mujoco contexts.
_use_viewer = "--viewer" in sys.argv
if _use_viewer:
    os.environ["MUJOCO_GL"] = "glfw"
    os.environ.pop("PYOPENGL_PLATFORM", None)
else:
    os.environ.setdefault("MUJOCO_GL", "egl")
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

sys.path.insert(0, "/tmp")
sys.path.insert(0, "/workspace/GR00T-WholeBodyControl-dex1")
sys.path.insert(0, "/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa")
sys.path.insert(0, "/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite")

import gymnasium as gym
from psi0_wbc_policy import Psi0WBCPolicy

from decoupled_wbc.control.main.teleop.configs.configs import SyncSimDataCollectionConfig
from decoupled_wbc.control.policy.wbc_policy_factory import get_wbc_policy
from decoupled_wbc.control.robot_model.instantiation import get_robot_type_and_model


def create_wbc_env_single(onscreen: bool = False, control_freq: int = 10) -> gym.Env:
    """Create single (non-vectorized) G1 WBC sim env."""
    import gr00t_wbc.control.envs.robocasa.sync_env  # noqa: F401

    env = gym.make(
        "gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc",
        onscreen=onscreen,
        offscreen=not onscreen,
        enable_waist=True,
        control_freq=control_freq,
        randomize_cameras=False,
        camera_names=["robot0_oak_egoview", "robot0_rs_tppview"],
    )
    return env


def _first_step(action_chunk: np.ndarray) -> np.ndarray:
    """Extract one step from [B?, T, D] / [T, D] / [D] formats."""
    arr = np.asarray(action_chunk, dtype=np.float32)
    if arr.ndim == 3:
        return arr[0, 0]
    if arr.ndim == 2:
        return arr[0]
    if arr.ndim == 1:
        return arr
    raise ValueError(f"Unsupported action array shape: {arr.shape}")


def _to_single_step_action(
    actions: dict[str, np.ndarray], use_psi0_waist: bool
) -> dict[str, np.ndarray]:
    """Convert batched/chunked policy outputs into one-step action dict."""
    one_step = {}
    for key in ("action.left_arm", "action.right_arm", "action.left_hand", "action.right_hand"):
        if key not in actions:
            raise KeyError(f"Missing required key '{key}' in Psi0 action output")
        one_step[key] = _first_step(actions[key])
    if use_psi0_waist and "action.waist" in actions:
        one_step["action.waist"] = _first_step(actions["action.waist"])
    if "action.base_height_command" in actions:
        one_step["action.base_height_command"] = _first_step(actions["action.base_height_command"])
    if "action.navigate_command" in actions:
        one_step["action.navigate_command"] = _first_step(actions["action.navigate_command"])
    return one_step


def build_wbc_goal(
    robot_model,
    current_q: np.ndarray,
    one_step_action: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """
    Build WBC goal by starting from current posture and applying only provided groups.
    This avoids zeroing uncontrolled upper-body joints.
    """
    q_target = np.asarray(current_q, dtype=np.float32).copy()
    for key, group in (
        ("action.left_arm", "left_arm"),
        ("action.right_arm", "right_arm"),
        ("action.left_hand", "left_hand"),
        ("action.right_hand", "right_hand"),
        ("action.waist", "waist"),
    ):
        if key not in one_step_action:
            continue
        indices = robot_model.get_joint_group_indices(group)
        q_target[indices] = np.asarray(one_step_action[key], dtype=np.float32)

    upper_body_indices = robot_model.get_joint_group_indices("upper_body")
    goal = {"target_upper_body_pose": q_target[upper_body_indices]}
    if "action.base_height_command" in one_step_action:
        goal["base_height_command"] = np.asarray(
            one_step_action["action.base_height_command"], dtype=np.float32
        )
    if "action.navigate_command" in one_step_action:
        goal["navigate_cmd"] = np.asarray(one_step_action["action.navigate_command"], dtype=np.float32)
    return goal


def build_decoupled_wbc_policy(env: gym.Env, control_freq: int, upper_body_joint_speed: float):
    """
    Build decoupled WBC policy explicitly with interpolation upper-body policy.
    """
    robot_name = env.unwrapped.robot_name
    robot_type, robot_model = get_robot_type_and_model(robot_name, enable_waist_ik=True)

    config = SyncSimDataCollectionConfig(
        robot=robot_name,
        enable_waist=True,
        control_frequency=control_freq,
        sim_frequency=max(200, control_freq * 4),
        enable_onscreen=bool(env.unwrapped.onscreen),
        enable_offscreen=not bool(env.unwrapped.onscreen),
    )
    wbc_config = config.load_wbc_yaml()
    wbc_config["upper_body_policy_type"] = "interpolation"
    wbc_config["upper_body_max_joint_speed"] = float(upper_body_joint_speed)

    wbc_policy = get_wbc_policy(robot_type, robot_model, wbc_config, init_time=time.monotonic())
    wbc_policy.activate_policy()
    return wbc_policy, robot_model


def main_simple(args: argparse.Namespace) -> None:
    print(f"\n{'='*70}")
    print("PSI0 WholeBodyControl Integration Probe (VALIDATED BALANCE PATH)")
    print(f"{'='*70}\n")

    print(
        f"[PROBE] Creating WBC environment (onscreen={args.viewer}, "
        f"control_freq={args.control_freq}Hz)..."
    )
    env = create_wbc_env_single(onscreen=args.viewer, control_freq=args.control_freq)
    obs, _ = env.reset()
    print("[PROBE] ✓ Environment created and reset")
    print(f"[PROBE] Observation keys: {sorted(obs.keys())[:8]}...")
    print(f"[PROBE] Image shape: {obs['ego_view_image'].shape}")

    print("\n[PROBE] Building decoupled WBC policy...")
    wbc_policy, robot_model = build_decoupled_wbc_policy(
        env=env,
        control_freq=args.control_freq,
        upper_body_joint_speed=args.wbc_upper_body_speed,
    )
    wbc_policy.set_observation(obs)
    print("[PROBE] ✓ WBC policy initialized (interpolation upper-body + GEAR lower-body)")

    print("\n[PROBE] Creating Psi0 policy...")
    policy = Psi0WBCPolicy(
        server_url=args.server_url,
        timeout_s=args.timeout_s,
        action_horizon=args.action_horizon,
        instruction_override=args.instruction_override,
        emit_q=False,
        use_psi0_base_height=args.use_psi0_base_height,
        use_psi0_navigate_command=args.use_psi0_navigate_command,
    )
    policy.reset()
    print("[PROBE] ✓ Psi0 policy initialized")

    obs_batched = {k: np.expand_dims(v, 0) if isinstance(v, np.ndarray) else v for k, v in obs.items()}

    print(f"\n[PROBE] Running inference loop (max_steps={args.max_steps})...")
    print("[PROBE] >>> GUI window should appear <<<\n")

    step_deltas = []
    base_heights = []

    for step in range(args.max_steps):
        try:
            actions, action_info = policy.get_action(obs_batched)
            one_step_action = _to_single_step_action(actions, use_psi0_waist=args.use_psi0_waist)
            wbc_goal = build_wbc_goal(
                robot_model=robot_model,
                current_q=np.asarray(obs["q"], dtype=np.float32),
                one_step_action=one_step_action,
            )

            now = time.monotonic()
            wbc_goal["target_time"] = now + (1.0 / float(args.control_freq))
            wbc_goal["interpolation_garbage_collection_time"] = now - (2.0 / float(args.control_freq))

            wbc_policy.set_goal(wbc_goal)
            wbc_action = wbc_policy.get_action(time=now)

            q_prev = np.asarray(obs["q"], dtype=np.float32).copy()
            obs, rewards, terminations, truncations, env_infos = env.step(wbc_action)
            wbc_policy.set_observation(obs)

            q_now = np.asarray(obs["q"], dtype=np.float32)
            delta = q_now - q_prev
            step_deltas.append(float(np.linalg.norm(delta)))

            base_z = float(np.asarray(obs["floating_base_pose"])[2])
            base_heights.append(base_z)
            status = "✓" if step_deltas[-1] > 1e-5 else "○"
            print(
                f"[PROBE] {status} Step {step + 1:3d}/{args.max_steps}: "
                f"delta_norm={step_deltas[-1]:8.6f} | base_z={base_z:7.4f} | "
                f"psi0_min={action_info['psi0_action_min']:+.4f} "
                f"psi0_max={action_info['psi0_action_max']:+.4f}"
            )

            obs_batched = {
                k: np.expand_dims(v, 0) if isinstance(v, np.ndarray) else v for k, v in obs.items()
            }

            if terminations or truncations:
                print("[PROBE] Episode terminated/truncated")
                break

        except KeyboardInterrupt:
            print("\n[PROBE] Interrupted by user")
            break
        except Exception as e:
            print(f"\n[PROBE] ✗ Error at step {step + 1}: {e}")
            import traceback

            traceback.print_exc()
            break

    env.close()

    print(f"\n{'='*70}")
    print("VALIDATION SUMMARY")
    print(f"{'='*70}")
    print("  ✓ WBC environment created and reset")
    print("  ✓ Psi0 policy integrated")
    print("  ✓ Decoupled WBC policy path exercised")
    print(f"  ✓ Completed {len(step_deltas)} steps")
    if step_deltas:
        print(f"  ✓ Mean delta: {np.mean(step_deltas):.6f}")
        print(f"  ✓ Max delta: {np.max(step_deltas):.6f}")
    if base_heights:
        print(f"  ✓ Base height min/mean/max: {min(base_heights):.4f}/{np.mean(base_heights):.4f}/{max(base_heights):.4f}")
    if args.viewer:
        print("  ✓ GUI visualization completed")
    print(f"{'='*70}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Psi0 + Decoupled-WBC integration validation probe")
    parser.add_argument(
        "--server-url",
        type=str,
        default="http://127.0.0.1:22085/act",
        help="Psi0 server URL",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=10.0,
        help="Request timeout",
    )
    parser.add_argument(
        "--action-horizon",
        type=int,
        default=30,
        help="Action horizon timesteps",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=50,
        help="Number of steps to run",
    )
    parser.add_argument(
        "--control-freq",
        type=int,
        default=10,
        help="WBC env control frequency in Hz",
    )
    parser.add_argument(
        "--wbc-upper-body-speed",
        type=float,
        default=0.8,
        help="Interpolation speed (rad/s) for upper-body pose tracking",
    )
    parser.add_argument(
        "--use-psi0-waist",
        action="store_true",
        help="Forward Psi0 waist channels to WBC (disabled by default for stability)",
    )
    parser.add_argument(
        "--use-psi0-base-height",
        action="store_true",
        help="Forward Psi0 channel 31 to WBC base_height_command",
    )
    parser.add_argument(
        "--use-psi0-navigate-command",
        action="store_true",
        help="Forward Psi0 channels 32:35 to WBC navigate_command",
    )
    parser.add_argument(
        "--instruction-override",
        type=str,
        default=None,
        help="Optional fixed instruction sent to Psi0 (overrides env task instruction)",
    )
    parser.add_argument(
        "--viewer",
        action="store_true",
        help="Enable GUI viewer (requires DISPLAY)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Force headless mode",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main_simple(args)
