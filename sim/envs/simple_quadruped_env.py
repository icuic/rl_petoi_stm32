"""Minimal MuJoCo quadruped environment for interface bring-up."""

from __future__ import annotations

from pathlib import Path

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces

from sim.envs.gait_reference import trot_reference
from sim.envs.simple_quadruped_interface import (
    ACTION_DIM,
    ACTION_SCALE_RAD,
    DEPLOYABLE_OBSERVATION_DIM,
    FULL_OBSERVATION_DIM,
    JOINT_NAMES,
    NEUTRAL_POSE_RAD,
)


FOOT_CONTACT_GEOMS = {
    "right_front": "shank_rf_1_collision_0",
    "right_rear": "shank_rr_1_collision_0",
    "left_front": "shank_lf_1_collision_0",
    "left_rear": "shank_lr_1_collision_0",
}
REAR_LEGS = ("right_rear", "left_rear")
FRONT_LEGS = ("right_front", "left_front")


class SimpleQuadrupedEnv(gym.Env):
    """A small 8-DoF quadruped controlled by normalized joint targets."""

    metadata = {"render_modes": ["rgb_array"], "render_fps": 50}

    def __init__(
        self,
        model_path: str | Path | None = None,
        frame_skip: int = 10,
        episode_steps: int = 1000,
        reward_config: dict[str, float] | None = None,
        reset_config: dict[str, float] | None = None,
        control_config: dict | None = None,
        observation_config: dict | None = None,
        render_mode: str | None = None,
    ) -> None:
        super().__init__()
        if render_mode not in (None, "rgb_array"):
            raise ValueError(f"Unsupported render_mode: {render_mode}")

        root_dir = Path(__file__).resolve().parents[2]
        self.model_path = Path(model_path) if model_path else root_dir / "sim" / "robots" / "simple_quadruped.xml"
        self.model = mujoco.MjModel.from_xml_path(str(self.model_path))
        self.data = mujoco.MjData(self.model)

        self.frame_skip = frame_skip
        self.episode_steps = episode_steps
        self.render_mode = render_mode
        self.step_count = 0
        self.phase = 0.0
        self.previous_x_position = 0.0
        self._renderer: mujoco.Renderer | None = None
        self.previous_action = np.zeros(8, dtype=np.float32)
        self.previous_foot_xy = np.zeros((len(FOOT_CONTACT_GEOMS), 2), dtype=np.float64)
        self.foot_geom_ids = self._resolve_optional_geom_ids(FOOT_CONTACT_GEOMS.values())
        self.floor_geom_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, "floor")
        self.reset_config = {
            "torso_height": 0.22,
            "joint_noise": 0.02,
            "velocity_noise": 0.01,
            "min_torso_height": 0.08,
            "max_torso_height": 0.45,
            "max_roll": 1.2,
            "max_pitch": 1.2,
        }
        if reset_config:
            self.reset_config.update({key: float(value) for key, value in reset_config.items()})
        self.reward_config = {
            "survival": 0.1,
            "forward": 1.0,
            "progress": 0.0,
            "upright": 0.2,
            "target_height": 0.22,
            "height": 0.5,
            "roll": 0.15,
            "pitch": 0.05,
            "xy_velocity": 0.0,
            "lateral_velocity": 0.0,
            "vertical_velocity": 0.0,
            "angular_velocity": 0.005,
            "joint_velocity": 0.0005,
            "joint_position": 0.0,
            "action": 0.002,
            "action_delta": 0.001,
            "drift": 0.0,
            "fall": 0.2,
            "contact_slip": 0.0,
            "rear_contact_slip": 0.0,
            "front_contact_duty": 0.0,
            "rear_contact_bonus": 0.0,
        }
        if reward_config:
            self.reward_config.update({key: float(value) for key, value in reward_config.items()})

        observation_config = observation_config or {}
        self.observation_mode = str(observation_config.get("mode", "full_state"))
        if self.observation_mode not in {"full_state", "deployable_v0"}:
            raise ValueError(f"Unsupported observation mode: {self.observation_mode}")
        observation_dim = FULL_OBSERVATION_DIM if self.observation_mode == "full_state" else DEPLOYABLE_OBSERVATION_DIM

        control_config = control_config or {}
        self.control_mode = str(control_config.get("mode", "absolute"))
        if self.control_mode not in {"absolute", "residual_trot"}:
            raise ValueError(f"Unsupported control mode: {self.control_mode}")

        gait_config = control_config.get("gait", {})
        default_gait_period_steps = 50 if self.control_mode == "absolute" else 120
        self.gait_period_steps = int(gait_config.get("period_steps", default_gait_period_steps))
        if self.gait_period_steps <= 0:
            raise ValueError("gait.period_steps must be positive")
        self.gait_shoulder_amplitude = float(gait_config.get("shoulder_amplitude", 0.08))
        self.gait_knee_amplitude = float(gait_config.get("knee_amplitude", 0.12))
        self.gait_duty_bias = float(gait_config.get("duty_bias", 0.0))

        self.joint_names = tuple(control_config.get("joint_names", JOINT_NAMES))
        self.actuator_names = tuple(control_config.get("actuator_names", ()))
        self.neutral_pose = np.asarray(control_config.get("neutral_pose", NEUTRAL_POSE_RAD), dtype=np.float32)
        self.action_scale = np.asarray(control_config.get("action_scale", ACTION_SCALE_RAD), dtype=np.float32)
        if len(self.joint_names) != ACTION_DIM:
            raise ValueError(f"Expected {ACTION_DIM} controlled joints, got {len(self.joint_names)}")
        if self.neutral_pose.shape != (ACTION_DIM,):
            raise ValueError(f"neutral_pose must have shape ({ACTION_DIM},), got {self.neutral_pose.shape}")
        if self.action_scale.shape != (ACTION_DIM,):
            raise ValueError(f"action_scale must have shape ({ACTION_DIM},), got {self.action_scale.shape}")

        if control_config.get("joint_names"):
            self.joint_qpos_addr, self.joint_qvel_addr = self._resolve_joint_addresses(self.joint_names)
        else:
            self.joint_qpos_addr = np.arange(7, 15)
            self.joint_qvel_addr = np.arange(6, 14)

        if self.actuator_names:
            self.actuator_ctrl_addr = self._resolve_actuator_addresses(self.actuator_names)
        else:
            self.actuator_ctrl_addr = np.arange(ACTION_DIM)

        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(ACTION_DIM,), dtype=np.float32)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(observation_dim,), dtype=np.float32)

    def reset(self, *, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        mujoco.mj_resetData(self.model, self.data)
        self.step_count = 0
        self.phase = 0.0
        self.previous_x_position = 0.0
        self.previous_action = np.zeros(8, dtype=np.float32)

        joint_noise = float(self.reset_config["joint_noise"])
        velocity_noise = float(self.reset_config["velocity_noise"])

        self.data.qpos[:7] = np.array([0.0, 0.0, self.reset_config["torso_height"], 1.0, 0.0, 0.0, 0.0])
        reset_pose = self._reference_joint_targets(self.phase)
        self.data.qpos[self.joint_qpos_addr] = reset_pose
        self.data.qpos[self.joint_qpos_addr] += self.np_random.uniform(-joint_noise, joint_noise, size=8)
        self.data.qvel[:] = self.np_random.uniform(-velocity_noise, velocity_noise, size=self.model.nv)
        self.data.ctrl[self.actuator_ctrl_addr] = reset_pose
        mujoco.mj_forward(self.model, self.data)
        self.previous_x_position = float(self.data.qpos[0])
        self.previous_foot_xy = self._foot_xy_positions()

        return self._get_obs(), {"phase": self.phase, "control_mode": self.control_mode, "observation_mode": self.observation_mode}

    def step(self, action):
        action = np.asarray(action, dtype=np.float32)
        action = np.clip(action, self.action_space.low, self.action_space.high)

        target = self._normalized_action_to_joint_targets(action)
        previous_x_position = float(self.data.qpos[0])
        self.data.ctrl[self.actuator_ctrl_addr] = target
        mujoco.mj_step(self.model, self.data, nstep=self.frame_skip)
        x_position = float(self.data.qpos[0])
        x_progress = x_position - previous_x_position
        foot_quality = self._get_foot_quality_terms()

        self.step_count += 1
        phase_delta = self.frame_skip / self.gait_period_steps if self.control_mode == "residual_trot" else 1.0 / self.gait_period_steps
        self.phase = (self.phase + phase_delta) % 1.0

        health = self._get_health()
        termination_reason = health["termination_reason"]
        terminated = termination_reason != "healthy"
        truncated = self.step_count >= self.episode_steps
        if truncated and not terminated:
            termination_reason = "timeout"
        reward, reward_terms = self._get_reward(
            action=action,
            health=health,
            terminated=terminated,
            x_progress=x_progress,
            foot_quality=foot_quality,
        )
        self.previous_action = action.copy()
        self.previous_x_position = x_position
        self.previous_foot_xy = self._foot_xy_positions()
        obs = self._get_obs()
        info = {
            "x_position": x_position,
            "x_velocity": float(self.data.qvel[0]),
            "x_progress": x_progress,
            "phase": self.phase,
            "torso_height": health["height"],
            "roll": health["roll"],
            "pitch": health["pitch"],
            "control_mode": self.control_mode,
            "observation_mode": self.observation_mode,
            "termination_reason": termination_reason,
            "reward_terms": reward_terms,
            "foot_quality": foot_quality,
        }
        return obs, reward, terminated, truncated, info

    def render(self):
        if self.render_mode != "rgb_array":
            return None
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self.model, width=640, height=480)
        self._renderer.update_scene(self.data)
        return self._renderer.render()

    def close(self) -> None:
        if self._renderer is not None:
            self._renderer.close()
            self._renderer = None

    def _get_obs(self) -> np.ndarray:
        phase_angle = 2.0 * np.pi * self.phase
        if self.observation_mode == "deployable_v0":
            roll, pitch = _quat_to_roll_pitch(self.data.qpos[3:7])
            obs = np.concatenate(
                [
                    np.array([roll, pitch], dtype=np.float32),
                    self.data.qvel[3:6],
                    self.data.qpos[self.joint_qpos_addr],
                    self.previous_action,
                    np.array([np.sin(phase_angle), np.cos(phase_angle)]),
                ]
            )
            return obs.astype(np.float32)

        obs = np.concatenate(
            [
                self.data.qpos[2:3],
                self.data.qpos[3:7],
                self.data.qvel[0:6],
                self.data.qpos[self.joint_qpos_addr],
                self.data.qvel[self.joint_qvel_addr],
                np.array([np.sin(phase_angle), np.cos(phase_angle)]),
            ]
        )
        return obs.astype(np.float32)

    def _normalized_action_to_joint_targets(self, action: np.ndarray) -> np.ndarray:
        clipped_action = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
        reference = self._reference_joint_targets(self.phase)
        return reference + clipped_action * self.action_scale

    def _reference_joint_targets(self, phase: float) -> np.ndarray:
        if self.control_mode == "residual_trot":
            return trot_reference(
                float(phase),
                stand_pose=self.neutral_pose,
                shoulder_amplitude=self.gait_shoulder_amplitude,
                knee_amplitude=self.gait_knee_amplitude,
                duty_bias=self.gait_duty_bias,
            )
        return self.neutral_pose

    def _get_reward(
        self,
        action: np.ndarray,
        health: dict[str, float | str],
        terminated: bool,
        x_progress: float,
        foot_quality: dict[str, float],
    ) -> tuple[float, dict[str, float]]:
        weights = self.reward_config
        roll = float(health["roll"])
        pitch = float(health["pitch"])
        action_delta = action - self.previous_action
        reference = self._reference_joint_targets(self.phase)

        terms = {
            "survival": weights["survival"],
            "forward": weights["forward"] * float(self.data.qvel[0]),
            "progress": weights["progress"] * float(x_progress),
            "upright": weights["upright"] * float(self.data.qpos[3]),
            "height_penalty": weights["height"] * abs(float(health["height"]) - weights["target_height"]),
            "roll_penalty": weights["roll"] * roll * roll,
            "pitch_penalty": weights["pitch"] * pitch * pitch,
            "xy_velocity_penalty": weights["xy_velocity"] * float(np.square(self.data.qvel[0:2]).sum()),
            "lateral_velocity_penalty": weights["lateral_velocity"] * float(self.data.qvel[1] * self.data.qvel[1]),
            "vertical_velocity_penalty": weights["vertical_velocity"] * float(self.data.qvel[2] * self.data.qvel[2]),
            "angular_velocity_penalty": weights["angular_velocity"] * float(np.square(self.data.qvel[3:6]).sum()),
            "joint_velocity_penalty": weights["joint_velocity"] * float(np.square(self.data.qvel[self.joint_qvel_addr]).sum()),
            "joint_position_penalty": weights["joint_position"] * float(np.square(self.data.qpos[self.joint_qpos_addr] - reference).sum()),
            "action_penalty": weights["action"] * float(np.square(action).sum()),
            "action_delta_penalty": weights["action_delta"] * float(np.square(action_delta).sum()),
            "drift_penalty": weights["drift"] * float(self.data.qpos[1] * self.data.qpos[1]),
            "fall_penalty": weights["fall"] if terminated else 0.0,
            "contact_slip_penalty": weights["contact_slip"] * foot_quality["contact_slip_speed_sum"],
            "rear_contact_slip_penalty": weights["rear_contact_slip"] * foot_quality["rear_contact_slip_speed_sum"],
            "front_contact_duty_penalty": weights["front_contact_duty"] * foot_quality["front_contact_count"],
            "rear_contact_bonus": weights["rear_contact_bonus"] * foot_quality["rear_contact_count"],
        }
        reward = (
            terms["survival"]
            + terms["forward"]
            + terms["progress"]
            + terms["upright"]
            - terms["height_penalty"]
            - terms["roll_penalty"]
            - terms["pitch_penalty"]
            - terms["xy_velocity_penalty"]
            - terms["lateral_velocity_penalty"]
            - terms["vertical_velocity_penalty"]
            - terms["angular_velocity_penalty"]
            - terms["joint_velocity_penalty"]
            - terms["joint_position_penalty"]
            - terms["action_penalty"]
            - terms["action_delta_penalty"]
            - terms["drift_penalty"]
            - terms["fall_penalty"]
            - terms["contact_slip_penalty"]
            - terms["rear_contact_slip_penalty"]
            - terms["front_contact_duty_penalty"]
            + terms["rear_contact_bonus"]
        )
        return float(reward), terms

    def _get_foot_quality_terms(self) -> dict[str, float]:
        if self.floor_geom_id < 0 or any(geom_id < 0 for geom_id in self.foot_geom_ids):
            return {
                "contact_slip_speed_sum": 0.0,
                "rear_contact_slip_speed_sum": 0.0,
                "front_contact_count": 0.0,
                "rear_contact_count": 0.0,
            }

        contacts = self._foot_contacts()
        foot_xy = self._foot_xy_positions()
        dt = float(self.model.opt.timestep * self.frame_skip)
        foot_xy_speed = np.linalg.norm(foot_xy - self.previous_foot_xy, axis=1) / dt
        contact_slip_speed = foot_xy_speed * contacts
        leg_names = tuple(FOOT_CONTACT_GEOMS)
        rear_indices = [leg_names.index(leg) for leg in REAR_LEGS]
        front_indices = [leg_names.index(leg) for leg in FRONT_LEGS]
        return {
            "contact_slip_speed_sum": float(np.sum(contact_slip_speed)),
            "rear_contact_slip_speed_sum": float(np.sum(contact_slip_speed[rear_indices])),
            "front_contact_count": float(np.sum(contacts[front_indices])),
            "rear_contact_count": float(np.sum(contacts[rear_indices])),
        }

    def _foot_contacts(self) -> np.ndarray:
        contacts = np.zeros(len(self.foot_geom_ids), dtype=np.float64)
        for contact_idx in range(self.data.ncon):
            contact = self.data.contact[contact_idx]
            pair = {int(contact.geom1), int(contact.geom2)}
            if self.floor_geom_id not in pair:
                continue
            for idx, geom_id in enumerate(self.foot_geom_ids):
                if geom_id in pair:
                    contacts[idx] = 1.0
        return contacts

    def _foot_xy_positions(self) -> np.ndarray:
        positions = np.zeros((len(self.foot_geom_ids), 2), dtype=np.float64)
        for idx, geom_id in enumerate(self.foot_geom_ids):
            if geom_id >= 0:
                positions[idx] = self.data.geom_xpos[geom_id, :2]
        return positions

    def _get_health(self) -> dict[str, float | str]:
        height = float(self.data.qpos[2])
        quat = self.data.qpos[3:7]
        roll, pitch = _quat_to_roll_pitch(quat)

        if height < self.reset_config["min_torso_height"]:
            termination_reason = "torso_too_low"
        elif height > self.reset_config["max_torso_height"]:
            termination_reason = "torso_too_high"
        elif abs(roll) > self.reset_config["max_roll"]:
            termination_reason = "roll_too_large"
        elif abs(pitch) > self.reset_config["max_pitch"]:
            termination_reason = "pitch_too_large"
        else:
            termination_reason = "healthy"

        return {
            "height": height,
            "roll": roll,
            "pitch": pitch,
            "termination_reason": termination_reason,
        }

    def _resolve_joint_addresses(self, joint_names: tuple[str, ...]) -> tuple[np.ndarray, np.ndarray]:
        qpos_addr = []
        qvel_addr = []
        for joint_name in joint_names:
            joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
            if joint_id < 0:
                raise ValueError(f"Joint not found in model {self.model_path}: {joint_name}")
            qpos_addr.append(int(self.model.jnt_qposadr[joint_id]))
            qvel_addr.append(int(self.model.jnt_dofadr[joint_id]))
        return np.asarray(qpos_addr, dtype=np.int32), np.asarray(qvel_addr, dtype=np.int32)

    def _resolve_actuator_addresses(self, actuator_names: tuple[str, ...]) -> np.ndarray:
        if len(actuator_names) != ACTION_DIM:
            raise ValueError(f"Expected {ACTION_DIM} actuators, got {len(actuator_names)}")
        actuator_ids = []
        for actuator_name in actuator_names:
            actuator_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator_name)
            if actuator_id < 0:
                raise ValueError(f"Actuator not found in model {self.model_path}: {actuator_name}")
            actuator_ids.append(int(actuator_id))
        return np.asarray(actuator_ids, dtype=np.int32)

    def _resolve_optional_geom_ids(self, geom_names) -> np.ndarray:
        geom_ids = []
        for geom_name in geom_names:
            geom_ids.append(int(mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, str(geom_name))))
        return np.asarray(geom_ids, dtype=np.int32)


def _quat_to_roll_pitch(quat: np.ndarray) -> tuple[float, float]:
    w, x, y, z = quat
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (w * y - z * x)
    pitch = np.arcsin(np.clip(sinp, -1.0, 1.0))
    return float(roll), float(pitch)
