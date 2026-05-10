#!/usr/bin/env python3
"""Load a MuJoCo XML or URDF model and print basic model dimensions."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", type=Path)
    args = parser.parse_args()

    try:
        import mujoco
    except ImportError as exc:
        print(f"ERROR: mujoco is not installed: {exc}", file=sys.stderr)
        return 1

    try:
        model = mujoco.MjModel.from_xml_path(str(args.model))
    except Exception as exc:
        print(f"ERROR: failed to load {args.model}: {exc}", file=sys.stderr)
        return 1

    print(f"Loaded {args.model}")
    print(f"  nq     : {model.nq}")
    print(f"  nv     : {model.nv}")
    print(f"  nu     : {model.nu}")
    print(f"  nbody  : {model.nbody}")
    print(f"  njnt   : {model.njnt}")
    print(f"  ngeom  : {model.ngeom}")
    print(f"  nmesh  : {model.nmesh}")
    if model.njnt:
        joint_names = [
            mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, idx)
            for idx in range(model.njnt)
        ]
        print("  joints : " + ", ".join(name or f"<joint:{idx}>" for idx, name in enumerate(joint_names)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
