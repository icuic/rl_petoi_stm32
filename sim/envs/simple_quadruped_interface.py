"""Shared control-interface constants for the minimal quadruped."""

from __future__ import annotations

import numpy as np

OBSERVATION_DIM = 29
ACTION_DIM = 8

JOINT_NAMES = (
    "front_left_hip",
    "front_left_knee",
    "front_right_hip",
    "front_right_knee",
    "rear_left_hip",
    "rear_left_knee",
    "rear_right_hip",
    "rear_right_knee",
)

OBSERVATION_LAYOUT = (
    ("torso_height_m", 0, 1),
    ("torso_quat_wxyz", 1, 5),
    ("base_linear_angular_velocity", 5, 11),
    ("joint_position_rad", 11, 19),
    ("joint_velocity_rad_s", 19, 27),
    ("phase_sin_cos", 27, 29),
)

ACTION_LAYOUT = tuple((name, index) for index, name in enumerate(JOINT_NAMES))

NEUTRAL_POSE_RAD = np.array(
    [0.15, -0.75, 0.15, -0.75, -0.15, -0.75, -0.15, -0.75],
    dtype=np.float32,
)

ACTION_SCALE_RAD = np.array([0.55] * ACTION_DIM, dtype=np.float32)


def normalized_action_to_joint_targets(action: np.ndarray) -> np.ndarray:
    """Map normalized actions in [-1, 1] to joint target angles in radians."""
    clipped_action = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
    return NEUTRAL_POSE_RAD + clipped_action * ACTION_SCALE_RAD
