#!/usr/bin/env python3
"""Call Khronos's finish_mapping_and_save service (std_srvs/Empty)."""
import rclpy
from std_srvs.srv import Empty


def try_call(node, name):
    client = node.create_client(Empty, name)
    if client.wait_for_service(timeout_sec=8.0):
        fut = client.call_async(Empty.Request())
        rclpy.spin_until_future_complete(node, fut, timeout_sec=30.0)
        print(f"finish_mapping_and_save called OK on {name}", flush=True)
        return True
    print(f"service {name} not available", flush=True)
    return False


def main():
    rclpy.init()
    node = rclpy.create_node("finish_mapping_caller")
    for name in ("/finish_mapping_and_save", "/khronos_node/finish_mapping_and_save"):
        if try_call(node, name):
            break
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
