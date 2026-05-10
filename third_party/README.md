# Third-party assets

This directory is reserved for externally sourced robot descriptions, CAD files,
and mesh assets used to build higher-fidelity simulation models.

Large third-party assets should normally be fetched by script instead of being
committed directly. This keeps the repository small and makes each temporary
training server reproducible.

Current source:

- Petoi Bittle ROS description: `scripts/fetch_petoi_model.sh`
