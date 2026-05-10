# Petoi model sources

Petoi model assets are fetched on demand rather than committed directly.

Run from the repository root:

```bash
bash scripts/fetch_petoi_model.sh
```

The script fetches the official Petoi ROS Bittle description into:

```text
third_party/petoi/ros_opencat/petoi_ROS_model_docs/bittle_ros/bittle_description
```

Expected contents include:

- `urdf/bittle.xacro`
- `urdf/bittle.gazebo`
- `urdf/bittle.trans`
- `meshes/*.stl`

Before using these files in generated MJCF models or redistributed artifacts,
check the upstream license files in the fetched repository.
