#!/usr/bin/env python3
"""Binary codec and host-side probe helpers for RL serial protocol v0."""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

MAGIC = b"RL"
VERSION = 0

MSG_GET_STATE_REQ = 0x01
MSG_SET_TARGETS_REQ = 0x02
MSG_STEP_REQ = 0x03
MSG_GET_STATE_RESP = 0x81
MSG_SET_TARGETS_RESP = 0x82
MSG_STEP_RESP = 0x83

HEADER_STRUCT = struct.Struct("<2sBBHH")
CRC_STRUCT = struct.Struct("<H")
FLOAT13_STRUCT = struct.Struct("<13f")
FLOAT8_STRUCT = struct.Struct("<8f")
STATUS_STRUCT = struct.Struct("<H")

STATE_FLOAT_COUNT = 13
TARGET_FLOAT_COUNT = 8

STATUS_TELEMETRY_VALID = 1 << 0
STATUS_FEEDBACK_VALID = 1 << 1
STATUS_COMMAND_ACCEPTED = 1 << 2
STATUS_INTERNAL_FAULT = 1 << 3


@dataclass(frozen=True)
class TelemetryState:
    roll: float
    pitch: float
    angular_velocity_x: float
    angular_velocity_y: float
    angular_velocity_z: float
    joint_feedback: tuple[float, float, float, float, float, float, float, float]

    def floats(self) -> tuple[float, ...]:
        return (
            self.roll,
            self.pitch,
            self.angular_velocity_x,
            self.angular_velocity_y,
            self.angular_velocity_z,
            *self.joint_feedback,
        )

    @classmethod
    def from_floats(cls, values: Iterable[float]) -> "TelemetryState":
        numbers = tuple(float(value) for value in values)
        if len(numbers) != STATE_FLOAT_COUNT:
            raise ValueError(f"expected {STATE_FLOAT_COUNT} telemetry floats, got {len(numbers)}")
        return cls(
            roll=numbers[0],
            pitch=numbers[1],
            angular_velocity_x=numbers[2],
            angular_velocity_y=numbers[3],
            angular_velocity_z=numbers[4],
            joint_feedback=numbers[5:13],
        )


@dataclass(frozen=True)
class DecodedFrame:
    message_type: int
    sequence_id: int
    payload: bytes


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    crc = initial
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def encode_frame(message_type: int, sequence_id: int, payload: bytes = b"") -> bytes:
    if not 0 <= message_type <= 0xFF:
        raise ValueError("message_type must fit uint8")
    if not 0 <= sequence_id <= 0xFFFF:
        raise ValueError("sequence_id must fit uint16")
    if len(payload) > 0xFFFF:
        raise ValueError("payload is too large for uint16 length")

    header = HEADER_STRUCT.pack(MAGIC, VERSION, message_type, sequence_id, len(payload))
    checksum = CRC_STRUCT.pack(crc16_ccitt(header + payload))
    return header + payload + checksum


def decode_frame(frame: bytes) -> DecodedFrame:
    if len(frame) < HEADER_STRUCT.size + CRC_STRUCT.size:
        raise ValueError("frame is too short")

    header = frame[: HEADER_STRUCT.size]
    magic, version, message_type, sequence_id, payload_len = HEADER_STRUCT.unpack(header)
    if magic != MAGIC:
        raise ValueError(f"unexpected magic: {magic!r}")
    if version != VERSION:
        raise ValueError(f"unsupported version: {version}")

    expected_len = HEADER_STRUCT.size + payload_len + CRC_STRUCT.size
    if len(frame) != expected_len:
        raise ValueError(f"frame length mismatch: expected {expected_len}, got {len(frame)}")

    payload_start = HEADER_STRUCT.size
    payload_end = payload_start + payload_len
    payload = frame[payload_start:payload_end]
    checksum = CRC_STRUCT.unpack(frame[payload_end:])[0]
    expected_checksum = crc16_ccitt(header + payload)
    if checksum != expected_checksum:
        raise ValueError(f"crc mismatch: expected 0x{expected_checksum:04x}, got 0x{checksum:04x}")

    return DecodedFrame(message_type=message_type, sequence_id=sequence_id, payload=payload)


def encode_get_state_request(sequence_id: int) -> bytes:
    return encode_frame(MSG_GET_STATE_REQ, sequence_id)


def encode_set_targets_request(sequence_id: int, joint_target: Iterable[float]) -> bytes:
    target = _pack_float_tuple(joint_target, TARGET_FLOAT_COUNT, "joint_target")
    return encode_frame(MSG_SET_TARGETS_REQ, sequence_id, FLOAT8_STRUCT.pack(*target))


def encode_step_request(sequence_id: int, joint_target: Iterable[float]) -> bytes:
    target = _pack_float_tuple(joint_target, TARGET_FLOAT_COUNT, "joint_target")
    return encode_frame(MSG_STEP_REQ, sequence_id, FLOAT8_STRUCT.pack(*target))


