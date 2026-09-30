# Khronos — Data Preparation Guide

Khronos is an **online metric-semantic RGB-D SLAM**. It reconstructs a volumetric
(TSDF) map from **dense depth**, and performs object / motion / change detection by
fusing **semantic labels** with RGB + depth. This document describes the sensor data
Khronos needs and how to prepare it.

## 1. Required sensor streams

Khronos consumes **five synchronized streams** per camera frame:

| # | Stream | ROS message | Format / notes |
|---|--------|-------------|----------------|
| 1 | Color | `sensor_msgs/msg/Image` | any encoding `cv_bridge` converts to **RGB8** (`rgb8`, `bgr8`, `bayer_*`, …) |
| 2 | Depth | `sensor_msgs/msg/Image` | **metric depth in meters**, registered/aligned to the color frame; `32FC1` (float meters) recommended |
| 3 | Semantic labels | `sensor_msgs/msg/Image` | **integer label IDs** (`mono8`/`mono16`) matching a label-space config |
| 4 | Camera info | `sensor_msgs/msg/CameraInfo` | intrinsics `K`, `D`, `P`, `R`, width/height |
| 5 | Pose | `tf2_msgs/msg/TFMessage` (`/tf`, `/tf_static`) **or** `nav_msgs/msg/Odometry` | sensor↔robot extrinsics + robot↔world odometry |

The receiver subscribes to these relative topic names (remapped in the launch file to
whatever your dataset actually publishes):

- `rgb/image_raw`
- `depth_registered/image_rect`
- `semantic/image_raw`
- `rgb/camera_info`

Color / depth / labels are **time-synchronized** (approximate-time policy), so they
must be published close together for the same frame.

## 2. LiDAR is NOT used

Khronos reconstructs from a **dense per-pixel depth image**, not from LiDAR scans.
Hydra does have a pointcloud receiver, but Khronos's configs do not use it.

> A LiDAR + RGB setup with **no depth camera** is not directly usable — projecting
> LiDAR into the image gives sparse depth, which works poorly for TSDF integration.

## 3. Depth is mandatory (RGB-only is not enough)

Khronos is a **depth-based** (RGB-D) method. It does **not** estimate depth from RGB.
A monocular RGB-only dataset **cannot** be run with Khronos.

## 4. Semantic labels — the key requirement

Khronos needs per-pixel semantic labels for object / motion / change detection.

Label sources used by the paper (RSS 2024):

| Dataset | Label source |
|---|---|
| Simulation (`tesse_cd`) | **ground-truth** labels from the simulator |
| Real (`mezzanine`) | **pre-recorded OneFormer** labels |

`semantic_inference` (bundled as a source dependency) provides **online** labels on RGB:

- **Closed-set** — ADE20k indoor classes, C++/TensorRT (needs CUDA + GPU).
- **Open-set** — FastSAM + CLIP (ViT-L/14), Python (no TensorRT needed).

> For a **fair comparison against the paper**, use the same label source:
> ground-truth (simulation) or OneFormer (real). Using `semantic_inference` is a
> *different* experiment — label-quality differences can be mistaken for SLAM issues.

Model weights are **downloaded on first run** (they are not bundled in the repo).

## 5. Planned datasets

### Dataset 1 — Gazebo Classic (no GT semantics)

- Record: `rgb`, `depth` (registered), `camera_info`, `/tf` + `/tf_static` (or odom).
- Semantics: `semantic_inference` (open-set `use_openset_semantics:=true`, or closed-set).
- Launch: `use_gt_semantics:=false [use_openset_semantics:=true]`.
- Remap Gazebo topics to Khronos's expected names.

### Dataset 2 — Isaac Sim (GT semantics) — paper-equivalent

- Record: `rgb`, `depth`, `camera_info`, **GT semantic label image**, (optional) GT
  instance, **GT pose**, `/tf`.
- Launch: `use_gt_semantics:=true` (default).
- Needs: a **label-space YAML** for Isaac Sim's class IDs + topic remap.

### Dataset 3 — Real world (RGB only)

- **Blocked by missing depth.** Add an RGB-D camera (or stereo depth) first.
- Then: pre-record **OneFormer** labels (paper-equivalent), or use `semantic_inference`.
- If using odometry (no GT pose): follow the `jackal` config path (`odom_to_tf.py`).

## 6. Recording checklist

For each frame, ensure all of the following are captured at a consistent rate:

- [ ] RGB image (`sensor_msgs/Image`)
- [ ] Depth image, **metric meters**, registered to RGB (`sensor_msgs/Image`, `32FC1`)
- [ ] Semantic label image, integer IDs (`sensor_msgs/Image`)
- [ ] Camera info (`sensor_msgs/CameraInfo`)
- [ ] TF (`/tf`, `/tf_static`) or odometry (`nav_msgs/Odometry`)
- [ ] Consistent `frame_id`s matching the config (sensor frame ↔ robot frame)
- [ ] `/clock` (or `use_sim_time`) for reproducible playback

## 7. TODO

- [ ] Gazebo Classic: record + run with `semantic_inference`.
- [ ] Isaac Sim: record GT semantics + write label-space YAML + remap.
- [ ] Real world: obtain a depth sensor, then record RGB-D + OneFormer labels.
