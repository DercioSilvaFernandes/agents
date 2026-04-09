#!/usr/bin/env python3
"""
Psi0 Policy Wrapper for GR00T WholeBodyControl Integration

This wrapper provides a GR00T-compatible interface for using Psi0 server
as the action generator in the WBC control loop.

Usage:
    policy = Psi0WBCPolicy(
        server_url="http://127.0.0.1:22085/act",
        timeout_s=10.0,
        action_horizon=30,  # matches WBC's n_action_steps
    )
    policy.reset()
    actions, info = policy.get_action(obs)  # obs from SyncVectorEnv
    # actions dict matches WBC format with keys:
    # 'action.left_arm', 'action.right_arm', 'action.left_hand', 'action.right_hand',
    # 'action.waist', 'action.base_height_command', 'action.navigate_command'
"""

from __future__ import annotations

import json
import time
from base64 import b64decode, b64encode
from typing import Any

import numpy as np
import requests


def dtype_to_descr(dtype: np.dtype) -> str:
    """Convert numpy dtype to descriptor string."""
    return dtype.str


def descr_to_dtype(descr: str) -> np.dtype:
    """Convert descriptor string back to numpy dtype."""
    return np.dtype(descr)


def numpy_serialize(obj: np.ndarray) -> dict[str, Any]:
    """Serialize numpy array to JSON-compatible dict."""
    if isinstance(obj, (np.ndarray, np.generic)):
        data = obj.data if obj.flags["C_CONTIGUOUS"] else obj.tobytes()
        return {
            "__numpy__": b64encode(data).decode(),
            "dtype": dtype_to_descr(obj.dtype),
            "shape": obj.shape,
        }
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def numpy_deserialize(obj: dict[str, Any]) -> np.ndarray:
    """Deserialize numpy array from JSON dict."""
    if "__numpy__" in obj:
        arr = np.frombuffer(b64decode(obj["__numpy__"]), descr_to_dtype(obj["dtype"]))
        return arr.reshape(obj["shape"]) if obj["shape"] else arr[0]
    return obj


def convert_numpy_in_dict(data: Any, func) -> Any:
    """Recursively apply conversion function to numpy arrays in nested dicts/lists."""
    if isinstance(data, dict):
        if "__numpy__" in data:
            return func(data)
        return {key: convert_numpy_in_dict(value, func) for key, value in data.items()}
    if isinstance(data, list):
        return [convert_numpy_in_dict(item, func) for item in data]
    if isinstance(data, (np.ndarray, np.generic)):
        return func(data)
    return data


