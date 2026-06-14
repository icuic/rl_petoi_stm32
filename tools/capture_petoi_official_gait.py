#!/usr/bin/env python3
"""Capture Petoi's own walking gait by issuing an official command and polling RL_GET_STATE."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT_DIR / "tools"))

from rl_serial_protocol_v0 import (
    encode_get_state_request,
    send_serial_request,
    serial_frame_to_json,
)


def require_state(decoded: dict[str, Any], label: str) -> dict[str, Any]:
    flags = decoded.get("status_flags", [])
    if "telemetry_valid" not in flags:
      raise RuntimeError(f"{label} missing telemetry_valid: {decoded}")
    state = decoded.get("state")
    if not isinstance(state, dict):
      raise RuntimeError(f"{label} missing state: {decoded}")
    return state


def stats(values: list[list[float]]) -> dict[str, list[float]]:
    if not values:
        return {"min": [], "max": [], "mean": [], "span": []}
    count = len(values)
    mins = [min(row[index] for row in values) for index in range(8)]
    maxs = [max(row[index] for row in values) for index in range(8)]
    means = [sum(row[index] for row in values) / count for index in range(8)]
    spans = [maxs[index] - mins[index] for index in range(8)]
    return {"min": mins, "max": maxs, "mean": means, "span": spans}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/ttyACM1")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=1.5)
    parser.add_argument("--rl-token", default="Y")
    parser.add_argument("--command", default="kwkF", help="Official OpenCat command, for example kwkF.")
    parser.add_argument("--stop-command", default="d", help="Raw command sent in finally; empty disables it.")
    parser.add_argument("--post-stop-command", default="kup", help="Optional second recovery command; empty disables it.")
    parser.add_argument("--after-open-delay", type=float, default=3.0)
    parser.add_argument("--command-settle", type=float, default=0.4)
    parser.add_argument("--duration", type=float, default=6.0)
    parser.add_argument("--period", type=float, default=0.08)
    parser.add_argument("--sequence-id", type=int, default=5000)
    parser.add_argument("--max-consecutive-errors", type=int, default=8)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON path. Defaults to artifacts/petoi_official_gait_capture_<timestamp>.json.",
    )
    parser.add_argument("--allow-motion", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.allow_motion:
        raise SystemExit("--allow-motion is required before sending an official walking command.")
    if len(args.rl_token.encode("latin1")) != 1:
        raise SystemExit("--rl-token must encode to exactly one byte")
    if args.duration <= 0:
        raise SystemExit("--duration must be > 0")
    if args.period <= 0:
        raise SystemExit("--period must be > 0")

    try:
        import serial
    except ImportError as exc:
        raise SystemExit("pyserial is required. Install it with: python3 -m pip install pyserial") from exc

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or ROOT_DIR / "artifacts" / f"petoi_official_gait_capture_{timestamp}.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    token = args.rl_token.encode("latin1")
    seq = args.sequence_id
    samples: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    started = time.monotonic()

    with serial.Serial(args.port, args.baud, timeout=args.timeout) as port:
        time.sleep(args.after_open_delay)
        port.reset_input_buffer()
        port.write(args.command.encode("ascii") + b"\n")
        port.flush()
        time.sleep(args.command_settle)

        capture_start = time.monotonic()
        consecutive_errors = 0
        try:
            while time.monotonic() - capture_start < args.duration:
                sample_start = time.monotonic()
                try:
                    decoded = serial_frame_to_json(
                        send_serial_request(port, encode_get_state_request(seq), token)
                    )
                    state = require_state(decoded, f"sample_{len(samples)}")
                    joints_rad = [float(value) for value in state["joint_feedback"]]
                    samples.append(
                        {
                            "t_s": sample_start - capture_start,
                            "sequence_id": seq,
                            "roll": float(state["roll"]),
                            "pitch": float(state["pitch"]),
                            "angular_velocity": [
                                float(state["angular_velocity_x"]),
                                float(state["angular_velocity_y"]),
                                float(state["angular_velocity_z"]),
                            ],
                            "joint_rad": joints_rad,
                            "joint_deg": [math.degrees(value) for value in joints_rad],
                            "status_flags": decoded.get("status_flags", []),
                        }
                    )
                    consecutive_errors = 0
                except Exception as exc:  # Keep the official gait running long enough to gather partial evidence.
                    consecutive_errors += 1
                    errors.append(
                        {
                            "t_s": sample_start - capture_start,
                            "sequence_id": seq,
                            "error": str(exc),
                        }
                    )
                    if consecutive_errors >= args.max_consecutive_errors:
                        break
                finally:
                    seq += 1

                elapsed = time.monotonic() - sample_start
                if elapsed < args.period:
                    time.sleep(args.period - elapsed)
        finally:
            for command in (args.stop_command, args.post_stop_command):
                if command:
                    port.reset_input_buffer()
                    port.write(command.encode("ascii") + b"\n")
                    port.flush()
                    time.sleep(0.5)

    joint_rad = [sample["joint_rad"] for sample in samples]
    joint_deg = [sample["joint_deg"] for sample in samples]
    summary = {
        "port": args.port,
        "baud": args.baud,
        "command": args.command,
        "duration_s": args.duration,
        "period_s": args.period,
        "samples": len(samples),
        "errors": len(errors),
        "elapsed_s": time.monotonic() - started,
        "joint_rad": stats(joint_rad),
        "joint_deg": stats(joint_deg),
        "max_abs_roll": max((abs(float(sample["roll"])) for sample in samples), default=0.0),
        "max_abs_pitch": max((abs(float(sample["pitch"])) for sample in samples), default=0.0),
    }
    payload = {
        "summary": summary,
        "samples": samples,
        "errors": errors,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "summary": summary}, indent=2))

    if not samples:
        raise SystemExit("no gait samples captured")


if __name__ == "__main__":
    main()
