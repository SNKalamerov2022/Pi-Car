#!/usr/bin/env python3
"""
Visual Inspection Robot - Vision Processing Node (OpenCV & ROS2)
Author: Simeon's Senior Robotics Mentor

This script processes webcam images to detect the center of a guide line.
It can run in two modes:
1. STANDALONE MODE (Default if ROS2 is not running): Runs a standard OpenCV webcam loop, 
   perfect for testing on your Windows laptop.
2. ROS2 NODE MODE: Runs as a ROS2 node, subscribing to /camera/image_raw and 
   publishing the calculated path deviation to /vision/line_error.
"""

import sys
import cv2
import numpy as np

# Try to import ROS2 components; if they fail, we run in standalone mode
try:
    import rclpy
    from rclpy.node import Node
    from sensor_msgs.msg import Image
    from std_msgs.msg import Float32
    from cv_bridge import CvBridge
    ROS2_AVAILABLE = True
except ImportError:
    ROS2_AVAILABLE = False


# HSV Color Bounds for Target Detection
# OpenCV HSV range: H (0-180), S (0-255), V (0-255)
COLOR_RANGES = {
    "red": [
        ((0, 100, 50), (10, 255, 255)),
        ((170, 100, 50), (180, 255, 255))
    ],
    "green": [
        ((35, 100, 50), (85, 255, 255))
    ],
    "blue": [
        ((100, 100, 50), (140, 255, 255))
    ],
    "yellow": [
        ((20, 100, 100), (35, 255, 255))
    ]
}

# Global Tracker Instances
tracker1 = None
tracker1_initialized = False
tracker2 = None
tracker2_initialized = False

def reset_crossbar_calibration(force=False):
    global tracker1, tracker1_initialized, tracker2, tracker2_initialized
    if force or not tracker1_initialized:
        tracker1 = None
        tracker1_initialized = False
        tracker2 = None
        tracker2_initialized = False

def is_tracker_active():
    global tracker1_initialized
    return tracker1_initialized


