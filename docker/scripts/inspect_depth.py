import rosbag2_py
import cv2, numpy as np
import cv_bridge
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image

uri = "/data/bags/isaac_sim"
reader = rosbag2_py.SequentialReader()
reader.open(rosbag2_py.StorageOptions(uri=uri, storage_id="sqlite3"), rosbag2_py.ConverterOptions(input_serialization_format="cdr", output_serialization_format="cdr"))
bridge = cv_bridge.CvBridge()
vals = []
n = 0
while reader.has_next():
    topic, data, t = reader.read_next()
    if topic == "/isaac/depth/image_raw":
        m = deserialize_message(data, Image)
        img = bridge.imgmsg_to_cv2(m, desired_encoding="passthrough")
        vals.append((m.encoding, float(np.nanmin(img)), float(np.nanmax(img)), float(np.nanmean(img))))
        n += 1
        if n >= 8:
            break
print("DEPTH_SAMPLES (encoding, min, max, mean):")
for v in vals:
    print("  ", v)
