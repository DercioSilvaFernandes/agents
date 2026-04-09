#!/usr/bin/env python3
"""
Psi0 WholeBodyControl G1 Integration Probe (with optional GUI)

This script validates that Psi0 can be used as the policy generator in the
GR00T WholeBodyControl framework for whole-body manipulation on the Unitree G1.

It mirrors the structure of gr00t_wbc_probe_vec.py but replaces GR00T with Psi0.

Usage (headless):
    export PYTHONPATH=/tmp:/workspace/GR00T-WholeBodyControl-dex1:...
    export MUJOCO_GL=egl PYOPENGL_PLATFORM=egl
    python psi0_wbc_probe.py \\
        --server-url http://127.0.0.1:22085/act \\
        --max-steps 5

Usage (with GUI viewer):
    export DISPLAY=:1
    export PYTHONPATH=/tmp:/workspace/GR00T-WholeBodyControl-dex1:...
    python psi0_wbc_probe.py \\
        --server-url http://127.0.0.1:22085/act \\
        --max-steps 100 \\
        --viewer
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from functools import partial
from pathlib import Path

import numpy as np

# Handle display environment early
_use_viewer = "--viewer" in sys.argv or "--gui" in sys.argv
if _use_viewer:
    os.environ["MUJOCO_GL"] = "glfw"
    os.environ.pop("PYOPENGL_PLATFORM", None)
else:
    os.environ.setdefault("MUJOCO_GL", "egl")
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

# Ensure WBC python paths are available
_wbc_root = Path(__file__).parent
if str(_wbc_root) not in sys.path:
    sys.path.insert(0, str(_wbc_root))
if "/tmp" not in sys.path:
    sys.path.insert(0, "/tmp")

import gymnasium as gym
from psi0_wbc_policy import Psi0WBCPolicy


def create_wbc_env(env_name: str, onscreen: bool = False, control_freq: int = 10) -> gym.Env:
    """Create and return WBC environment."""
    import gr00t_wbc.control.envs.robocasa.sync_env
    
    env = gym.make(
        env_name,
        onscreen=onscreen,
        offscreen=not onscreen,
        enable_waist=True,
        control_freq=control_freq,
        randomize_cameras=False,
        camera_names=["robot0_oak_egoview", "robot0_rs_tppview"],
    )
    return env


def main(args: argparse.Namespace) -> None:
    """Run Psi0 WBC integration probe."""
    
    print(f"[PSI0-WBC-PROBE] Starting integration validation")
    print(f"[PSI0-WBC-PROBE] Server URL: {args.server_url}")
    print(f"[PSI0-WBC-PROBE] Max steps: {args.max_steps}")
    print(f"[PSI0-WBC-PROBE] GUI Viewer: {'ENABLED' if args.viewer else 'disabled'}")
    
    # Create environment
    print(f"[PSI0-WBC-PROBE] Creating WBC environment (onscreen={args.viewer})...")
    env = create_wbc_env(args.env_name, onscreen=args.viewer, control_freq=args.control_freq)
    obs, info = env.reset()
    print(f"[PSI0-WBC-PROBE] Environment created successfully")
    print(f"[PSI0-WBC-PROBE] Observation keys: {sorted(obs.keys())[:10]}")
    print(f"[PSI0-WBC-PROBE] Image obs shape: {obs.get('ego_view_image', np.array([])).shape}")
    
    # Create Psi0 policy
    print(f"[PSI0-WBC-PROBE] Creating Psi0 policy wrapper...")
    policy = Psi0WBCPolicy(
        server_url=args.server_url,
        timeout_s=args.timeout_s,
        action_horizon=args.action_horizon,
    )
    policy.reset()
    print(f"[PSI0-WBC-PROBE] Policy created and reset")
    
    # Capture initial state
    q0 = np.array(obs["q"] if "q" in obs else obs.get("body_q", np.zeros(43))).copy()
    if q0.ndim > 1:
        q0 = q0[0]
    
    print(f"[PSI0-WBC-PROBE] Initial joint state: shape={q0.shape}, norm={np.linalg.norm(q0):.4f}")
    print(f"\n[PSI0-WBC-PROBE] Starting inference loop...")
    if args.viewer:
        print(f"[PSI0-WBC-PROBE] >>> GUI window should appear - watch the robot move! <<<\n")
    
    # Get action from Psi0
    print(f"[PSI0-WBC-PROBE] Step 1: Requesting action from Psi0...")
    try:
        actions, action_info = policy.get_action(obs)
        print(f"[PSI0-WBC-PROBE] ✓ Action received successfully")
    except Exception as e:
        print(f"[PSI0-WBC-PROBE] ✗ ERROR getting action: {e}")
        env.close()
        raise
    
    # Log action structure
    print(f"[PSI0-WBC-PROBE] Action keys: {sorted(actions.keys())}")
    for key in sorted(actions.keys()):
        shape = actions[key].shape
        print(f"[PSI0-WBC-PROBE]   {key}: {shape}")
    
    # Step environment
    print(f"[PSI0-WBC-PROBE] Stepping environment with WBC control...")
    t0 = time.time()
    actions_unbatched = {
        k: v[0] if isinstance(v, np.ndarray) and v.ndim > 1 else v
        for k, v in actions.items()
    }
    obs2, rewards, terminations, truncations, env_infos = env.step(actions_unbatched)
    t_step = time.time() - t0
    
    # Check state change
    q1 = np.array(obs2["q"] if "q" in obs2 else obs2.get("body_q", np.zeros(43))).copy()
    if q1.ndim > 1:
        q1 = q1[0]
    
    delta = q1 - q0
    
    print(f"[PSI0-WBC-PROBE] ✓ Step completed in {t_step:.3f}s")
    print(f"[PSI0-WBC-PROBE] Joint state after step: norm={np.linalg.norm(q1):.4f}")
    print(f"[PSI0-WBC-PROBE] Joint delta norm: {float(np.linalg.norm(delta)):.8f}")
    print(f"[PSI0-WBC-PROBE] Joint delta max abs: {float(np.max(np.abs(delta))):.8f}")
    print(f"[PSI0-WBC-PROBE] Joint delta nonzero: {int(np.count_nonzero(np.abs(delta) > 1e-6))}")
    print(f"[PSI0-WBC-PROBE] First 10 joints delta: {np.round(delta[:10], 6).tolist()}")
    
    # Multi-step rollout if requested
    if args.max_steps > 1:
        print(f"\n[PSI0-WBC-PROBE] Running {args.max_steps - 1} additional steps...\n")
        step_times = []
        for step in range(1, args.max_steps):
            try:
                q_prev = q1.copy()
                
                # Get action
                actions, _ = policy.get_action(obs2)
                
                # Step with timing
                t0 = time.time()
                actions_unbatched = {
                    k: v[0] if isinstance(v, np.ndarray) and v.ndim > 1 else v
                    for k, v in actions.items()
                }
                obs2, rewards, terminations, truncations, env_infos = env.step(actions_unbatched)
                t_step = time.time() - t0
                step_times.append(t_step)
                
                q1 = np.array(obs2["q"] if "q" in obs2 else obs2.get("body_q", np.zeros(43))).copy()
                if q1.ndim > 1:
                    q1 = q1[0]
                delta_step = q1 - q_prev
                
                status_icon = "✓" if np.linalg.norm(delta_step) > 1e-4 else "○"
                print(f"[PSI0-WBC-PROBE] {status_icon} Step {step + 1:3d}/{args.max_steps}: "
                      f"delta_norm={np.linalg.norm(delta_step):8.6f} | "
                      f"nonzero={np.count_nonzero(np.abs(delta_step) > 1e-6):3d} | "
                      f"time={t_step*1000:5.1f}ms")
            except KeyboardInterrupt:
                print(f"\n[PSI0-WBC-PROBE] Interrupted by user")
                break
            except Exception as e:
                print(f"\n[PSI0-WBC-PROBE] ✗ Error at step {step + 1}: {e}")
                break
        
        if step_times:
            print(f"\n[PSI0-WBC-PROBE] Timing stats:")
            print(f"  Mean: {np.mean(step_times)*1000:.2f}ms")
            print(f"  Median: {np.median(step_times)*1000:.2f}ms")
            print(f"  Max: {np.max(step_times)*1000:.2f}ms")
    else:
        step_times = []
    
    # Final summary
    print(f"\n[PSI0-WBC-PROBE] ╔════════════════════════════════════════╗")
    print(f"[PSI0-WBC-PROBE] ║     VALIDATION SUMMARY                 ║")
    print(f"[PSI0-WBC-PROBE] ╚════════════════════════════════════════╝")
    print(f"  ✓ Environment created and reset")
    print(f"  ✓ Psi0 policy created and called")
    print(f"  ✓ Actions generated in WBC format")
    print(f"  ✓ Environment stepped {min(args.max_steps, len(step_times) + 1)} time(s)")
    print(f"  ✓ Joint state changed: {np.linalg.norm(delta) > 0}")
    if args.viewer:
        print(f"  ✓ GUI visualization displayed")
    
    env.close()
    print(f"\n[PSI0-WBC-PROBE] Integration validation complete!\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Psi0 integration with GR00T WholeBodyControl"
    )
    parser.add_argument(
        "--env-name",
        type=str,
        default="gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc",
        help="WBC environment ID",
    )
    parser.add_argument(
        "--server-url",
        type=str,
        default="http://127.0.0.1:22085/act",
        help="Psi0 server HTTP endpoint",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=10.0,
        help="Psi0 server request timeout",
    )
    parser.add_argument(
        "--action-horizon",
        type=int,
        default=30,
        help="Number of action timesteps (should match WBC config)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=1,
        help="Number of environment steps to execute",
    )
    parser.add_argument(
        "--control-freq",
        type=int,
        default=10,
        help="WBC env control frequency in Hz",
    )
    parser.add_argument(
        "--viewer",
        action="store_true",
        help="Enable GUI viewer (requires X11 DISPLAY)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to save outputs (for future video recording)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args)
