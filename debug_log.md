# Khronos Docker — Debug Log

Records the issues encountered and fixes applied while setting up Khronos
(ROS2 Jazzy, Docker) on custom datasets (Gazebo Classic / Isaac Sim / real world).

## Environment

- Host: Ubuntu 22.04 + ROS2 Humble (recording only).
- Container: `osrf/ros:jazzy-desktop` (Ubuntu 24.04 + ROS2 Jazzy).
- Khronos + 11 source deps built with `colcon build --symlink-install -DCMAKE_BUILD_TYPE=Release`.
- GPU: NVIDIA RTX 4070 SUPER (12 GB) via nvidia-container-toolkit.

---

## Issue 1 — Open-set mapper config missing `type` fields

- **Symptom**: `khronos_node` aborts with:
  `Active window is not khronos::ActiveWindow!` and `Backend is not khronos::Backend!`.
- **Cause**: `khronos_ros/config/mapper/uHumans2_openset.yaml` (upstream bug) is missing:
  - `active_window.type: "ActiveWindow"`
  - `backend.type: "Backend"`
  - `backend.update_functors.khronos_objects.type: UpdateKhronosObjectsFunctor`
  (it had a broken `update_objects:` instead).
- **Fix**: added the three missing `type` fields.

## Issue 2 — Embed service name mismatch

- **Symptom**: `khronos_node` hung at:
  `Waiting for embedding encoder on '/semantic_inference/embed'`.
- **Cause**: `RosEmbeddingGroup` (C++, `ianvs`) resolves `embed` under `ns`
  (config `ns: /semantic_inference`), while `PromptEncoder` (Python) creates the
  service at `semantic/embed` relative to the open_set node → `/semantic_inference/semantic/embed`.
- **Fix**: changed mapper config `ns` from `/semantic_inference` to `/semantic_inference/semantic`.

## Issue 3 — Open-set node namespace mismatch

- **Symptom**: `khronos_node` still couldn't find the embed service / labels.
- **Cause**: `open_set_node` is Python (`rclpy`, default namespace `/`), but the
  C++ (`ianvs`) nodes use namespace `/semantic_inference`; the launch `set_remap
  from: semantic_inference/color/image_raw` assumed the `/semantic_inference` namespace.
- **Fix**: launched the open-set node with `namespace: semantic_inference` so its
  `semantic/...` topics/services land under `/semantic_inference/semantic/...`.

## Issue 4 — Open-set (FastSAM + CLIP) labels never produced

- **Symptom**: pipeline fully starts (`[Hydra Input/Active Window/Frontend] started!`,
  `Running...`), but no voxels/mesh are integrated — the time-synchronized input
  (color + depth + labels) never fires, so no map.
- **Cause**: the CLIP model forward pass times out:
  ```
  ros_embedding_group.cpp:80] Failed to get result for 'structure'
  ros_embedding_group.cpp:80] Failed to get result for 'wall'
  ros_embedding_group.cpp:80] Failed to get result for 'floor'
  ```
  The same CLIP model (ViT-L/14) drives the open-set label stream, so no
  `FeatureImage` labels are published → synchronizer starves.
- **Resolution**: switch to **closed-set (ADE20k / TensorRT)** segmentation
  (see Issue 5), which does not depend on CLIP.

## Issue 5 — Closed-set (ADE20k / TensorRT) setup

- **Done**: added CUDA keyring + TensorRT (`libnvinfer-dev libnvonnxparsers-dev
  libnvinfer-plugin-dev cuda-nvcc-12-6`) to the Dockerfile; rebuilt
  `semantic_inference` + `semantic_inference_ros` with TensorRT
  (`ENABLE_TENSORRT 1`, links `libnvinfer.so.11` + `libcudart.so.12`); downloaded
  `ade20k-efficientvit_seg_l2.onnx` (206 MB) to `$HOME/.semantic_inference/`; switched
  `gazebo_khronos.launch.yaml` to `closed_set_node` (ADE20k + `ade20k_indoor` labelspace).
