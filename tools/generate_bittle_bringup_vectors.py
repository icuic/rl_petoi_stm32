#!/usr/bin/env python3
"""Generate conservative Bittle bring-up target vectors and RL serial frames."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Iterable

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "tools"))

from rl_serial_protocol_v0 import encode_get_state_request, encode_set_targets_request

ACTION_DIM = 8


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def rounded(values: Iterable[float]) -> list[float]:
    return [round(float(value), 6) for value in values]


def checked_targets(raw_targets: Iterable[float], neutral: list[float], max_delta: float) -> list[float]:
    targets = []
    for value, center in zip(raw_targets, neutral):
        targets.append(clamp(float(value), center - max_delta, center + max_delta))
    if len(targets) != ACTION_DIM:
        raise ValueError(f"expected {ACTION_DIM} joint targets, got {len(targets)}")
    return rounded(targets)


def make_frame(sequence_id: int, targets: list[float], rl_token: str) -> dict[str, object]:
    frame = encode_set_targets_request(sequence_id, targets)
    return {
        "sequence_id": sequence_id,
        "message_type": "RL_SET_TARGETS_REQ",
        "target_joint_rad": targets,
        "frame_hex": frame.hex(),
        "wire_hex_with_default_token": (rl_token.encode("latin1") + frame).hex(),
    }


def generate_vectors(config: dict[str, object], rl_token: str) -> dict[str, object]:
    neutral = [float(value) for value in config["neutral_pose_rad"]]
    joint_order = list(config["joint_order"])
    limits = config["first_day_soft_limit_rad"]
    reference = config["low_amplitude_reference"]

    max_delta = float(limits["max_abs_delta_from_neutral"])
    single_delta = float(limits["max_single_joint_test_delta"])
    gait_delta = float(limits["max_low_amplitude_gait_delta"])
    shoulder_amp = float(reference["shoulder_amplitude_rad"])
    knee_amp = float(reference["knee_amplitude_rad"])
    phase_count = int(reference["phase_count"])

    frames: list[dict[str, object]] = []
    sequence_id = 1

    get_state_frame = encode_get_state_request(sequence_id)
    get_state = {
        "sequence_id": sequence_id,
        "message_type": "RL_GET_STATE_REQ",
        "frame_hex": get_state_frame.hex(),
        "wire_hex_with_default_token": (rl_token.encode("latin1") + get_state_frame).hex(),
    }
    sequence_id += 1

    frames.append(make_frame(sequence_id, checked_targets(neutral, neutral, max_delta), rl_token))
    sequence_id += 1

    for joint_index, joint_name in enumerate(joint_order):
        for direction, label in ((1.0, "positive"), (-1.0, "negative")):
            targets = list(neutral)
            targets[joint_index] += direction * single_delta
            frame = make_frame(sequence_id, checked_targets(targets, neutral, max_delta), rl_token)
            frame["test"] = f"single_joint_{joint_index}_{label}"
            frame["joint_name"] = joint_name
            frames.append(frame)
            sequence_id += 1

    for phase_index in range(phase_count):
        phase = phase_index / phase_count
        angle = 2.0 * math.pi * phase
        diagonal_a = math.sin(angle)
        diagonal_b = -diagonal_a
        knee_a = math.sin(angle + math.pi / 2.0)
        knee_b = math.sin(angle - math.pi / 2.0)
        offsets = [
            shoulder_amp * diagonal_a,
            knee_amp * knee_a,
            shoulder_amp * diagonal_b,
            knee_amp * knee_b,
            shoulder_amp * diagonal_b,
            knee_amp * knee_b,
            shoulder_amp * diagonal_a,
            knee_amp * knee_a,
        ]
        raw_targets = [center + offset for center, offset in zip(neutral, offsets)]
        frame = make_frame(sequence_id, checked_targets(raw_targets, neutral, gait_delta), rl_token)
        frame["test"] = f"low_amplitude_reference_phase_{phase_index:02d}"
        frame["phase"] = round(phase, 6)
        frames.append(frame)
        sequence_id += 1

    return {
        "version": "bittle_bringup_vectors_v0",
        "source_config": config["version"],
        "rl_token": rl_token,
        "joint_order": joint_order,
        "neutral_pose_rad": rounded(neutral),
        "safety": {
            "first_day_soft_limit_rad": limits,
            "runtime_abort_gate": config["runtime_abort_gate"],
        },
        "get_state_request": get_state,
        "set_target_sequence": frames,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT_DIR / "protocol/bittle_bringup_safety_v0.json",
        help="Safety config JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT_DIR / "protocol/test_vectors/bittle_bringup_v0.json",
        help="Output JSON vector path.",
    )
    parser.add_argument("--rl-token", default="Y", help="OpenCat token prepended to RL frames for wire_hex output.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.config.open("r", encoding="utf-8") as f:
        config = json.load(f)
    vectors = generate_vectors(config, args.rl_token)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(vectors, f, indent=2)
        f.write("\n")
    print(f"Saved Bittle bring-up vectors to {args.output}")


if __name__ == "__main__":
    main()
