# Pi-Car: Autonomous Robotics Project (2026)

This repository contains the codebase and deliverables for our two-wheeled differential drive robot car project, developed for the school robotics curriculum. 

The project is split into two student submissions based on the same hardware chassis:
1. **Color Target Seeker Robot** (Zadanie 3) - Autonomous scanning, hue thresholding, and approach stop at 10cm.
2. **Visual Inspection Robot** (Zadanie 19) - Autonomous guide line tracking and checkpoint target camera inspections.

---

## Repository Structure

```
Pi-Car/
├── app.py                     # Main Flask server running on the physical robot
├── vision_node.py             # OpenCV line-tracking and marker detection node (ROS2 compatible)
├── test_morph.py              # Auxiliary morphology calibration tool
├── templates/                 # Global UI templates for physical robot desk test control
│   └── index.html
├── documents/
│   ├── visual_inspection_robot/  # Deliverables folder for Zadanie 19 (Visual Inspection)
│   │   ├── app/                  # Flask package (models, forms, routes, templates, assets)
│   │   ├── camera_node.py        # ROS2 camera publisher node
│   │   ├── sensor_node.py        # ROS2 encoder & bumper publisher node
│   │   ├── input_system.md       # Input layer documentation & safety report
│   │   ├── use_case.md           # UML Use Case Diagram
│   │   └── README.md             # Running instructions for port 5000
│   │
│   └── color_seeker_robot/       # Deliverables folder for Zadanie 3 (Color Seeker)
│       ├── app/                  # Flask package (cyberpunk styling, routes, templates)
│       ├── camera_node.py        # ROS2 camera publisher node
│       ├── sensor_node.py        # ROS2 distance & yaw publisher node
│       ├── input_system.md       # Target isolation details & safety report
│       ├── use_case.md           # UML Use Case Diagram
│       └── README.md             # Running instructions for port 5001
```

---

## Hardware Configuration (BOM)

* **Controller**: Raspberry Pi 4B (Running Ubuntu Desktop / headless setup)
* **Motors**: 2x 5V DC Gear Motors with encoder disks
* **Motor Driver**: L298N Dual H-Bridge module
* **Camera**: USB Webcam (Sony IMX219 or standard USB equivalent)
* **Distance Sensor**: HC-SR04 Ultrasonic sensor
* **Orientation Sensor**: MPU6050 Gyro/IMU
* **Power Source**: 5V/3A Power Bank (Pi) & 4x AA Battery Pack (Motors)

### BCM GPIO Pin Mappings
* **Left Motor**: `IN1` = Pin 17, `IN2` = Pin 27
* **Right Motor**: `IN3` = Pin 22, `IN4` = Pin 23
* **Ultrasonic**: `Trigger` = Pin 24, `Echo` = Pin 25

---

## Setup & Running the Code

### 1. Desk Test / Standalone Web Control
To test the web remote control console locally on a PC or laptop (using simulated keyboard driving signals and default webcam input):
```bash
# Install dependencies
pip install Flask opencv-python numpy

# Start the local server
python app.py
```
Open `http://localhost:5000` in your web browser. You can drive the mock robot using the UI buttons or keyboard **W A S D** controls.

### 2. Standalone Webcam Tracking
To test the OpenCV line-tracking and centroid offset calculations directly:
```bash
python vision_node.py --standalone
```

### 3. Student Submissions
To run the individual student assignment control terminals, navigate to their respective subfolders in `documents/` and follow their README setups:
* **Visual Inspection**: Runs on port `5000` (`python documents/visual_inspection_robot/run.py`)
* **Color Seeker**: Runs on port `5001` (`python documents/color_seeker_robot/run.py`)