- The TensorRT engine is cached to `.trt` on first run; subsequent runs load it in ~1 s.

## Issue 6 — Closed-set node received no color (wrong remap)

- **Symptom**: `closed_set_node` loaded the engine but produced no labels
  (`Encountered class id` count == 0) while the color topic was flowing.
- **Cause**: `set_remap from: semantic_inference/color/image_raw` is resolved relative
  to the **node's** namespace (`semantic_inference`), producing
  `/semantic_inference/semantic_inference/color/image_raw`, but the node subscribes to
  `color/image_raw` → `/semantic_inference/color/image_raw`.
- **Fix**: use an absolute `from: /semantic_inference/color/image_raw`.

## Issue 7 — Khronos receiver QoS mismatch on color/depth

- **Symptom**: labels flowed (28 Hz) and color flowed (27 Hz), but the khronos node
  never integrated (`kimera_rpgo_optimizer` reported "0 factors" every 3 s).
- **Cause**: `hydra_ros` `FilterSub` subscribes with `rclcpp::QoS(queue_size)` =
  Reliable, but the Gazebo bag publishes color/depth with **BestEffort** (sensor data).
- **Fix**: make image data BestEffort everywhere:
  - `hydra_ros .../input/image_receiver.h`: `FilterSub` now uses `rclcpp::SensorDataQoS()`.
  - `semantic_inference_ros .../src/output_publisher.cpp`: label/color/overlay publishers
    use `rclcpp::SensorDataQoS()` (dropped the `1` = Reliable).
  - Rebuilt `hydra_ros` + `semantic_inference_ros`.

## Issue 8 — No odometry (empty pose graph)

- **Symptom**: after the QoS fix, the frontend still didn't integrate.
- **Cause**: the closed-set mapper `uHumans2.yaml` had no `active_window.odometry` entry,
  so Khronos defaulted to `RosPoseGraphTracker` (subscribes to
  `pose_graph_tools::PoseGraph`), which the Gazebo bag does not provide (it has
  `/odom` + `/tf`).
- **Fix**: add `active_window.odometry: {type: "tf"}` to the mapper config so Khronos
  reads `odom -> base_footprint_gz` from the bag's `/tf`.

## Issue 9 — (diagnostic) flaky DDS discovery

- `network_mode: host` + Fast DDS multicast makes fresh `ros2 node/topic/service`
  CLI invocations intermittently fail to discover the container's nodes, even though
  the long-running launch nodes discover each other fine. `ros2 topic hz` (which waits)
  works; one-shot `ros2 topic info`/`ros2 service list` often report "Unknown".
- Workaround: use rclpy `wait_for_service` (with a timeout) instead of `ros2 service call`.

## ✅ Result

- Closed-set path works end-to-end on the Gazebo AGV bag: labels flow (~28 Hz), the
  khronos node integrates, and `finish_mapping_and_save` saves the map:
  `mesh.ply` (362 KB), `frontend/mesh.ply`, `dsg.json` + `shared_dsg.json` (1.1 MB),
  `maps/dsg_*.json`, `deformation_graph.dgrf`.
- Log: `Saved 4D map with 2 time steps`, `Saved 2 individual DSGs`, `[Khronos Pipeline] Saved full state`.

---

## Isaac Sim path (RGB-D + GT semantic labels)

Third input path: Isaac Sim `isaac_world_test.usd` (warehouse + Carter robot), with GT
semantic labels (`use_gt_semantics: true`) and GT pose (`use_gt_frame: true`). Issues
encountered and fixes:

### Issue 10 — Circular trajectory (camera orbited the origin)

- **Symptom**: Khronos estimated a perfect circle regardless of the robot's motion.
- **Cause**: the recording script orbited the camera around the origin and published that
  circular pose as `world → camera`.
- **Fix**: publish the actual robot-mounted camera pose (see Issue 12/13).

### Issue 11 — `TF_SELF_TRANSFORM` (camera → camera)

