# Pi-Car: Autonomous Robotics Project (2026)

This repository contains the codebase and deliverables for the two-wheeled differential drive robot car project, developed as part of the school robotics curriculum. 

The project consists of two independent student submissions sharing the same hardware chassis:
1. **Color Target Seeker Robot** (Zadanie 3) – Rotational search scans, OpenCV hue thresholding, and distance proximity stopping at 10cm.
2. **Visual Inspection Robot** (Zadanie 19) – Autonomous guide line tracking and checkpoint-triggered target camera inspections.

---

## Repository Structure

```
Pi-Car/
├── app.py                     # Main Flask server running on the physical robot
├── vision_node.py             # OpenCV line-tracking and marker detection node (ROS2 compatible)
├── templates/                 # Global UI templates for physical robot desk test control
│   └── index.html
├── scripts/
│   └── test_morph.py          # Auxiliary morphology calibration tool
├── systemd/
│   └── pi-car.service         # Systemd service deployment file for the Raspberry Pi
└── student_submissions/       # Independent project submissions for each assignment
    ├── visual_inspection_robot/  # Deliverables folder for Zadanie 19 (Visual Inspection)
    │   ├── app/                  # Flask package (models, forms, routes, templates, assets)
    │   ├── camera_node.py        # ROS2 camera publisher node
    │   ├── sensor_node.py        # ROS2 encoder & bumper publisher node
    │   ├── input_system.md       # Input layer documentation & safety report
    │   ├── use_case.md           # UML Use Case Diagram
    │   └── README.md             # Subsystem running instructions (port 5000)
    │
    └── color_seeker_robot/       # Deliverables folder for Zadanie 3 (Color Seeker)
        ├── app/                  # Flask package (cyberpunk styling, routes, templates)
        ├── camera_node.py        # ROS2 camera publisher node
        ├── sensor_node.py        # ROS2 distance & yaw publisher node
        ├── input_system.md       # Target isolation details & safety report
        ├── use_case.md           # UML Use Case Diagram
        └── README.md             # Subsystem running instructions (port 5001)
```

---

## Hardware Configuration (BOM)

| Component | Quantity | Model / Specification | Purpose |
| :--- | :--- | :--- | :--- |
| **Controller** | 1 | Raspberry Pi 4B | Running headless Ubuntu Desktop environment |
| **Drive Motors** | 2 | 5V DC Gear Motors | Differential wheel propulsion |
| **Motor Driver** | 1 | L298N H-Bridge | Motor voltage and direction regulation |
| **Camera Sensor**| 1 | USB Webcam | Guidelines tracking and target frames capture |
| **Range Sensor**  | 1 | HC-SR04 Ultrasonic | Obstacle distance estimation |
| **Motion Sensor** | 1 | MPU6050 Gyro/IMU | Angular heading and rotation tracking |

### BCM GPIO Pin Mappings
* **Left Motor control**: `IN1` = Pin 17, `IN2` = Pin 27
* **Right Motor control**: `IN3` = Pin 22, `IN4` = Pin 23
* **Ultrasonic Distance Sensor**: `Trigger` = Pin 24, `Echo` = Pin 25

---

## Operation & Execution Guide

### 1. Manual Desk Testing (Simulated Mode)
For local evaluation on a PC or laptop without connection to the physical GPIO hardware, a simulated execution is provided. The keyboard driving keys (**W, A, S, D**) and default webcam feed are processed locally.

* **Dependency Installation**:
  ```bash
  pip install Flask opencv-python numpy
  ```
* **Starting the Server**:
  ```bash
  python app.py
  ```
  The control panel is accessible by navigating to `http://localhost:5000` via web browser.

### 2. Standalone Computer Vision Calibration
Centroid offset algorithms and line threshold parameters can be evaluated using a local webcam by initiating the standalone tracking node:
```bash
python vision_node.py --standalone
```

### 3. Executing Student Subsystem Consoles
The individual submissions are designed to execute independently on separate ports to avoid resource collisions. Running instructions are located in the respective subfolders under `student_submissions/`:
* **Visual Inspection Subsystem** (Zadanie 19): Configured to execute on port `5000` (`python student_submissions/visual_inspection_robot/run.py`).
* **Color Seeker Subsystem** (Zadanie 3): Configured to execute on port `5001` (`python student_submissions/color_seeker_robot/run.py`).
