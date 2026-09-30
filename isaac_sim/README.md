# Isaac Sim path (RGB-D + GT semantic labels)

Khronos's third input path: Isaac Sim provides RGB + depth + **GT semantic labels**
(no semantic inference). This mirrors the upstream `play_uhumans` GT path
(`use_gt_semantics: true`, `use_gt_frame: true`).

## Files

| File | Purpose |
|------|---------|
| `isaac_sim/isaac_sim_record.py` | Isaac Sim script: RGB + depth + semantic + camera_info + TF |
| `khronos_ros/config/datasets/isaac_sim.yaml` | Dataset config (`ClosedSetImageReceiver`) |
| `khronos_ros/launch/isaac_sim.launch.yaml` | GT-semantics launch |
| `khronos_ros/config/label_spaces/isaac_sim_label_space.yaml` | Semantic label space (fill in after recording) |
| `docker/scripts/inspect_semantic.py` | Prints the distinct semantic ids + encoding from a bag |

## Step 1 — Record the Isaac Sim bag

Isaac Sim publishes to ROS2 topics via its bundled bridge (ROS2 Humble). Record them
with the **system** `ros2 bag record` in a second terminal. Both must use the same
RMW — set `RMW_IMPLEMENTATION` to the same value in both terminals (e.g.
`rmw_cyclonedds_cpp`, or leave it unset to use Fast DDS on both).

Terminal 1 — run Isaac Sim (host, needs a GPU + display; use `--headless` to test):

```bash
cd /home/jiaming/isaac_sim4.5/isaac-sim-standalone-4.5.0-linux-x86_64
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
  ./python.sh /home/jiaming/Khronos/isaac_sim/isaac_sim_record.py
```

Terminal 2 — record the topics (system ROS2 Humble):

```bash
mkdir -p ~/khronos_data/bags/isaac_sim
rm -f ~/khronos_data/bags/isaac_sim/*.db3
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 bag record -o ~/khronos_data/bags/isaac_sim \
  /isaac/rgb/image_raw \
  /isaac/depth/image_raw \
  /isaac/semantic/image_raw \
  /isaac/camera_info \
  /tf /tf_static /clock /odom
```

Confirmed topics (verified with `ros2 topic list`/`echo`):

| Topic | Type | Encoding |
|-------|------|----------|
| `/isaac/rgb/image_raw` | `sensor_msgs/Image` | `rgb8` |
| `/isaac/depth/image_raw` | `sensor_msgs/Image` | `32FC1` (meters) |
| `/isaac/semantic/image_raw` | `sensor_msgs/Image` | `32SC1` (semantic ids) |
| `/isaac/camera_info` | `sensor_msgs/CameraInfo` | — |
| `/clock` | `rosgraph_msgs/Clock` | — |
| `/tf` | `tf2_msgs/TFMessage` | `world → camera` |
| `/odom` | `nav_msgs/Odometry` | `world → camera` (GT odometry) |

Stop the recording after a few orbits (Ctrl+C both). The bag is written to
`~/khronos_data/bags/isaac_sim/` (mounted at `/data/bags/isaac_sim` in the container).

### Drive the Carter robot (optional)

The script subscribes to `/cmd_vel` (differential drive) and drives the Carter.
In a third terminal, use `teleop_twist_keyboard`:

```bash
RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

> The script opens your `isaac_world_test.usd` (warehouse + Carter robot) and
> renders from the Carter's **built-in `carter_camera_first_person`** camera
> (`/World/carter_v1/chassis_link/camera_mount/carter_camera_first_person`), so
> the recorded view and `/odom` `/tf` odometry follow the robot (driven via
> `/cmd_vel` / `teleop_twist_keyboard`). The wheel radius / track width are
> `CARTER_WHEEL_RADIUS` / `CARTER_TRACK_WIDTH` in the script (adjust if the
> motion looks off).

## Step 2 — Inspect the semantic ids (fill the label space)

Isaac Sim's `semantic_segmentation` emits **sequential integer ids** (verified:
`32SC1`, ids `1..23` for the warehouse + robots). Find the distinct ids and the
image encoding:

```bash
cd ~/Khronos/docker
docker compose run --rm khronos bash -c \
  'source /root/ros2_ws/install/setup.bash && python3 /root/scripts/inspect_semantic.py /data/bags/isaac_sim'
```

Then edit `khronos_ros/config/label_spaces/isaac_sim_label_space.yaml` to map each
id to a name (e.g. `{label: 1234567, name: Floor}`). If the encoding is not a
single-channel integer image (e.g. it is `32FC1` or `8UC3`), remap/normalize it
first — see the note below.

> **Note on encoding**: Khronos's `ClosedSetImageReceiver` reads the label image
> directly. If Isaac Sim publishes semantic as `32FC1`/`8UC3`, add a small remap
> node (or change the `ROS2CameraHelper` `type`) so the labels are a single-channel
> integer image (`16SC1`/`32SC1`).

## Step 3 — Run Khronos

```bash
cd ~/Khronos/docker
docker compose run --rm khronos bash -c \
  'source /root/ros2_ws/install/setup.bash && ros2 launch khronos_ros isaac_sim.launch.yaml'
```

After the bag finishes (~90 s), save the map in a second terminal:

```bash
cd ~/Khronos/docker
docker compose run --rm khronos bash -c \
  'source /root/ros2_ws/install/setup.bash && python3 /root/scripts/finish_mapping.py'
```

Output: `~/khronos_data/output/isaac_sim/{mesh.ply, dsg.json, frontend/mesh.ply, ...}`.
