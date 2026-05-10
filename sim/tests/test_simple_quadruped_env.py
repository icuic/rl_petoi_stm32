import json
from pathlib import Path

import numpy as np

from sim.envs import (
    ACTION_DIM,
    ACTION_LAYOUT,
    ACTION_SCALE_RAD,
    JOINT_NAMES,
    NEUTRAL_POSE_RAD,
    OBSERVATION_DIM,
    OBSERVATION_LAYOUT,
    SimpleQuadrupedEnv,
    normalized_action_to_joint_targets,
)
from sim.envs.gait_reference import DEFAULT_PETOI_STAND_POSE, trot_reference


def test_random_actions_run_without_nan():
    env = SimpleQuadrupedEnv()
    obs, info = env.reset(seed=7)

    assert obs.shape == env.observation_space.shape
    assert np.isfinite(obs).all()
    assert 0.0 <= info["phase"] < 1.0

    for _ in range(300):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        assert obs.shape == env.observation_space.shape
        assert np.isfinite(obs).all()
        assert np.isfinite(reward)
        assert 0.0 <= info["phase"] < 1.0
        assert info["termination_reason"] in {
            "healthy",
            "torso_too_low",
            "torso_too_high",
            "roll_too_large",
            "pitch_too_large",
            "timeout",
        }
        assert np.isfinite(info["torso_height"])
        assert np.isfinite(info["roll"])
        assert np.isfinite(info["pitch"])
        assert "reward_terms" in info
        assert all(np.isfinite(value) for value in info["reward_terms"].values())
        if terminated or truncated:
            obs, info = env.reset()

    env.close()


def test_control_interface_layout_matches_environment():
    env = SimpleQuadrupedEnv()

    assert env.observation_space.shape == (OBSERVATION_DIM,)
    assert env.action_space.shape == (ACTION_DIM,)
    assert len(JOINT_NAMES) == ACTION_DIM
    assert len(ACTION_LAYOUT) == ACTION_DIM
    assert OBSERVATION_LAYOUT[-1] == ("phase_sin_cos", 27, 29)
    assert NEUTRAL_POSE_RAD.shape == (ACTION_DIM,)
    assert ACTION_SCALE_RAD.shape == (ACTION_DIM,)

    zero_action = np.zeros(ACTION_DIM, dtype=np.float32)
    np.testing.assert_allclose(normalized_action_to_joint_targets(zero_action), NEUTRAL_POSE_RAD)

    saturated_action = np.ones(ACTION_DIM, dtype=np.float32) * 2.0
    np.testing.assert_allclose(
        normalized_action_to_joint_targets(saturated_action),
        NEUTRAL_POSE_RAD + ACTION_SCALE_RAD,
    )

    env.close()


def test_control_interface_v0_test_vector():
    vector_path = Path("protocol/test_vectors/control_interface_v0.json")
    with vector_path.open("r", encoding="utf-8") as f:
        vector = json.load(f)

    assert vector["interface_version"] == "control_interface_v0"
    assert len(vector["observation"]) == OBSERVATION_DIM
    assert len(vector["normalized_action"]) == ACTION_DIM
    assert len(vector["expected_joint_target_rad"]) == ACTION_DIM

    action = np.asarray(vector["normalized_action"], dtype=np.float32)
    expected = np.asarray(vector["expected_joint_target_rad"], dtype=np.float32)
    np.testing.assert_allclose(normalized_action_to_joint_targets(action), expected)


def test_supported_robot_models_load_and_step():
    model_paths = [
        "sim/robots/simple_quadruped.xml",
        "sim/robots/bittle_like_v0.xml",
        "sim/robots/bittle_like_v1_visual.xml",
    ]

    for model_path in model_paths:
        env = SimpleQuadrupedEnv(model_path=model_path)
        obs, _ = env.reset(seed=7)
        assert obs.shape == (OBSERVATION_DIM,)

        action = np.zeros(ACTION_DIM, dtype=np.float32)
        obs, reward, terminated, truncated, info = env.step(action)
        assert obs.shape == (OBSERVATION_DIM,)
        assert np.isfinite(obs).all()
        assert np.isfinite(reward)
        assert not truncated
        assert info["termination_reason"] in {
            "healthy",
            "torso_too_low",
            "torso_too_high",
            "roll_too_large",
            "pitch_too_large",
        }
        env.close()


def test_trot_reference_is_finite_and_periodic():
    phase_0 = trot_reference(
        0.0,
        stand_pose=DEFAULT_PETOI_STAND_POSE,
        shoulder_amplitude=0.08,
        knee_amplitude=0.12,
    )
    phase_half = trot_reference(
        0.5,
        stand_pose=DEFAULT_PETOI_STAND_POSE,
        shoulder_amplitude=0.08,
        knee_amplitude=0.12,
    )
    phase_wrap = trot_reference(
        1.0,
        stand_pose=DEFAULT_PETOI_STAND_POSE,
        shoulder_amplitude=0.08,
        knee_amplitude=0.12,
    )

    assert phase_0.shape == (ACTION_DIM,)
    assert np.isfinite(phase_0).all()
    np.testing.assert_allclose(phase_0, phase_wrap, atol=1e-6)
    assert not np.allclose(phase_0, phase_half)


def test_residual_trot_control_mode_steps_with_reference_targets():
    env = SimpleQuadrupedEnv(
        model_path="sim/robots/bittle_like_v0.xml",
        control_config={
            "mode": "residual_trot",
            "neutral_pose": [0.2, 1.0, 0.2, 1.0, 0.2, 1.0, 0.2, 1.0],
            "action_scale": [0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05],
            "gait": {
                "period_steps": 120,
                "shoulder_amplitude": 0.08,
                "knee_amplitude": 0.12,
            },
        },
        reset_config={"joint_noise": 0.0, "velocity_noise": 0.0},
    )

    obs, info = env.reset(seed=7)
    assert obs.shape == (OBSERVATION_DIM,)
    assert info["control_mode"] == "residual_trot"
    np.testing.assert_allclose(obs[11:19], env._reference_joint_targets(0.0), atol=1e-6)

    obs, reward, terminated, truncated, info = env.step(np.zeros(ACTION_DIM, dtype=np.float32))
    assert obs.shape == (OBSERVATION_DIM,)
    assert np.isfinite(obs).all()
    assert np.isfinite(reward)
    assert not truncated
    assert info["control_mode"] == "residual_trot"
    assert np.isclose(info["phase"], 1.0 / 120.0)

    env.close()


def test_reset_and_reward_config_are_applied():
    env = SimpleQuadrupedEnv(
        model_path="sim/robots/bittle_like_v0.xml",
        reset_config={"torso_height": 0.19, "joint_noise": 0.0, "velocity_noise": 0.0},
        reward_config={
            "forward": 0.0,
            "target_height": 0.18,
            "xy_velocity": 0.08,
            "vertical_velocity": 0.08,
            "joint_position": 0.02,
            "drift": 0.1,
        },
    )

    obs, _ = env.reset(seed=7)
    assert obs.shape == (OBSERVATION_DIM,)
    assert np.isclose(float(obs[0]), 0.19)
    np.testing.assert_allclose(obs[11:19], NEUTRAL_POSE_RAD, atol=1e-6)

    obs, reward, terminated, truncated, info = env.step(np.zeros(ACTION_DIM, dtype=np.float32))
    assert obs.shape == (OBSERVATION_DIM,)
    assert np.isfinite(reward)
    assert not truncated
    assert "xy_velocity_penalty" in info["reward_terms"]
    assert "joint_position_penalty" in info["reward_terms"]
    assert "drift_penalty" in info["reward_terms"]

    env.close()
