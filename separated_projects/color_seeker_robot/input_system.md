# Robot Input Layer Documentation — Color Target Seeker Robot

This document describes the camera input system for **Zadanie 3: Color Target Seeker Robot**. It serves as the verification report showing that the robot can receive useful target readings and publish them to the ROS2 environment.

---

## 1. Camera Input System

### Camera Description
* **Model/Type**: Raspberry Pi Camera Module V2 (8 Megapixel, Sony IMX219 sensor).
* **Position**: Mounted on the upper mast of the differential chassis, elevated at 20 cm from ground level.
* **Direction**: Pointing horizontally forward in the driving direction.
* **Purpose**: Capture the field of view in front of the robot to scan, identify, and lock onto color target cylinders (Red, Green, Blue, Yellow).

### Camera Output
* **Resolution**: 640 x 480 pixels.
* **Framerate**: 30 FPS.
* **Format**: BGR8 Raw array data.
* **ROS2 Topic**: `/camera/image_raw` (sensor_msgs/msg/Image)
* **Status Topic**: `/camera/status` (std_msgs/msg/String)

---

## 2. Sensor Input System

### Sensor Description
* **Additional Sensors**: No additional hardware sensors (such as ultrasonic distance sensors, infrared detectors, encoders, or IMUs) are connected to the vehicle at this stage. All environment tracking and target-seeking decisions are processed exclusively using the visual camera frame input.

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
**Yes.** Mounted horizontally, the camera has a wide-angle field of view (FOV) covering the entire navigation floor area, letting it spot colored target cards or cylinders up to 2.5 meters away.

### Is the image clear enough?
**Yes.** Color threshold isolation performs best under balanced white lighting. Shadows and high reflections are minimized by setting dynamic saturation and value calibration bounds.

### Known Problems
* **Reflections**: High reflections or shadows under direct ambient lighting can distort hue filtration values. Solved by tuning OpenCV HSV tolerance bounds.

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