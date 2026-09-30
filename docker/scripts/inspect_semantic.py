#!/usr/bin/env python3
"""Inspect the Isaac Sim GT semantic topic in a bag: print encoding + distinct ids.

Run inside the Khronos container:
    docker compose run --rm khronos bash -c \
      'source /root/ros2_ws/install/setup.bash && python3 /root/scripts/inspect_semantic.py /data/bags/isaac_sim'
"""
import sys
from collections import Counter

import cv2
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image
import cv_bridge


def main():
    uri = sys.argv[1] if len(sys.argv) > 1 else "/data/bags/isaac_sim"
    topic = sys.argv[2] if len(sys.argv) > 2 else "/isaac/semantic/image_raw"

    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3"),
        rosbag2_py.ConverterOptions(
            input_serialization_format="cdr",
            output_serialization_format="cdr",
        ),
    )

    bridge = cv_bridge.CvBridge()
    counts = Counter()
    encoding = None
    n = 0
    while reader.has_next():
        (topic_name, data, _t) = reader.read_next()
        if topic_name != topic:
            continue
        msg = deserialize_message(data, Image)
        img = bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
        encoding = msg.encoding
        counts.update(np.unique(img).tolist())
        n += 1
        if n >= 200:
            break

    print(f"topic: {topic}")
    print(f"encoding: {encoding}")
    print(f"messages inspected: {n}")
    print(f"distinct label values ({len(counts)}):")
    for val, cnt in sorted(counts.items()):
        print(f"  {val}: {cnt}")


if __name__ == "__main__":
    main()
