"""Check whether an exported ONNX actor matches the STM32 deployable policy contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import onnx
from onnx import numpy_helper


EXPECTED_INPUT_DIM = 23
EXPECTED_OUTPUT_DIM = 8
SUPPORTED_OPS = {"Flatten", "Gemm", "Tanh", "Relu", "Clip", "Constant"}
SUPPORTED_ACTIVATIONS = {"Tanh", "Relu"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "onnx_model",
        type=Path,
        nargs="?",
        default=Path("models/onnx/petoi_bittle_v0_deployable_v0_best_actor.onnx"),
        help="Exported actor ONNX model.",
    )
    parser.add_argument("--expected-input-dim", type=int, default=EXPECTED_INPUT_DIM)
    parser.add_argument("--expected-output-dim", type=int, default=EXPECTED_OUTPUT_DIM)
    parser.add_argument("--report", type=Path, default=None, help="Optional JSON report path.")
    return parser.parse_args()


def tensor_shape(value_info: onnx.ValueInfoProto) -> list[int | str]:
    dims: list[int | str] = []
    for dim in value_info.type.tensor_type.shape.dim:
        dims.append(dim.dim_value if dim.dim_value else dim.dim_param)
    return dims


def trailing_dim(shape: list[int | str]) -> int | None:
    if not shape:
        return None
    value = shape[-1]
    return value if isinstance(value, int) else None


def check_model(path: Path, expected_input_dim: int, expected_output_dim: int) -> dict[str, Any]:
    model = onnx.load(path)
    onnx.checker.check_model(model)

    inputs = [(value.name, tensor_shape(value)) for value in model.graph.input]
    outputs = [(value.name, tensor_shape(value)) for value in model.graph.output]
    initializers = {init.name: numpy_helper.to_array(init) for init in model.graph.initializer}

    gemm_layers: list[dict[str, Any]] = []
    activations: list[str] = []
    unsupported_ops: list[str] = []
    for node in model.graph.node:
        if node.op_type not in SUPPORTED_OPS:
            unsupported_ops.append(node.op_type)
        if node.op_type in SUPPORTED_ACTIVATIONS:
            activations.append(node.op_type)
        if node.op_type == "Gemm":
            weight_name = node.input[1] if len(node.input) > 1 else ""
            bias_name = node.input[2] if len(node.input) > 2 else ""
            weight = initializers.get(weight_name)
            bias = initializers.get(bias_name)
            gemm_layers.append(
                {
                    "name": node.name,
                    "weight": weight_name,
                    "weight_shape": list(weight.shape) if weight is not None else None,
                    "bias": bias_name,
                    "bias_shape": list(bias.shape) if bias is not None else None,
                }
            )

    parameter_count = int(sum(array.size for array in initializers.values()))
    parameter_bytes_float32 = parameter_count * 4
    input_dim = trailing_dim(inputs[0][1]) if len(inputs) == 1 else None
    output_dim = trailing_dim(outputs[0][1]) if len(outputs) == 1 else None

    hidden_layers = [
        layer["weight_shape"][0]
        for layer in gemm_layers[:-1]
        if layer["weight_shape"] is not None and len(layer["weight_shape"]) == 2
    ]
    first_weight_shape = gemm_layers[0]["weight_shape"] if gemm_layers else None
    final_weight_shape = gemm_layers[-1]["weight_shape"] if gemm_layers else None
    checks = {
        "single_input": len(inputs) == 1,
        "single_output": len(outputs) == 1,
        "input_dim": input_dim == expected_input_dim,
        "output_dim": output_dim == expected_output_dim,
        "unsupported_ops": len(unsupported_ops) == 0,
        "has_gemm_layers": len(gemm_layers) >= 1,
        "first_gemm_input_dim": bool(first_weight_shape and first_weight_shape[-1] == expected_input_dim),
        "final_gemm_output_dim": bool(final_weight_shape and final_weight_shape[0] == expected_output_dim),
        "has_clip_output": bool(model.graph.node and model.graph.node[-1].op_type == "Clip"),
    }
    passed = all(checks.values())

    return {
        "onnx_model": str(path),
        "inputs": inputs,
        "outputs": outputs,
        "gemm_layers": gemm_layers,
        "hidden_layers": hidden_layers,
        "activations": activations,
        "ops": [node.op_type for node in model.graph.node],
        "unsupported_ops": unsupported_ops,
        "parameter_count": parameter_count,
        "parameter_bytes_float32": parameter_bytes_float32,
        "checks": checks,
        "passed": passed,
    }


def main() -> None:
    args = parse_args()
    report = check_model(args.onnx_model, args.expected_input_dim, args.expected_output_dim)
    print(json.dumps(report, indent=2))
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
            f.write("\n")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