def encode_state_response(message_type: int, sequence_id: int, status: int, state: TelemetryState) -> bytes:
    if message_type not in {MSG_GET_STATE_RESP, MSG_STEP_RESP}:
        raise ValueError("state response message_type must be GET_STATE_RESP or STEP_RESP")
    payload = STATUS_STRUCT.pack(_validate_status(status)) + FLOAT13_STRUCT.pack(*state.floats())
    return encode_frame(message_type, sequence_id, payload)


def encode_set_targets_response(sequence_id: int, status: int) -> bytes:
    return encode_frame(MSG_SET_TARGETS_RESP, sequence_id, STATUS_STRUCT.pack(_validate_status(status)))


def decode_joint_target_payload(payload: bytes) -> tuple[float, ...]:
    if len(payload) != FLOAT8_STRUCT.size:
        raise ValueError(f"joint target payload length mismatch: expected {FLOAT8_STRUCT.size}, got {len(payload)}")
    return tuple(float(value) for value in FLOAT8_STRUCT.unpack(payload))


def decode_status_payload(payload: bytes) -> int:
    if len(payload) != STATUS_STRUCT.size:
        raise ValueError(f"status payload length mismatch: expected {STATUS_STRUCT.size}, got {len(payload)}")
    return STATUS_STRUCT.unpack(payload)[0]


def decode_state_payload(payload: bytes) -> tuple[int, TelemetryState]:
    expected = STATUS_STRUCT.size + FLOAT13_STRUCT.size
    if len(payload) != expected:
        raise ValueError(f"state payload length mismatch: expected {expected}, got {len(payload)}")
    status = STATUS_STRUCT.unpack(payload[: STATUS_STRUCT.size])[0]
    state = TelemetryState.from_floats(FLOAT13_STRUCT.unpack(payload[STATUS_STRUCT.size :]))
    return status, state


def _pack_float_tuple(values: Iterable[float], expected_len: int, label: str) -> tuple[float, ...]:
    numbers = tuple(float(value) for value in values)
    if len(numbers) != expected_len:
        raise ValueError(f"{label} must contain {expected_len} floats, got {len(numbers)}")
    return numbers


def _validate_status(status: int) -> int:
    if not 0 <= int(status) <= 0xFFFF:
        raise ValueError("status must fit uint16")
    return int(status)


def example_vectors() -> dict[str, object]:
    state = TelemetryState(
        roll=0.05,
        pitch=-0.03,
        angular_velocity_x=0.11,
        angular_velocity_y=-0.12,
        angular_velocity_z=0.13,
        joint_feedback=(0.2, 1.4, 0.21, 1.39, 0.19, 1.41, 0.18, 1.42),
    )
    targets = (0.22, 1.38, 0.24, 1.36, 0.18, 1.42, 0.16, 1.44)
    status = STATUS_TELEMETRY_VALID | STATUS_FEEDBACK_VALID | STATUS_COMMAND_ACCEPTED

    frames = {
        "get_state_request": encode_get_state_request(7),
        "set_targets_request": encode_set_targets_request(8, targets),
        "set_targets_response": encode_set_targets_response(8, status),
        "step_request": encode_step_request(9, targets),
        "step_response": encode_state_response(MSG_STEP_RESP, 9, status, state),
    }
    return {
        "wire_version": VERSION,
        "target_joint_rad": list(targets),
        "telemetry_state": asdict(state),
        "status": status,
        "frames_hex": {name: frame.hex() for name, frame in frames.items()},
    }


def run_self_test() -> dict[str, object]:
    vectors = example_vectors()
    frames = vectors["frames_hex"]

    step_req = decode_frame(bytes.fromhex(frames["step_request"]))
    if step_req.message_type != MSG_STEP_REQ or step_req.sequence_id != 9:
        raise AssertionError("step request metadata mismatch")
    decoded_targets = decode_joint_target_payload(step_req.payload)

    step_resp = decode_frame(bytes.fromhex(frames["step_response"]))
    if step_resp.message_type != MSG_STEP_RESP or step_resp.sequence_id != 9:
        raise AssertionError("step response metadata mismatch")
    decoded_status, decoded_state = decode_state_payload(step_resp.payload)

    return {
        "step_request_targets": decoded_targets,
        "step_response_status": decoded_status,
        "step_response_state": asdict(decoded_state),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="Encode and decode reference frames.")
    parser.add_argument("--write-vectors", type=Path, default=None, help="Write JSON protocol vectors to this path.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.write_vectors:
        args.write_vectors.parent.mkdir(parents=True, exist_ok=True)
        with args.write_vectors.open("w", encoding="utf-8") as f:
            json.dump(example_vectors(), f, indent=2)
            f.write("\n")
        print(f"Saved RL serial protocol vectors to {args.write_vectors}")

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2))

    if not args.write_vectors and not args.self_test:
        print(json.dumps(example_vectors(), indent=2))


if __name__ == "__main__":
    main()
