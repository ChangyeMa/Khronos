# Khronos — Docker (ROS2 Jazzy)

Runs [Khronos](https://github.com/MIT-SPARK/Khronos) in a ROS2 **Jazzy**
(Ubuntu 24.04) container. Khronos requires ROS2 Iron+; it will **not** build on
Humble.

## Prerequisites

- Docker + Docker Compose v2.
- (Recommended) NVIDIA GPU + [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
  for RViz rendering / open-set segmentation. CPU-only works too — comment out
  `gpus:` and the `NVIDIA_*` env vars in `docker-compose.yml` — just not recommended.
- A ROS2 bag (sqlite3 or mcap). Humble-recorded sqlite3 bags play fine in Jazzy.

## Data layout (all outside this repo)

Everything is kept under `~/khronos_data/` (change the path in `docker-compose.yml` if desired):

```
~/khronos_data/
├── ros2_ws/    # cloned sources + colcon build artifacts
├── bags/       # your ROS2 bags, e.g. bags/tesse_cd_office/
└── output/     # results: timing stats, 4D maps, eval output
```

Download/prepare bag data under `~/khronos_data/bags/<dataset>/`.

## Build

```bash
cd <repo>/docker
xhost +local:          # allow RViz to reach your X display (resets on logout)
docker compose build
docker compose run --rm khronos /root/scripts/build.sh
```

`build.sh` clones Khronos (override with `KHRONOS_URI` / `KHRONOS_BRANCH`) and its
source dependencies, then `colcon build --symlink-install -DCMAKE_BUILD_TYPE=Release`.

## Run

```bash
cd <repo>/docker
# simulated (office):
docker compose run --rm khronos /root/scripts/run_sim.sh
# simulated (apartment):
docker compose run --rm -e DATASET=tesse_cd_apartment khronos /root/scripts/run_sim.sh
# real Jackal (mezzanine):
docker compose run --rm khronos /root/scripts/run_jackal.sh
```

After playback finishes, save the results (second terminal):

```bash
docker compose run --rm khronos bash -lc \
  "source /root/ros2_ws/install/setup.bash && ros2 service call /khronos_node/experiment/finish_mapping_and_save std_srvs/srv/Empty"
```

Results land in `~/khronos_data/output/<timestamp>/`.

## Evaluate (accuracy metrics)

```bash
docker compose run --rm khronos /root/scripts/eval.sh /root/output/<timestamp> office.yaml
```

## Notes

- The Khronos source is cloned by `build.sh` from this fork
  (`ChangyeMa/Khronos@docker-setup`). Override with `KHRONOS_URI`/`KHRONOS_BRANCH` if needed.
- Topic names must match the dataset config (sim: `/tesse/...`, real: `/sparkal1/...` + `/oneformer/...`).
