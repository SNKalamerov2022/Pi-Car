# Color Target Seeker Robot - Flask Web Console

This package implements an organized, modular Flask application that serves as the operator control terminal for the **Color Target Seeker Robot** (Zadanie 3). Features include user authentication, database logging, a cyberpunk-themed scanner dashboard, and placeholder command integrations.

---

## 1. Project Purpose
The console provides high-level monitoring and calibration of the target-seeking vehicle:
* **Operator Session Management**: Restricts control interface privileges to registered users.
* **Target Management**: Configures color hue isolation filters (Red, Green, Blue, Yellow).
* **Telemetry Monitoring**: Renders real-time indicators reflecting the current state (Scanning, Target Spotted, Approaching, Completed, E-Stop).
* **Database Auditing**: Stores timestamps, search history, and detection metrics.

---

## 2. Setup & Execution

### Step 1: Dependency Installation
The execution environment is configured by installing the packages listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Step 2: Database Setup
The SQLite database (`instance/robot_seeker.db`) is initialized and seeded automatically during the initial server start. Manual table creation is not required.

### Step 3: Starting the Server
The Flask application is launched using the entrypoint runner:
```bash
python run.py
```
The interface is hosted locally at `http://localhost:5001/` (configured on port 5001 to prevent conflict with other console systems).

### Step 4: Running Input Nodes
The input camera feed can be tested in standalone or ROS2 environments:
* **Camera Input Node**: Captures frames from default camera index 0 (generates mock target graphics if no camera is detected):
  ```bash
  python camera_node.py
  ```
Detailed telemetry structure and safety checklists are documented in [input_system.md](file:///c:/Users/Simeon/Desktop/Pi-Car/separated_projects/color_seeker_robot/input_system.md).

---

## 3. Telemetry Console Instructions
1. The web browser is directed to `http://localhost:5001/`.
2. A new user is registered via the **Register** panel.
3. Access is granted by entering the credentials on the **Log In** screen.
4. An active target range is configured by navigating to the **Configure Target** menu and clicking **Configure**.
5. Execution is initiated on the **Dashboard** by clicking **START SCANNING**, which simulates rotational search patterns, HSV target lock, Yaw alignment adjustments, and approaching proximity logs.
6. Safety overrides are initiated by clicking the **EMERGENCY STOP (E-STOP)** button.
7. Event logs and previous path runs are reviewed on the **Logs & History** page.

---

## 4. Current Limitations & Future Work
* **ROS2 publishers**: The API endpoints (`/api/start`, `/api/stop`, `/api/estop`) currently log actions to the SQLite database. Future integration will bind these endpoints to publish velocity and state commands directly to ROS2 nodes.
* **OpenCV Tuning**: Real-time calibration parameters for H, S, V filter bounds will be exposed to the web console interface to support ambient classroom lighting adjustments.