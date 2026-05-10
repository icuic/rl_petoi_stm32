"""Open-loop gait references for quadruped bring-up."""

from __future__ import annotations

import numpy as np

DEFAULT_PETOI_STAND_POSE = np.array(
    [0.2, 1.4, 0.2, 1.4, 0.2, 1.4, 0.2, 1.4],
    dtype=np.float32,
)


def trot_reference(
    phase: float,
    stand_pose: np.ndarray | None = None,
    shoulder_amplitude: float = 0.12,
    knee_amplitude: float = 0.10,
    duty_bias: float = 0.0,
) -> np.ndarray:
    """Return an 8D symmetric trot joint target around a stand pose.

    Joint order is:
    RF shoulder, RF knee, RR shoulder, RR knee, LF shoulder, LF knee, LR shoulder,
    LR knee. The diagonal pairs RF/LR and LF/RR move in opposite phase.
    """

    base = DEFAULT_PETOI_STAND_POSE if stand_pose is None else np.asarray(stand_pose, dtype=np.float32)
    if base.shape != (8,):
        raise ValueError(f"stand_pose must have shape (8,), got {base.shape}")

    angle = 2.0 * np.pi * float(phase)
    diagonal_a = np.sin(angle)
    diagonal_b = -diagonal_a
    knee_a = np.sin(angle + np.pi / 2.0) + duty_bias
    knee_b = np.sin(angle - np.pi / 2.0) + duty_bias

    offsets = np.array(
        [
            shoulder_amplitude * diagonal_a,
            knee_amplitude * knee_a,
            shoulder_amplitude * diagonal_b,
            knee_amplitude * knee_b,
            shoulder_amplitude * diagonal_b,
            knee_amplitude * knee_b,
            shoulder_amplitude * diagonal_a,
            knee_amplitude * knee_a,
        ],
        dtype=np.float32,
    )
    return base + offsets