- **Symptom**: TF2 spam `Ignoring transform ... frame_id and child_frame_id "camera"`.
- **Cause**: the script published a bogus `camera → camera` self-transform.
- **Fix**: removed it; publish only `world → camera`.

### Issue 12 — Camera axis misalignment (yaw showed up as roll)

- **Symptom**: the Carter's yaw appeared as roll in the reconstruction (swept scene graph).
- **Cause**: the USD camera frame (view `-Z`, up `+Y`, right `+X`) is not the Carter body
  frame (forward `+X`, right `-Y`, up `+Z`); a hand-rolled mount rotation got the axes wrong.
- **Fix**: use the Carter's **built-in `carter_camera_first_person`** camera
  (`/World/carter_v1/chassis_link/camera_mount/carter_camera_first_person`) and publish its
  world pose in the ROS camera frame (`+Z` forward, `+X` right, `+Y` down = USD rotated 180° about X).

### Issue 13 — Images from the third-person viewport camera

- **Symptom**: the recorded images were a third-person view, not the robot camera; the ground
  reconstructed tilted.
- **Cause**: the OmniGraph `setCamera` node never received `renderProductPath` (only the
  `ROS2CameraHelper` nodes did), so `setCamera` failed with `Invalid renderProduct ""` and the
  render stayed on the default viewport.
- **Fix**: connect `getRenderProduct.outputs:renderProductPath → setCamera.inputs:renderProductPath`.

### Issue 14 — Odometry time base mismatch

- **Symptom**: `Failed to find 'world_T_camera @ ... [ns]'` / `Lookup would require
  extrapolation into the past`; the frontend dropped inputs due to a missing pose.
- **Cause**: `ROS2CameraHelper` stamps images with **sim time**, but `/tf` `/odom` used the
  **wall clock** (or vice-versa) — the two time bases must match.
- **Fix**: stamp `/tf` + `/odom` with sim time (`tf_node.set_parameters([use_sim_time: true])`)
  and run Khronos with `sim_time_required: true`, matching the images.

### Issue 15 — Missing `/odom` (nav_msgs/Odometry)

- **Symptom**: pose graph empty / sweep; the Isaac Sim bag had `/tf` but no `/odom`.
- **Cause**: Khronos's pose-graph tracker (`PoseGraphFromOdom`) needs an odometry source.
- **Fix**: publish `/odom` (`nav_msgs/Odometry`, `world → camera`) alongside `/tf`.

### Issue 16 — `SimulationContext` invalidated by `open_stage`

- **Symptom**: `World or Simulation Object are invalidated` at launch.
- **Cause**: `SimulationContext` was created **before** `omni.usd.open_stage()`, which resets
  the stage and invalidates the context.
- **Fix**: open the stage first, wait for `is_stage_loading()` to finish, then create the
  `SimulationContext`.

### ✅ Isaac Sim result

The Carter's `carter_camera_first_person` camera is rendered, `/tf` + `/odom` are stamped in
sim time, and the launch uses `use_gt_semantics: true` + `use_gt_frame: true`. Re-record the
bag and re-run Khronos (the correct setup is documented in `isaac_sim/README.md`).

---

## Other notes

- Khronos writes output to `output_dir` directly and `remove_all()`s it when
  `overwrite: true`; `/root/output` must be a **subdirectory** (not the bind-mount
  point) or it fails with "Device or resource busy". Run scripts use a timestamped
  subdir.
- Model weights (CLIP/FastSAM/ADE20k) are cached under `$HOME`
  (=`/root/ros2_ws/semantic_home`, mounted) via `HOME` + `YOLO_CONFIG_DIR` env so they
  aren't re-downloaded per run. The TensorRT `.trt` engine is cached there too.
- The bag player is delayed (`sleep 15`) so semantic inference initializes before the
  bag data flows.
- Save the map by calling the `finish_mapping_and_save` service
  (`docker/scripts/finish_mapping.py`), not by SIGINT (SIGINT does not trigger the save).

