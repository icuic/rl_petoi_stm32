#!/usr/bin/env python3
"""Run the official OpenCat Bittle wkF gait frames through the RL serial link."""

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

DEFAULT_SOURCE = (
    ROOT_DIR
    / "third_party/petoi/OpenCatEsp32-Quadruped-Robot/src/InstinctBittleESP.h"
)


def parse_wkf_frames(source: Path) -> tuple[list[int], list[list[float]]]:
    text = source.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"const\s+int8_t\s+wkF\[\]\s+PROGMEM\s*=\s*\{(.*?)\};", text, re.S)
    if not match:
        raise SystemExit(f"wkF array not found in {source}")
    values = [int(value) for value in re.findall(r"-?\d+", match.group(1))]
    if len(values) < 12:
        raise SystemExit(f"wkF array is too short in {source}")
    header = values[:4]
    frame_count = header[0]
    raw = values[4 : 4 + frame_count * 8]
    if len(raw) != frame_count * 8:
        raise SystemExit(f"wkF expected {frame_count} frames, found {len(raw) // 8}")
    frames = [[float(value) for value in raw[index : index + 8]] for index in range(0, len(raw), 8)]
    return header, frames


def require_flag(decoded: dict[str, Any], flag: str, label: str) -> None:
    if flag not in decoded.get("status_flags", []):
        raise RuntimeError(f"{label} missing {flag}: {decoded}")


def check_state(decoded: dict[str, Any], label: str, roll_pitch_limit: float, summary: dict[str, Any]) -> dict[str, Any]:
    require_flag(decoded, "telemetry_valid", label)
    state = decoded.get("state")
    if not isinstance(state, dict):
        raise RuntimeError(f"{label} missing state: {decoded}")
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
    if roll > roll_pitch_limit or pitch > roll_pitch_limit:
        raise RuntimeError(f"{label} abort: roll={roll:.4f}, pitch={pitch:.4f}")
    return state


def radians(values_deg: list[float]) -> list[float]:
    return [math.radians(value) for value in values_deg]


def joint_stats(frames: list[list[float]]) -> dict[str, list[float]]:
    mins = [min(frame[joint] for frame in frames) for joint in range(8)]
    maxs = [max(frame[joint] for frame in frames) for joint in range(8)]
    means = [sum(frame[joint] for frame in frames) / len(frames) for joint in range(8)]
    spans = [maxs[joint] - mins[joint] for joint in range(8)]
    return {"min_deg": mins, "max_deg": maxs, "mean_deg": means, "span_deg": spans}


def scale_frames(frames: list[list[float]], scale: float) -> tuple[list[float], list[list[float]]]:
    stats = joint_stats(frames)
    center = stats["mean_deg"]
    scaled = [
        [center[joint] + scale * (frame[joint] - center[joint]) for joint in range(8)]
        for frame in frames
    ]
    return center, scaled


