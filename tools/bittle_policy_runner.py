#!/usr/bin/env python3
"""Run a guarded policy-in-the-loop Bittle controller over RL serial."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "tools"))

from rl_serial_protocol_v0 import (
    encode_get_state_request,
    encode_set_targets_request,
    send_serial_request,
    serial_frame_to_json,
)

DEFAULT_ACTION_SCALE_VALUES = (0.07, 0.055, 0.07, 0.055, 0.07, 0.055, 0.07, 0.055)
PROFILE_TO_SAFETY = {
    "crouch": ROOT_DIR / "protocol/bittle_bringup_safety_v0.json",
    "stand-up": ROOT_DIR / "protocol/bittle_stand_safety_v0.json",
}
DEFAULT_WKF_SOURCE = (
    ROOT_DIR
    / "third_party/petoi/OpenCatEsp32-Quadruped-Robot/src/InstinctBittleESP.h"
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def require_flag(decoded: dict[str, Any], flag: str, label: str) -> None:
    if flag not in decoded.get("status_flags", []):
        raise RuntimeError(f"{label} missing {flag}: {decoded}")


def telemetry_state(decoded: dict[str, Any], label: str) -> dict[str, Any]:
    require_flag(decoded, "telemetry_valid", label)
    state = decoded.get("state")
    if not isinstance(state, dict):
        raise RuntimeError(f"{label} missing state: {decoded}")
    return state


def low_reference(phase: float, neutral: np.ndarray, shoulder_amp: float, knee_amp: float) -> np.ndarray:
    angle = 2.0 * math.pi * float(phase % 1.0)
    diagonal_a = math.sin(angle)
    diagonal_b = -diagonal_a
    knee_a = math.sin(angle + math.pi / 2.0)
    knee_b = math.sin(angle - math.pi / 2.0)
    offsets = np.array(
        [
            shoulder_amp * diagonal_a,
            knee_amp * knee_a,
            shoulder_amp * diagonal_b,
            knee_amp * knee_b,
            knee_amp * 0.0 + shoulder_amp * diagonal_b,
            knee_amp * knee_b,
            shoulder_amp * diagonal_a,
            knee_amp * knee_a,
        ],
        dtype=np.float32,
    )
    return neutral + offsets


def parse_wkf_frames(source: Path) -> list[list[float]]:
    text = source.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"const\s+int8_t\s+wkF\[\]\s+PROGMEM\s*=\s*\{(.*?)\};", text, re.S)
    if not match:
        raise SystemExit(f"wkF array not found in {source}")
    values = [int(value) for value in re.findall(r"-?\d+", match.group(1))]
    frame_count = values[0]
    raw = values[4 : 4 + frame_count * 8]
    if len(raw) != frame_count * 8:
        raise SystemExit(f"wkF expected {frame_count} frames, found {len(raw) // 8}")
    return [[float(value) for value in raw[index : index + 8]] for index in range(0, len(raw), 8)]


def scaled_wkf_reference(source: Path, scale: float, stride: int) -> np.ndarray:
    frames = parse_wkf_frames(source)
    if stride < 1:
        raise SystemExit("--wkf-stride must be >= 1")
    means = [sum(frame[joint] for frame in frames) / len(frames) for joint in range(8)]
    scaled = [
        [math.radians(means[joint] + scale * (frame[joint] - means[joint])) for joint in range(8)]
        for frame in frames[::stride]
    ]
    return np.asarray(scaled, dtype=np.float32)


def build_observation(
    state: dict[str, Any],
    phase: float,
    previous_action: np.ndarray,
    joint_source: str,
    policy_joint_reference: np.ndarray,
) -> np.ndarray:
    if joint_source == "telemetry":
        joints = np.asarray(state["joint_feedback"], dtype=np.float32)
    else:
        joints = policy_joint_reference.astype(np.float32)

    phase_angle = 2.0 * math.pi * float(phase % 1.0)
    return np.concatenate(
        [
            np.array(
                [
                    float(state["roll"]),
                    float(state["pitch"]),
                    float(state["angular_velocity_x"]),
                    float(state["angular_velocity_y"]),
                    float(state["angular_velocity_z"]),
                ],
                dtype=np.float32,
            ),
            joints,
            previous_action.astype(np.float32),
            np.array([math.sin(phase_angle), math.cos(phase_angle)], dtype=np.float32),
        ]
    ).reshape(1, -1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default=None)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--rl-token", default="Y")
    parser.add_argument("--onnx", type=Path, default=ROOT_DIR / "models/onnx/petoi_bittle_v0_gait_quality_v2_30k_actor.onnx")
    parser.add_argument("--profile", choices=sorted(PROFILE_TO_SAFETY), default="crouch")
    parser.add_argument("--safety", type=Path, default=None, help="Override the safety/profile JSON.")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--period", type=float, default=0.05)
    parser.add_argument("--phase-delta", type=float, default=1.0 / 8.0)
    parser.add_argument("--residual-scale", type=float, default=1.0)
    parser.add_argument("--reference-mode", choices=["low-sine", "wkf"], default="low-sine")
    parser.add_argument("--wkf-source", type=Path, default=DEFAULT_WKF_SOURCE)
    parser.add_argument("--wkf-scale", type=float, default=0.5)
    parser.add_argument("--wkf-stride", type=int, default=2)
    parser.add_argument("--ramp-steps", type=int, default=0)
    parser.add_argument(
        "--state-every",
        type=int,
        default=1,
        help="Read GET_STATE every N policy steps. 1 is fully closed-loop; larger values reduce serial latency.",
    )
    parser.add_argument("--roll-pitch-limit", type=float, default=0.25)
    parser.add_argument("--max-delta-rad", type=float, default=0.12)
    parser.add_argument("--joint-observation-source", choices=["canonical", "telemetry"], default="canonical")
    parser.add_argument("--allow-motion", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.steps < 1:
        raise SystemExit("--steps must be >= 1")
    if args.period < 0:
        raise SystemExit("--period must be >= 0")
    if args.ramp_steps < 0:
        raise SystemExit("--ramp-steps must be >= 0")
    if args.state_every < 1:
        raise SystemExit("--state-every must be >= 1")
    if args.port and not args.allow_motion:
        raise SystemExit("--allow-motion is required before controlling hardware")

    if not args.port:
        print(
            json.dumps(
                {
                    "onnx": str(args.onnx),
                    "profile": args.profile,
                    "safety": str(args.safety or PROFILE_TO_SAFETY[args.profile]),
                    "steps": args.steps,
                    "period": args.period,
                    "phase_delta": args.phase_delta,
                    "residual_scale": args.residual_scale,
                    "reference_mode": args.reference_mode,
                    "wkf_source": str(args.wkf_source),
                    "wkf_scale": args.wkf_scale,
                    "wkf_stride": args.wkf_stride,
                    "ramp_steps": args.ramp_steps,
                    "state_every": args.state_every,
                    "joint_observation_source": args.joint_observation_source,
                    "max_delta_rad": args.max_delta_rad,
                },
                indent=2,
            )
        )
        return

    global np
    try:
        import numpy as np
        import onnxruntime as ort
        import serial
    except ImportError as exc:
        raise SystemExit(f"missing runtime dependency: {exc}") from exc

    safety_path = args.safety or PROFILE_TO_SAFETY[args.profile]
    safety = load_json(safety_path)
    neutral = np.asarray(safety["neutral_pose_rad"], dtype=np.float32)
    low_ref = safety["low_amplitude_reference"]
    shoulder_amp = float(low_ref["shoulder_amplitude_rad"])
    knee_amp = float(low_ref["knee_amplitude_rad"])
    wkf_reference = None
    if args.reference_mode == "wkf":
        wkf_reference = scaled_wkf_reference(args.wkf_source, args.wkf_scale, args.wkf_stride)
    policy_joint_reference = np.array([0.2, 1.4, 0.2, 1.4, 0.2, 1.4, 0.2, 1.4], dtype=np.float32)

    session = ort.InferenceSession(str(args.onnx), providers=["CPUExecutionProvider"])
    action_scale = np.asarray(DEFAULT_ACTION_SCALE_VALUES, dtype=np.float32)
    previous_action = np.zeros(8, dtype=np.float32)
    phase = 0.0
    seq = 1200
    token = args.rl_token.encode("latin1")
    summary: dict[str, Any] = {
        "steps_requested": args.steps,
        "profile": args.profile,
        "safety": str(safety_path),
        "period": args.period,
        "phase_delta": args.phase_delta,
        "residual_scale": args.residual_scale,
        "reference_mode": args.reference_mode,
        "wkf_source": str(args.wkf_source),
        "wkf_scale": args.wkf_scale,
        "wkf_stride": args.wkf_stride,
        "wkf_reference_frames": 0 if wkf_reference is None else int(wkf_reference.shape[0]),
        "ramp_steps": args.ramp_steps,
        "state_every": args.state_every,
        "joint_observation_source": args.joint_observation_source,
        "set_targets": 0,
        "states": 0,
        "max_abs_roll": 0.0,
        "max_abs_pitch": 0.0,
        "max_abs_angular_velocity": 0.0,
        "max_abs_action": 0.0,
        "max_abs_delta_rad": 0.0,
    }
    events: list[dict[str, Any]] = []

    def update_state_summary(state: dict[str, Any], label: str) -> None:
        roll = abs(float(state["roll"]))
        pitch = abs(float(state["pitch"]))
        angular = max(
            abs(float(state["angular_velocity_x"])),
            abs(float(state["angular_velocity_y"])),
            abs(float(state["angular_velocity_z"])),
        )
        summary["states"] += 1
        summary["max_abs_roll"] = max(summary["max_abs_roll"], roll)
        summary["max_abs_pitch"] = max(summary["max_abs_pitch"], pitch)
        summary["max_abs_angular_velocity"] = max(summary["max_abs_angular_velocity"], angular)
        if roll > args.roll_pitch_limit or pitch > args.roll_pitch_limit:
            raise RuntimeError(f"{label} abort: roll={roll:.4f}, pitch={pitch:.4f}")

    with serial.Serial(args.port, args.baud, timeout=args.timeout) as port:
        time.sleep(0.3)
        port.reset_input_buffer()
        try:
            neutral_resp = serial_frame_to_json(send_serial_request(port, encode_set_targets_request(seq, neutral), token))
            require_flag(neutral_resp, "command_accepted", "neutral_start")
            summary["set_targets"] += 1
            seq += 1
            time.sleep(args.period)

            if wkf_reference is not None and args.ramp_steps:
                for ramp_index in range(args.ramp_steps):
                    alpha = float(ramp_index + 1) / float(args.ramp_steps)
                    ramp_target = neutral + (wkf_reference[0] - neutral) * alpha
                    response = serial_frame_to_json(
                        send_serial_request(port, encode_set_targets_request(seq, ramp_target), token)
                    )
                    require_flag(response, "command_accepted", f"ramp_{ramp_index}_target")
                    summary["set_targets"] += 1
                    seq += 1
                    time.sleep(args.period)

            state_frame = serial_frame_to_json(send_serial_request(port, encode_get_state_request(seq), token))
            state = telemetry_state(state_frame, "initial_state")
            update_state_summary(state, "initial_state")
            seq += 1

            for step in range(args.steps):
                if step > 0 and step % args.state_every == 0:
                    state_frame = serial_frame_to_json(send_serial_request(port, encode_get_state_request(seq), token))
                    state = telemetry_state(state_frame, f"step_{step}_state")
                    update_state_summary(state, f"step_{step}_state")
                    seq += 1

                obs = build_observation(
                    state,
                    phase,
                    previous_action,
                    args.joint_observation_source,
                    policy_joint_reference,
                )
                action = session.run(["action"], {"observation": obs.astype(np.float32)})[0].reshape(-1).astype(np.float32)
                clipped_action = np.clip(action, -1.0, 1.0)
                if wkf_reference is None:
                    reference = low_reference(phase, neutral, shoulder_amp, knee_amp)
                    target_center = neutral
                else:
                    reference = wkf_reference[step % len(wkf_reference)]
                    target_center = reference
                raw_target = reference + clipped_action * action_scale * float(args.residual_scale)
                target = np.clip(raw_target, target_center - args.max_delta_rad, target_center + args.max_delta_rad)
                delta = target - target_center

                summary["max_abs_action"] = max(summary["max_abs_action"], float(np.max(np.abs(clipped_action))))
                summary["max_abs_delta_rad"] = max(summary["max_abs_delta_rad"], float(np.max(np.abs(delta))))

                response = serial_frame_to_json(send_serial_request(port, encode_set_targets_request(seq, target), token))
                require_flag(response, "command_accepted", f"step_{step}_target")
                summary["set_targets"] += 1
                if not args.summary_only:
                    events.append(
                        {
                            "step": step,
                            "sequence_id": seq,
                            "phase": phase,
                            "roll": float(state["roll"]),
                            "pitch": float(state["pitch"]),
                            "max_abs_action": float(np.max(np.abs(clipped_action))),
                            "max_abs_delta_rad": float(np.max(np.abs(delta))),
                        }
                    )
                seq += 1
                previous_action = clipped_action
                phase = (phase + args.phase_delta) % 1.0
                time.sleep(args.period)
        finally:
            neutral_resp = serial_frame_to_json(send_serial_request(port, encode_set_targets_request(seq, neutral), token))
            require_flag(neutral_resp, "command_accepted", "neutral_end")
            summary["set_targets"] += 1

    output = {"summary": summary}
    if not args.summary_only:
        output["events"] = events
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
