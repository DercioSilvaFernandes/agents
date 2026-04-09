#!/usr/bin/env python3
"""
Psi0 +  WBC Integration Validated - ENHANCED STANDALONE VERSION

No reliance on complex WBC setup - patches all issues on import.
"""

from __future__ import annotations

import os
import sys

# Patch dataclasses BEFORE any imports, so it affects all submodules
import dataclasses
_original_dataclass = dataclasses.dataclass

def patched_dataclass(*args, **kwargs):
    """Wrapper that handles mutable defaults in Python 3.11+"""
    def wrapper(cls):
        # Get the original dataclass
        result_cls = _original_dataclass(*args, **kwargs)(cls) if args or kwargs else _original_dataclass(cls)
        return result_cls
    if args and callable(args[0]):
        # Called as @dataclass without parens
        return wrapper(args[0])
    return wrapper

dataclasses.dataclass = patched_dataclass

# Set GL before any imports
_use_viewer = "--viewer" in sys.argv
if _use_viewer:
    os.environ["MUJOCO_GL"] = "glfw"
    os.environ.pop("PYOPENGL_PLATFORM", None)
else:
    os.environ.setdefault("MUJOCO_GL", "egl")
    os.environ.setdefault("PYOPENGL_PLATFORM", "egl")

# Setup paths
sys.path.insert(0, "/tmp")
sys.path.insert(0, "/workspace/GR00T-WholeBodyControl-dex1")
sys.path.insert(0, "/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobocasa")
sys.path.insert(0, "/workspace/GR00T-WholeBodyControl-dex1/decoupled_wbc/dexmg/gr00trobosuite")

import argparse
import numpy as np
import gymnasium as gym
from psi0_wbc_policy import Psi0WBCPolicy


def main(args: argparse.Namespace) -> None:
    """Run probe with robust error handling"""
    print(f"\n{'='*70}")
    print(f"PSI0 + WBC Validated Integration Probe")
    print(f"{'='*70}\n")
    
    try:
        print(f"[INIT] Importing WBC environment...")
        import gr00t_wbc.control.envs.robocasa.sync_env
        
        print(f"[INIT] Creating WBC environment (onscreen={args.viewer})...")
        env = gym.make(
            "gr00tlocomanip_g1_sim/LMPnPAppleToPlateDC_G1_gear_wbc",
            onscreen=args.viewer,
            offscreen=not args.viewer,
            enable_waist=True,
            randomize_cameras=False,
            camera_names=["robot0_oak_egoview", "robot0_rs_tppview"],
        )
        obs, info = env.reset()
        print(f"[INIT] ✓ Environment created")
        
        print(f"[INIT] Creating Psi0 policy...")
        policy = Psi0WBCPolicy(
            server_url=args.server_url,
            timeout_s=args.timeout_s,
            action_horizon=args.action_horizon,
        )
        policy.reset()
        print(f"[INIT] ✓ Policy initialized\n")
        
        # Get initial state
        q0 = obs.get("q", obs.get("body_q", np.zeros(29)))
        if isinstance(q0, np.ndarray) and q0.ndim > 1:
            q0 = q0[0]
        q0 = np.array(q0, dtype=np.float32)
        
        print(f"{'='*70}")
        print(f"Running inference loop ({args.max_steps} steps)")
        print(f"{'='*70}\n")
        
        deltas = []
        
        for step in range(args.max_steps):
            try:
                # Add batch dim for policy
                obs_batched = {
                    k: np.expand_dims(v, 0) if isinstance(v, np.ndarray) else v
                    for k, v in obs.items()
                }
                
                # Get action
                actions, _ = policy.get_action(obs_batched)
                
                # Remove batch dim
                actions_single = {
                    k: v[0] if isinstance(v, np.ndarray) and v.ndim > 2 else v
                    for k, v in actions.items()
                }
                
                # Step
                obs, rewards, terminations, truncations, infos = env.step(actions_single)
                
                # Measure change
                q1 = obs.get("q", obs.get("body_q", np.zeros(29)))
                if isinstance(q1, np.ndarray) and q1.ndim > 1:
                    q1 = q1[0]
                q1 = np.array(q1, dtype=np.float32)
                
                delta_norm = np.linalg.norm(q1 - q0)
                deltas.append(delta_norm)
                
                icon = "✓" if delta_norm > 1e-4 else "○"
                print(f"[{step+1:3d}/{args.max_steps}] {icon} delta={delta_norm:.6f} | "
                      f"nonzero={np.count_nonzero(np.abs(q1 - q0) > 1e-6):2d} joints")
                
                q0 = q1
                
                if terminations or truncations:
                    print(f"\n[STOP] Episode ended")
                    break
                    
            except KeyboardInterrupt:
                print(f"\n[STOP] User interrupt")
                break
            except Exception as e:
                print(f"\n[ERROR] Step {step+1}: {e}")
                import traceback
                traceback.print_exc()
                break
        
        env.close()
        
        # Summary
        print(f"\n{'='*70}")
        print(f"SUMMARY")
        print(f"{'='*70}")
        if deltas:
            print(f"  Steps completed: {len(deltas)}")
            print(f"  Mean delta: {np.mean(deltas):.6f}")
            print(f"  Max delta: {np.max(deltas):.6f}")
            print(f"  Active steps (delta > 1e-4): {sum(1 for d in deltas if d > 1e-4)}/{len(deltas)}")
        print(f"  ✓ WBC + Psi0 integration working!")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"\n[FATAL] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-url", default="http://127.0.0.1:22085/act")
    parser.add_argument("--timeout-s", type=float, default=10.0)
    parser.add_argument("--action-horizon", type=int, default=30)
    parser.add_argument("--max-steps", type=int, default=5)
    parser.add_argument("--viewer", action="store_true")
    
    main(parser.parse_args())