def lerp(start: list[float], end: list[float], alpha: float) -> list[float]:
    return [start[index] + (end[index] - start[index]) * alpha for index in range(8)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--port", default=None)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--rl-token", default="Y")
    parser.add_argument("--scale", type=float, default=0.25, help="Scale around the official wkF per-joint mean.")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--period", type=float, default=0.035)
    parser.add_argument("--stride", type=int, default=2, help="Use every Nth wkF frame.")
    parser.add_argument("--max-frames", type=int, default=0, help="Limit gait frames per round after striding; 0 means all.")
    parser.add_argument("--ramp-steps", type=int, default=8)
    parser.add_argument("--state-every", type=int, default=12)
    parser.add_argument("--roll-pitch-limit", type=float, default=0.35)
    parser.add_argument("--sequence-id", type=int, default=2000)
    parser.add_argument("--return-command", default="kup", help="Raw OpenCat command to send after the run; empty disables it.")
    parser.add_argument("--allow-motion", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.scale < 0:
        raise SystemExit("--scale must be >= 0")
    if args.rounds < 1:
        raise SystemExit("--rounds must be >= 1")
    if args.period < 0:
        raise SystemExit("--period must be >= 0")
    if args.stride < 1:
        raise SystemExit("--stride must be >= 1")
    if args.ramp_steps < 0:
        raise SystemExit("--ramp-steps must be >= 0")
    if args.state_every < 0:
        raise SystemExit("--state-every must be >= 0")
    if len(args.rl_token.encode("latin1")) != 1:
        raise SystemExit("--rl-token must encode to exactly one byte")

    header, official_frames = parse_wkf_frames(args.source)
    center_deg, scaled_frames = scale_frames(official_frames, args.scale)
    frames = scaled_frames[:: args.stride]
    if args.max_frames:
        frames = frames[: args.max_frames]
    stats = joint_stats(frames)
    summary: dict[str, Any] = {
        "source": str(args.source),
        "official_header": header,
        "official_frames": len(official_frames),
        "scale": args.scale,
        "rounds_requested": args.rounds,
        "period": args.period,
        "stride": args.stride,
        "frames_per_round": len(frames),
        "ramp_steps": args.ramp_steps,
        "state_every": args.state_every,
        "center_deg": center_deg,
        "scaled_min_deg": stats["min_deg"],
        "scaled_max_deg": stats["max_deg"],
        "scaled_span_deg": stats["span_deg"],
        "set_targets": 0,
        "states": 0,
        "max_abs_roll": 0.0,
        "max_abs_pitch": 0.0,
        "max_abs_angular_velocity": 0.0,
    }
    events: list[dict[str, Any]] = []

    if not args.port:
        print(json.dumps({"summary": summary, "first_frame_deg": frames[0], "last_frame_deg": frames[-1]}, indent=2))
        return
    if not args.allow_motion:
        raise SystemExit("--allow-motion is required before sending wkF targets to hardware.")

    try:
        import serial
    except ImportError as exc:
        raise SystemExit("pyserial is required for --port. Install it with: python3 -m pip install pyserial") from exc

    seq = args.sequence_id
    token = args.rl_token.encode("latin1")
    with serial.Serial(args.port, args.baud, timeout=args.timeout) as port:
        time.sleep(0.3)
        port.reset_input_buffer()
        try:
            state_frame = serial_frame_to_json(send_serial_request(port, encode_get_state_request(seq), token))
            state = check_state(state_frame, "initial_state", args.roll_pitch_limit, summary)
            current = [math.degrees(float(value)) for value in state["joint_feedback"]]
            seq += 1

            if args.ramp_steps:
                for ramp_index in range(args.ramp_steps):
                    target_deg = lerp(current, frames[0], (ramp_index + 1) / args.ramp_steps)
                    response = serial_frame_to_json(
                        send_serial_request(port, encode_set_targets_request(seq, radians(target_deg)), token)
                    )
                    require_flag(response, "command_accepted", f"ramp_{ramp_index}")
                    summary["set_targets"] += 1
                    seq += 1
                    time.sleep(args.period)

            target_counter = 0
            for round_index in range(args.rounds):
                for frame_index, target_deg in enumerate(frames):
                    response = serial_frame_to_json(
                        send_serial_request(port, encode_set_targets_request(seq, radians(target_deg)), token)
                    )
                    require_flag(response, "command_accepted", f"round_{round_index}_frame_{frame_index}")
                    summary["set_targets"] += 1
                    target_counter += 1
                    if not args.summary_only:
                        events.append(
                            {
                                "round": round_index + 1,
                                "frame": frame_index,
                                "sequence_id": seq,
                                "target_deg": target_deg,
                            }
                        )
                    seq += 1
                    time.sleep(args.period)

                    if args.state_every and target_counter % args.state_every == 0:
                        state_frame = serial_frame_to_json(send_serial_request(port, encode_get_state_request(seq), token))
                        check_state(state_frame, f"round_{round_index}_frame_{frame_index}_state", args.roll_pitch_limit, summary)
                        seq += 1

            state_frame = serial_frame_to_json(send_serial_request(port, encode_get_state_request(seq), token))
            check_state(state_frame, "final_state", args.roll_pitch_limit, summary)
            seq += 1
        finally:
            if args.return_command:
                command = args.return_command.encode("ascii") + b"\n"
                port.reset_input_buffer()
                port.write(command)
                port.flush()
                time.sleep(0.8)
                reply = port.read(4096).decode("utf-8", "replace")
                events.append({"event": "return_command", "command": args.return_command, "reply": reply})

    output = {"summary": summary}
    if not args.summary_only:
        output["events"] = events
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
