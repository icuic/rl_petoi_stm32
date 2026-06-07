#!/usr/bin/env python3
"""Run guarded Bittle policy-shadow target sequences over the RL serial link."""

from __future__ import annotations

import argparse
import json
import math
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

MODE_TO_REPORT = {
    "residual-0p5": ROOT_DIR / "experiments/reports/policy_shadow_samples_v2_30k_scale0p5.json",
    "residual-1p0": ROOT_DIR / "experiments/reports/policy_shadow_samples_v2_30k_scale1p0.json",
    "hybrid-0p5": ROOT_DIR / "experiments/reports/policy_shadow_lowref_plus_residual_v2_30k_scale0p5.json",
    "hybrid-1p0": ROOT_DIR / "experiments/reports/policy_shadow_lowref_plus_residual_v2_30k_scale1p0.json",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_shadow_targets(path: Path) -> list[dict[str, Any]]:
    data = load_json(path)
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        raise SystemExit(f"shadow report has no samples: {path}")
    for index, sample in enumerate(samples):
        targets = sample.get("target_deg")
        if not isinstance(targets, list) or len(targets) != 8:
            raise SystemExit(f"sample {index} in {path} does not have 8 target_deg values")
    return samples


def load_neutral_targets(path: Path) -> list[float]:
    data = load_json(path)
    sequence = data.get("set_target_sequence")
    if not isinstance(sequence, list) or not sequence:
        raise SystemExit(f"bring-up vectors have no set_target_sequence: {path}")
    neutral = sequence[0].get("target_joint_rad")
    if not isinstance(neutral, list) or len(neutral) != 8:
        raise SystemExit(f"neutral target is missing or invalid in {path}")
    return [float(value) for value in neutral]


def require_status_flag(decoded: dict[str, Any], flag: str, label: str) -> None:
    flags = decoded.get("status_flags", [])
    if flag not in flags:
        raise RuntimeError(f"{label} missing {flag}: {decoded}")


def check_state(decoded: dict[str, Any], label: str, roll_pitch_limit: float, summary: dict[str, Any]) -> tuple[float, float]:
    require_status_flag(decoded, "telemetry_valid", label)
    state = decoded.get("state", {})
    if not isinstance(state, dict):
        raise RuntimeError(f"{label} missing state: {decoded}")
    roll = float(state.get("roll", 99.0))
    pitch = float(state.get("pitch", 99.0))
    angular_velocity = [
        abs(float(state.get("angular_velocity_x", 0.0))),
        abs(float(state.get("angular_velocity_y", 0.0))),
        abs(float(state.get("angular_velocity_z", 0.0))),
    ]
    summary["states"] += 1
    summary["max_abs_roll"] = max(summary["max_abs_roll"], abs(roll))
    summary["max_abs_pitch"] = max(summary["max_abs_pitch"], abs(pitch))
    summary["max_abs_angular_velocity"] = max(summary["max_abs_angular_velocity"], *angular_velocity)
    if abs(roll) > roll_pitch_limit or abs(pitch) > roll_pitch_limit:
        raise RuntimeError(f"{label} abort: roll={roll:.4f}, pitch={pitch:.4f}")
    return roll, pitch


def target_deg_to_rad(target_deg: list[Any]) -> list[float]:
    return [math.radians(float(value)) for value in target_deg]


def max_abs_delta_deg(target_deg: list[Any], neutral_rad: list[float]) -> float:
    neutral_deg = [math.degrees(value) for value in neutral_rad]
    return max(abs(float(target_deg[i]) - neutral_deg[i]) for i in range(8))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=sorted(MODE_TO_REPORT), default="hybrid-1p0")
    parser.add_argument("--report", type=Path, default=None, help="Override the shadow report JSON for --mode.")
    parser.add_argument(
        "--vectors",
        type=Path,
        default=ROOT_DIR / "protocol/test_vectors/bittle_bringup_v0.json",
        help="Bring-up vectors containing the neutral target.",
    )
    parser.add_argument("--port", default=None, help="Serial port, e.g. /dev/ttyACM0.")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--rl-token", default="Y")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--period", type=float, default=0.2, help="Delay after each target before GET_STATE.")
    parser.add_argument(
        "--state-every",
        type=int,
        default=1,
        help="Read GET_STATE every N targets. Use 0 for start/end checks only.",
    )
    parser.add_argument("--sequence-id", type=int, default=1000)
    parser.add_argument("--roll-pitch-limit", type=float, default=0.25)
    parser.set_defaults(return_neutral=True)
    parser.add_argument("--return-neutral", dest="return_neutral", action="store_true")
    parser.add_argument("--no-return-neutral", dest="return_neutral", action="store_false")
    parser.add_argument("--allow-motion", action="store_true", help="Required before sending targets to --port.")
    parser.add_argument("--summary-only", action="store_true", help="Print only the run summary JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.rounds < 1:
        raise SystemExit("--rounds must be >= 1")
    if args.period < 0:
        raise SystemExit("--period must be >= 0")
    if args.state_every < 0:
        raise SystemExit("--state-every must be >= 0")
    if len(args.rl_token.encode("latin1")) != 1:
        raise SystemExit("--rl-token must encode to exactly one byte")

    report_path = args.report or MODE_TO_REPORT[args.mode]
    samples = load_shadow_targets(report_path)
    neutral_targets = load_neutral_targets(args.vectors)

    summary: dict[str, Any] = {
        "mode": args.mode,
        "report": str(report_path),
        "rounds_requested": args.rounds,
        "period": args.period,
        "state_every": args.state_every,
        "set_targets": 0,
        "states": 0,
        "max_abs_roll": 0.0,
        "max_abs_pitch": 0.0,
        "max_abs_angular_velocity": 0.0,
        "max_abs_delta_deg": max(max_abs_delta_deg(sample["target_deg"], neutral_targets) for sample in samples),
    }
    events: list[dict[str, Any]] = []

    if not args.port:
        dry_run = {
            "summary": summary,
            "samples": [
                {
                    "sample": int(sample.get("sample", index)),
                    "ref_index": sample.get("ref_index"),
                    "phase": sample.get("phase"),
                    "max_abs_delta_deg": max_abs_delta_deg(sample["target_deg"], neutral_targets),
                    "target_deg": sample["target_deg"],
                }
                for index, sample in enumerate(samples)
            ],
        }
        print(json.dumps(dry_run, indent=2))
        return

    if not args.allow_motion:
        raise SystemExit("--allow-motion is required before sending shadow targets to hardware.")

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
            response = serial_frame_to_json(
                send_serial_request(port, encode_set_targets_request(seq, neutral_targets), token)
            )
            require_status_flag(response, "command_accepted", "neutral_start")
            summary["set_targets"] += 1
            events.append({"event": "neutral_start", "sequence_id": seq})
            seq += 1
            time.sleep(args.period)

            state = serial_frame_to_json(send_serial_request(port, encode_get_state_request(seq), token))
            roll, pitch = check_state(state, "post_neutral_state", args.roll_pitch_limit, summary)
            events.append({"event": "post_neutral_state", "sequence_id": seq, "roll": roll, "pitch": pitch})
            seq += 1

            for round_index in range(args.rounds):
                for sample_index, sample in enumerate(samples):
                    target_deg = sample["target_deg"]
                    response = serial_frame_to_json(
                        send_serial_request(port, encode_set_targets_request(seq, target_deg_to_rad(target_deg)), token)
                    )
                    require_status_flag(response, "command_accepted", f"round_{round_index}_sample_{sample_index}")
                    summary["set_targets"] += 1
                    events.append(
                        {
                            "round": round_index + 1,
                            "sample": int(sample.get("sample", sample_index)),
                            "event": "set_target",
                            "sequence_id": seq,
                            "max_abs_delta_deg": round(max_abs_delta_deg(target_deg, neutral_targets), 3),
                        }
                    )
                    seq += 1
                    time.sleep(args.period)

                    target_count = round_index * len(samples) + sample_index + 1
                    if args.state_every and target_count % args.state_every == 0:
                        state = serial_frame_to_json(send_serial_request(port, encode_get_state_request(seq), token))
                        roll, pitch = check_state(
                            state,
                            f"round_{round_index}_sample_{sample_index}_state",
                            args.roll_pitch_limit,
                            summary,
                        )
                        events.append(
                            {
                                "round": round_index + 1,
                                "sample": int(sample.get("sample", sample_index)),
                                "event": "state",
                                "sequence_id": seq,
                                "roll": roll,
                                "pitch": pitch,
                            }
                        )
                        seq += 1

            if args.state_every == 0:
                state = serial_frame_to_json(send_serial_request(port, encode_get_state_request(seq), token))
                roll, pitch = check_state(state, "post_burst_state", args.roll_pitch_limit, summary)
                events.append({"event": "post_burst_state", "sequence_id": seq, "roll": roll, "pitch": pitch})
                seq += 1
        finally:
            if args.return_neutral:
                response = serial_frame_to_json(
                    send_serial_request(port, encode_set_targets_request(seq, neutral_targets), token)
                )
                require_status_flag(response, "command_accepted", "neutral_end")
                summary["set_targets"] += 1
                events.append({"event": "neutral_end", "sequence_id": seq})

    output = {"summary": summary}
    if not args.summary_only:
        output["events"] = events
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