def process_frame(frame, is_running=False, is_mock=False, click_coords=None, mode="line", target_color=None):
    """
    Core OpenCV logic supporting:
      1. line (traditional line following & click-to-track)
      2. color (HSV segmentation for target color seeking)
    """
    if frame is None:
        return None, 0.0, None, False, -1, -1

    # Get dimensions
    height, width, _ = frame.shape
    
    if mode == "color" and target_color:
        # --- COLOR TARGET SEEKER MODE ---
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = None
        ranges = COLOR_RANGES.get(target_color.lower())
        if ranges:
            for lower, upper in ranges:
                r_mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                if mask is None:
                    mask = r_mask
                else:
                    mask = cv2.bitwise_or(mask, r_mask)
        else:
            mask = np.zeros(frame.shape[:2], dtype=np.uint8)

        # Cleanup morphological noise
        morph_kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, morph_kernel, iterations=1)
        mask = cv2.dilate(mask, morph_kernel, iterations=2)

        contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        largest_contour = None
        max_area = 0
        for c in contours:
            area = cv2.contourArea(c)
            if area > max_area:
                max_area = area
                largest_contour = c

        crossbar_detected = False
        bm_y_min, bm_y_max = -1, -1
        centroid_x = width // 2
        
        # Minimum area to consider a detected object valid (filters out noise/far objects)
        if largest_contour is not None and max_area > 300:
            M = cv2.moments(largest_contour)
            if M["m00"] > 0:
                centroid_x = int(M["m10"] / M["m00"])
                centroid_y = int(M["m01"] / M["m00"])
            else:
                centroid_x = width // 2
                centroid_y = height // 2

            x, y, w, h = cv2.boundingRect(largest_contour)
            crossbar_detected = True
            bm_x_min = x
            bm_x_max = x + w
            bm_y_min = y
            bm_y_max = y + h

            # Draw green bounding box around target
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
            # Draw target centroid dot
            cv2.circle(frame, (centroid_x, centroid_y), 5, (0, 0, 255), -1)
            # Annotate detected color information
            cv2.putText(frame, f"TARGET: {target_color.upper()} (Area: {int(max_area)})", (15, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        else:
            cv2.putText(frame, f"SEARCHING FOR {target_color.upper()}...", (15, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Deviation from center
        error = float(centroid_x - (width // 2))
        # Note: We use bm_y_max - bm_y_min (height) and area in the state machine.
        # But we also return max_area through a sneaky way or compute it from height/width.
        # To avoid breaking function signatures, we can repurpose the bm_y_min as the area!
        # Wait, let's keep bm_y_min as y, but let's pass a tuple or use height.
        # Actually, bm_y_max - bm_y_min (height) and max_area are related.
        # Let's pass the area as bm_y_min if crossbar_detected is true, or keep it standard.
        # Wait! Let's return max_area directly by replacing bm_y_min with the area!
        # If we return: frame, error, mask, crossbar_detected, bm_y_max, max_area
        # Let's check how the calling code uses it in app.py:
        # raw_marker, bm_y_max, bm_y_min = marker_data
        # branch_height = bm_y_max - bm_y_min
        # reached_branch = (bm_y_max > 400 and branch_height > 60)
        # So it uses branch_height.
        # If we return bm_y_min = area, branch_height = bm_y_max - area which is negative.
        # So we should keep standard coordinates: bm_y_max and bm_y_min, and we can calculate the area
        # in app.py or just use the bounding box height/width to determine distance.
        # Bounding box height > 80 is a perfect indicator that the robot reached the target!
        # Yes, using the height of the bounding box is extremely standard and robust!
        
        return frame, error, mask, crossbar_detected, bm_y_max, bm_y_min

    else:
        # --- TRADITIONAL LINE / CHECKPOINT FOLLOW MODE ---
        # Get dimensions
        roi_start_row = int(height * 0.3)
        roi_end_row = height
        roi = frame[roi_start_row:roi_end_row, 0:width]
        
        # 2. Convert to Grayscale
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # 3. Blur
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        
        # 4. Threshold
        _, thresholded = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 4b. Morphological cleanup
        morph_kernel = np.ones((5, 5), np.uint8)
        thresholded = cv2.erode(thresholded, morph_kernel, iterations=1)
        thresholded = cv2.dilate(thresholded, morph_kernel, iterations=2)
        
        # 5b. Contour filtering
        contours, _ = cv2.findContours(thresholded.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        clean_mask = np.zeros_like(thresholded)
        for c in contours:
            if cv2.contourArea(c) > 100:
                cv2.drawContours(clean_mask, [c], -1, 255, -1)
        thresholded = clean_mask
        
        # 5. OpenCV MIL Tracker logic
        global tracker1, tracker1_initialized, tracker2, tracker2_initialized
        crossbar_detected = False
        bm_y_min, bm_y_max = 9999, -1
        bm_x_min, bm_x_max = 9999, -1
        
        if click_coords is not None and isinstance(click_coords, list):
            box_w, box_h = 60, 60
            if len(click_coords) >= 1 and not tracker1_initialized:
                cx, cy = click_coords[0]
                init_box = (max(0, cx - box_w//2), max(0, cy - box_h//2), box_w, box_h)
                try:
                    if hasattr(cv2, 'TrackerMIL_create'):
                        tracker1 = cv2.TrackerMIL_create()
                    elif hasattr(cv2, 'TrackerMIL') and hasattr(cv2.TrackerMIL, 'create'):
                        tracker1 = cv2.TrackerMIL.create()
                    else:
                        raise AttributeError("No TrackerMIL builder found in cv2")
                    tracker1.init(frame, init_box)
                    tracker1_initialized = True
                except Exception as e:
                    tracker1 = None
                    tracker1_initialized = False
                    print(f"Failed to initialize tracker1: {e}")
            if len(click_coords) >= 2 and not tracker2_initialized:
                cx, cy = click_coords[1]
                init_box = (max(0, cx - box_w//2), max(0, cy - box_h//2), box_w, box_h)
                try:
                    if hasattr(cv2, 'TrackerMIL_create'):
                        tracker2 = cv2.TrackerMIL_create()
                    elif hasattr(cv2, 'TrackerMIL') and hasattr(cv2.TrackerMIL, 'create'):
                        tracker2 = cv2.TrackerMIL.create()
                    else:
                        raise AttributeError("No TrackerMIL builder found in cv2")
                    tracker2.init(frame, init_box)
                    tracker2_initialized = True
                except Exception as e:
                    tracker2 = None
                    tracker2_initialized = False
                    print(f"Failed to initialize tracker2: {e}")
            
        if tracker1_initialized and tracker1 is not None:
            try:
                success, bbox = tracker1.update(frame)
            except Exception as e:
                success = False
                tracker1_initialized = False
                tracker1 = None
            if success:
                x, y, w, h = [int(v) for v in bbox]
                crossbar_detected = True
                bm_x_min = x
                bm_x_max = x + w
                bm_y_min = y
                bm_y_max = y + h
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 255), 3)
                cv2.putText(frame, "TARGET 1", (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
            else:
                cv2.putText(frame, "TARGET 1 LOST", (50, 50), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                            
        if tracker2_initialized and tracker2 is not None:
            try:
                success2, bbox2 = tracker2.update(frame)
            except Exception as e:
                success2 = False
                tracker2_initialized = False
                tracker2 = None
            if success2:
                x, y, w, h = [int(v) for v in bbox2]
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 3)
                cv2.putText(frame, "TARGET 2", (x, max(20, y - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            else:
                cv2.putText(frame, "TARGET 2 LOST", (50, 80), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        else:
            # Autonomous crossbar detection using row sum density
            if is_running:
                row_sums = np.sum(thresholded, axis=1) / 255
                crossbar_rows = np.where(row_sums > 100)[0]
                if len(crossbar_rows) >= 3:
                    col_sums = np.sum(thresholded[crossbar_rows, :], axis=0)
                    crossbar_cols = np.where(col_sums > 0)[0]
                    if len(crossbar_cols) > 80:
                        crossbar_detected = True
                        bm_x_min = int(np.min(crossbar_cols))
                        bm_x_max = int(np.max(crossbar_cols))
                        bm_y_min = int(roi_start_row + np.min(crossbar_rows))
                        bm_y_max = int(roi_start_row + np.max(crossbar_rows))
                        # Draw a bounding box on the frame for autonomous visual feedback
                        cv2.rectangle(frame, (bm_x_min, bm_y_min), (bm_x_max, bm_y_max), (255, 0, 255), 3)
                        cv2.putText(frame, f"INSPECTION MARKER DETECTED (H: {bm_y_max - bm_y_min}px)", 
                                    (bm_x_min, max(20, bm_y_min - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 1)
        
        # 6. Centroid calculation
        moments = cv2.moments(thresholded)
        line_center_x = width // 2
        line_found = False
        
        if tracker1_initialized:
            if crossbar_detected and bm_x_min != 9999:
                line_center_x = (bm_x_min + bm_x_max) // 2
                line_found = True
            else:
                line_center_x = width // 2
                line_found = False
        else:
            if moments['m00'] > 800:
                line_center_x = int(moments['m10'] / moments['m00'])
                line_found = True
            
        # 7. Error calculation
        image_center_x = width // 2
        error = float(line_center_x - image_center_x)
        
        return frame, error, thresholded, crossbar_detected, bm_y_max, bm_y_min



if ROS2_AVAILABLE:
    class LineFollowerVisionNode(Node):
        """
        ROS2 Node that subscribes to raw camera images, processes them,
        and publishes the calculated line tracking error.
        """
        def __init__(self):
            super().__init__('vision_node')
            self.get_logger().info('Initializing LineFollowerVisionNode...')
            
            # Bridge to convert ROS Images to OpenCV Images
            self.bridge = CvBridge()
            
            # Subscribers and Publishers
            self.subscription = self.create_subscription(
                Image,
                '/camera/image_raw',
                self.image_callback,
                10  # Queue size
            )
            
            self.error_publisher = self.create_publisher(
                Float32,
                '/vision/line_error',
                10
            )
            
            self.get_logger().info('Vision Node initialized and listening on /camera/image_raw')

        def image_callback(self, msg):
            try:
                # Convert ROS Image to OpenCV BGR image
                cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            except Exception as e:
                self.get_logger().error(f'Failed to convert image: {str(e)}')
                return
                
            # Process the image frame using our core function
            processed_frame, error, thresholded, marker_detected, bm_y_max, bm_y_min = process_frame(cv_image)
            
            # Publish the error value
            error_msg = Float32()
            error_msg.data = error
            self.error_publisher.publish(error_msg)
            
            # Log the error tracking value
            self.get_logger().debug(f'Published Line Error: {error}')


def run_standalone():
    """
    Runs OpenCV processing directly using your computer's built-in webcam.
    Allows testing the line detection logic without needing ROS2 installed!
    """
    print("\n--- Starting Standalone Webcam Test Mode ---")
    print("Connecting to default camera index 0...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("ERROR: Could not open webcam. Make sure it is connected and not in use by another app.")
        return

    print("Webcam initialized. Press 'q' key in the video window to quit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break
            
        # Process the frame using our algorithm
        processed_frame, error, thresholded, marker_detected, bm_y_max, bm_y_min = process_frame(frame)
        
        # Show the result in a windows
        cv2.imshow('Live Camera (Processed Feed)', processed_frame)
        cv2.imshow('Binary Mask (Line Isolation)', thresholded)
        
        # Check for user quit command 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()
    print("Standalone test ended cleanly.")


def main(args=None):
    # Determine if we run standalone or ROS2 node
    # If ROS2 libraries imported successfully AND --standalone is not passed as an argument
    if ROS2_AVAILABLE and "--standalone" not in sys.argv:
        rclpy.init(args=args)
        node = LineFollowerVisionNode()
        try:
            rclpy.spin(node)
        except KeyboardInterrupt:
            pass
        finally:
            node.destroy_node()
            rclpy.shutdown()
    else:
        # Fall back to running standalone webcam mode
        if not ROS2_AVAILABLE:
            print("Note: ROS2 libraries not detected on this system. Running standalone.")
        run_standalone()


if __name__ == '__main__':
    main()