class Psi0WBCPolicy:
    """
    Policy wrapper that calls Psi0 server and converts output to WBC action format.
    
    Psi0 outputs raw hand/arm/torso actions in shape (30, 36):
    - 30 timesteps
    - 36 DOFs: hand(14) + arm(14) + torso(4) + pad(4)
    
    This converter outputs WBC-compatible action dict with batch dimension:
    - 'action.left_arm': (1, 30, 7)
    - 'action.right_arm': (1, 30, 7)
    - 'action.left_hand': (1, 30, 7)
    - 'action.right_hand': (1, 30, 7)
    - 'action.waist': (1, 30, 3)
    - 'action.base_height_command': (1, 30, 1)
    - 'action.navigate_command': (1, 30, 3)
    """

    def __init__(
        self,
        server_url: str = "http://127.0.0.1:22085/act",
        timeout_s: float = 10.0,
        action_horizon: int = 30,
        image_key: str = "ego_view_image",
        instruction_key: str = "annotation.human.task_description",
        instruction_override: str | None = None,
        emit_q: bool = False,
        use_psi0_base_height: bool = False,
        use_psi0_navigate_command: bool = False,
    ):
        """
        Initialize Psi0 policy wrapper.
        
        Args:
            server_url: HTTP endpoint for Psi0 inference server
            timeout_s: Request timeout in seconds
            action_horizon: Number of action timesteps (matches MultiStepConfig.n_action_steps)
            image_key: Key in observation dict for egocentric image
            instruction_key: Key in observation dict for task instruction
            instruction_override: If provided, always use this instruction for Psi0
            emit_q: If True, include a full-body q trajectory in returned actions
            use_psi0_base_height: If True, map Psi0 channel 31 to base height command
            use_psi0_navigate_command: If True, map Psi0 channels 32:35 to navigate command
        """
        self.server_url = server_url
        self.timeout_s = timeout_s
        self.action_horizon = action_horizon
        self.image_key = image_key
        self.instruction_key = instruction_key
        self.instruction_override = instruction_override
        self.emit_q = emit_q
        self.use_psi0_base_height = use_psi0_base_height
        self.use_psi0_navigate_command = use_psi0_navigate_command
        self.session = requests.Session()
        self.reset_count = 0
        self._pending_reset = True
        self._cached_action_chunk: np.ndarray | None = None
        self._chunk_cursor = 0

    def reset(self) -> None:
        """Reset policy state for new episode."""
        self.reset_count += 1
        self._pending_reset = True
        self._cached_action_chunk = None
        self._chunk_cursor = 0

    def get_action(self, obs: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], dict]:
        """
        Generate action from observation using Psi0 server.
        
        Args:
            obs: Observation dict from SyncVectorEnv containing:
                - ego_view_image: (batch, H, W, 3) RGB image
                - language_instruction: str or (batch,) array
                - body_q: (batch, n_joints) joint positions
                - Other robot state fields
        
        Returns:
            (actions_dict, info_dict) where:
            - actions_dict: WBC-format action dict with (batch=1, horizon=30, dof) shapes
            - info_dict: Metadata about the action generation
        """
        # Extract image - handle both single and batched observations
        if self.image_key not in obs:
            raise ValueError(f"Observation missing required key '{self.image_key}'")
        image = np.array(obs[self.image_key])
        if image.ndim == 4:
            # Batched: (batch, H, W, 3)
            image = image[0]  # Take first (only) batch element
        
        instruction = self._extract_instruction(obs)
        state = self._extract_psi0_state(obs)
        current_q = self._extract_current_q(obs)
        
        # Request a new chunk only when the current one is exhausted.
        if (
            self._cached_action_chunk is None
            or self._chunk_cursor >= self._cached_action_chunk.shape[0]
        ):
            self._cached_action_chunk = self._request_psi0_action(image, state, instruction)
            self._chunk_cursor = 0

        psi0_step = self._cached_action_chunk[self._chunk_cursor : self._chunk_cursor + 1]
        self._chunk_cursor += 1

        # Convert one-step Psi0 output to WBC action format.
        wbc_actions = self._convert_psi0_to_wbc_actions(psi0_step, current_q=current_q)
        
        info = {
            "policy": "Psi0WBC",
            "reset_count": self.reset_count,
            "psi0_action_shape": psi0_step.shape,
            "server_url": self.server_url,
            "instruction": instruction,
            "state_shape": tuple(state.shape),
            "state_norm": float(np.linalg.norm(state)),
            "psi0_action_min": float(np.min(psi0_step)),
            "psi0_action_max": float(np.max(psi0_step)),
            "chunk_cursor": self._chunk_cursor,
            "chunk_size": int(self._cached_action_chunk.shape[0]) if self._cached_action_chunk is not None else 0,
        }
        
        return wbc_actions, info

    def _extract_instruction(self, obs: dict[str, np.ndarray]) -> str:
        """Extract instruction from known WBC keys."""
        if self.instruction_override is not None and self.instruction_override.strip():
            return self.instruction_override.strip()
        candidate_keys = [
            self.instruction_key,
            "annotation.human.task_description",
            "language.language_instruction",
            "language_instruction",
            "task",
        ]
        for key in candidate_keys:
            if key not in obs:
                continue
            value = obs[key]
            if isinstance(value, np.ndarray):
                value = value.item() if value.ndim == 0 else value[0]
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return "do something"

    @staticmethod
    def _flatten_first(value: np.ndarray | Any) -> np.ndarray:
        """Convert value to float32 vector and remove optional batch dimension."""
        arr = np.asarray(value)
        if arr.ndim > 1:
            arr = arr[0]
        return arr.astype(np.float32).reshape(-1)

    def _extract_current_q(self, obs: dict[str, np.ndarray]) -> np.ndarray | None:
        """Extract current 43-DoF whole-body q if available."""
        if "q" in obs:
            q = self._flatten_first(obs["q"])
            if q.size >= 43:
                return q[:43].astype(np.float32)
        if "body_q" in obs:
            q = self._flatten_first(obs["body_q"])
            if q.size >= 43:
                return q[:43].astype(np.float32)
        return None

    @staticmethod
    def _quat_wxyz_to_rpy(quat_wxyz: np.ndarray) -> np.ndarray:
        """Convert quaternion [w, x, y, z] to [roll, pitch, yaw]."""
        w, x, y, z = quat_wxyz.astype(np.float64)
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)

        sinp = 2.0 * (w * y - z * x)
        sinp = np.clip(sinp, -1.0, 1.0)
        pitch = np.arcsin(sinp)

        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)
        return np.array([roll, pitch, yaw], dtype=np.float32)

    def _extract_psi0_state(self, obs: dict[str, np.ndarray]) -> np.ndarray:
        """
        Build 36-dim Psi0 state:
        [hand(14), arm(14), torso_rpy(3), torso_height(1), pad(4)].
        """
        if "states" in obs:
            state = self._flatten_first(obs["states"])
        elif "state" in obs:
            state = self._flatten_first(obs["state"])
        elif "q" in obs:
            q = self._flatten_first(obs["q"])
            if q.size >= 43:
                # G1 joint groups in pinocchio order for this WBC stack:
                # left_arm [15:22], right_arm [29:36], left_hand [22:29], right_hand [36:43], waist [12:15]
                hand = np.concatenate([q[22:29], q[36:43]], axis=0)
                arm = np.concatenate([q[15:22], q[29:36]], axis=0)
                if "floating_base_pose" in obs:
                    fb = self._flatten_first(obs["floating_base_pose"])
                    if fb.size >= 7:
                        torso_rpy = self._quat_wxyz_to_rpy(fb[3:7])
                        torso_h = np.array([fb[2]], dtype=np.float32)
                    else:
                        torso_rpy = np.zeros(3, dtype=np.float32)
                        torso_h = np.array([0.75], dtype=np.float32)
                else:
                    torso_rpy = np.zeros(3, dtype=np.float32)
                    torso_h = np.array([0.75], dtype=np.float32)
                state32 = np.concatenate([hand, arm, torso_rpy, torso_h], axis=0).astype(np.float32)
                state = state32
            else:
                state = q.astype(np.float32)
        elif "body_q" in obs:
            state = self._flatten_first(obs["body_q"])
        else:
            state = np.zeros(32, dtype=np.float32)

        if state.size < 36:
            state = np.pad(state, (0, 36 - state.size), mode="constant", constant_values=0)
        elif state.size > 36:
            state = state[:36]
        return state.astype(np.float32)

    def _request_psi0_action(
        self,
        image: np.ndarray,
        state: np.ndarray,
        instruction: str,
    ) -> np.ndarray:
        """
        Call Psi0 server and return action tensor.
        
        Args:
            image: (H, W, 3) uint8 RGB image (will be resized to 240x320 for Psi0)
            state: (n_joints,) float32 joint positions
            instruction: str task description
        
        Returns:
            (30, 36) float32 action array with timesteps × DOFs
        """
        # Ensure proper dtypes
        image = image.astype(np.uint8)
        state = state.astype(np.float32)
        
        # Resize image if needed (Psi0 model expects 240x320)
        if image.shape != (240, 320, 3):
            import cv2
            image = cv2.resize(image, (320, 240), interpolation=cv2.INTER_LINEAR)
        
        # Build request payload matching Psi0 API
        payload = {
            "image": {"egocentric": image},
            "instruction": instruction,
            "history": {"reset": True} if self._pending_reset else {},
            "state": {"states": state[np.newaxis, :].astype(np.float32)},
            "condition": {},
            "gt_action": np.zeros((self.action_horizon, 36), dtype=np.float32),
            "dataset_name": "real",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        
        # Serialize numpy arrays
        payload = convert_numpy_in_dict(payload, numpy_serialize)
        
        # Make HTTP request
        try:
            response = self.session.post(self.server_url, json=payload, timeout=self.timeout_s)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Psi0 server request failed: {e}")
        
        # Deserialize response
        body = convert_numpy_in_dict(response.json(), numpy_deserialize)
        
        if not isinstance(body, dict) or "action" not in body:
            raise RuntimeError(f"Unexpected Psi0 response format: {body}")
        
        action = np.asarray(body["action"], dtype=np.float32)
        
        # Validate action shape
        if action.ndim != 2 or action.shape != (self.action_horizon, 36):
            raise ValueError(
                f"Expected Psi0 action shape ({self.action_horizon}, 36), got {action.shape}"
            )
        self._pending_reset = False
        
        return action

    def _convert_psi0_to_wbc_actions(
        self,
        psi0_action: np.ndarray,
        current_q: np.ndarray | None = None,
    ) -> dict[str, np.ndarray]:
        """
        Convert Psi0 output (30, 36) to WBC action format.
        
        Psi0 action structure (36 DOFs, task1 checkpoint):
        - [0:7] left hand
        - [7:14] right hand
        - [14:21] left arm
        - [21:28] right arm
        - [28:31] torso rpy / waist-like command
        - [31:32] torso height-like command
        - [32:36] zero-padded channels
        
        G1 robot q structure (43 DOFs total per g1_body29_hand14.xml):
        - q[0:29] = body DOFs (29 actuated mechanical joints - legs, waist, arms excluded)
        - q[29:36] = left hand (7 DOFs for Inspire dexterous hand)
        - q[36:43] = right hand (7 DOFs for Inspire dexterous hand)
        
        Hand control: WBC expects hand position commands directly in q[29:43].
        Arm control: Handled via "action.left_arm"/"action.right_arm" keys (IK layer).
        """
        steps = psi0_action.shape[0]
        left_hand = psi0_action[:, 0:7]
        right_hand = psi0_action[:, 7:14]
        left_arm = psi0_action[:, 14:21]
        right_arm = psi0_action[:, 21:28]
        waist = psi0_action[:, 28:31]
        base_height = psi0_action[:, 31:32]
        navigate = psi0_action[:, 32:35]

        # Build full-body q from current posture (do not zero unrelated joints).
        if current_q is not None and current_q.size >= 43:
            q_base = current_q[:43].astype(np.float32)
        else:
            q_base = np.zeros(43, dtype=np.float32)
        q_trajectory = np.repeat(q_base[np.newaxis, :], steps, axis=0)

        # Pinocchio-order indices for G1 in this WBC environment.
        q_trajectory[:, 15:22] = left_arm
        q_trajectory[:, 29:36] = right_arm
        q_trajectory[:, 22:29] = left_hand
        q_trajectory[:, 36:43] = right_hand
        q_trajectory[:, 12:15] = waist

        # Default integration uses WBC lower-body balance policy. Psi0 task1 channels
        # 31:35 are not reliable lower-body commands, so they are opt-in.
        wbc_actions = {
            "action.left_arm": left_arm[np.newaxis, :, :],
            "action.right_arm": right_arm[np.newaxis, :, :],
            "action.left_hand": left_hand[np.newaxis, :, :],
            "action.right_hand": right_hand[np.newaxis, :, :],
            "action.waist": waist[np.newaxis, :, :],
        }

        if self.use_psi0_base_height:
            wbc_actions["action.base_height_command"] = base_height[np.newaxis, :, :]
        if self.use_psi0_navigate_command:
            wbc_actions["action.navigate_command"] = navigate[np.newaxis, :, :]
        if self.emit_q:
            wbc_actions["q"] = q_trajectory
        
        
        return wbc_actions


if __name__ == "__main__":
    # Quick validation of conversion logic
    dummy_psi0_action = np.random.randn(30, 36).astype(np.float32)
    policy = Psi0WBCPolicy()
    wbc_actions = policy._convert_psi0_to_wbc_actions(dummy_psi0_action)
    
    print("WBC Action Format Validation:")
    for key in sorted(wbc_actions.keys()):
        shape = wbc_actions[key].shape
        print(f"  {key}: {shape}")
    
    expected_shapes = {
        "action.left_arm": (1, 30, 7),
        "action.right_arm": (1, 30, 7),
        "action.left_hand": (1, 30, 7),
        "action.right_hand": (1, 30, 7),
        "action.waist": (1, 30, 3),
        "action.base_height_command": (1, 30, 1),
        "action.navigate_command": (1, 30, 3),
    }
    
    all_match = all(
        wbc_actions[key].shape == expected_shapes[key]
        for key in expected_shapes
    )
    print(f"\nAll shapes match expected: {all_match}")
