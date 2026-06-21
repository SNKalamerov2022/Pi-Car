# Robot Input Layer Documentation — Visual Inspection Robot

This document describes the camera input system for **Zadanie 19: Visual Inspection Robot**. It serves as the verification report showing that the robot can receive useful environment readings and publish them to the ROS2 system.

---

## 1. Camera Input System

### Camera Description
* **Model/Type**: Raspberry Pi Camera Module V2 (8 Megapixel, Sony IMX219 sensor).
* **Position**: Mounted on the front bumper center of the differential chassis, tilted downwards at an angle of 35 degrees.
* **Direction**: Pointing downwards at the floor immediately in front of the vehicle.
* **Purpose**: Capture close-range lane guidelines (black tape) and horizontal crossbars (inspection points) taped to the classroom floor.

### Camera Output
* **Resolution**: 640 x 480 pixels (configured for frame processing efficiency and reduced packet latency).
* **Framerate**: 30 FPS.
* **Format**: BGR8 Raw array data.
* **ROS2 Topic**: `/camera/image_raw` (sensor_msgs/msg/Image)
* **Status Topic**: `/camera/status` (std_msgs/msg/String)

---

## 2. Sensor Input System

### Sensor Description
* **Additional Sensors**: No additional hardware sensors (such as ultrasonic distance sensors, infrared detectors, encoders, or IMUs) are connected to the vehicle at this stage. All environment tracking and navigation decisions are processed exclusively using the visual camera frame input.

---

## 3. Test Evidence

### ROS2 Topic Verification
To verify that the camera node is successfully publishing data to the ROS2 environment, the following terminal checks were performed:

#### 1. Listing Active Topics
```bash
$ ros2 topic list
/camera/image_raw
/camera/status
```

#### 2. Checking Camera Topic Frequency
```bash
$ ros2 topic hz /camera/image_raw
average rate: 29.982
  min: 0.031s max: 0.035s std dev: 0.001s window: 30
```

---

## 4. Input Testing & Verification Questions

### Can the camera see the required area?
**Yes.** The downward tilt angle of 35 degrees captures a 60cm wide floor view directly in front of the wheels, ensuring the black guides and inspection markers are completely visible before they cross the wheels' axis.

### Is the image clear enough?
**Yes.** Under classroom ambient fluorescent lights, contrast levels between the black tape and light-colored floor are above 70%. Sharpness holds steady during motion.

### Known Problems
* **Lighting Reflections**: Highly reflective floor tile glare can cause white hotspots in the thresholding mask. Filtered using morphological erosion filters.

---

## 5. Testing Safety Checklist

During all input device configuration checks, the robot chassis remains stationary and raised.

| Safety Item | Checked? |
| :--- | :--- |
| Robot is placed safely on the table or floor | **[X]** |
| Motors are stopped during camera testing | **[X]** |
| Battery is mounted securely | **[X]** |
| Wires are not touching the wheels | **[X]** |
| Camera is firmly mounted | **[X]** |
| No exposed wires can cause short circuits | **[X]** |
| Robot can be turned off quickly | **[X]** |
| Testing area is safe and clear | **[X]** |