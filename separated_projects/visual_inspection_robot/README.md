# Visual Inspection Robot - Flask Web Console

This package implements an organized, modular Flask application that serves as the operator control terminal for the **Visual Inspection Robot** (Zadanie 19). Features include user authentication, database logging, a dashboard displaying path check-ins, and placeholder command integrations.

---

## 1. Project Purpose
The console provides high-level monitoring and configuration of the autonomous vehicle:
* **Operator Session Management**: Restricts control interface privileges to registered users.
* **Path Management**: Configures active search templates (Route Alpha, Route Beta, full loop).
* **Telemetry Monitoring**: Renders real-time indicators reflecting the current state (Following Route, Stopped for Inspection, Completed, E-Stop).
* **Database Auditing**: Stores timestamps, route run history, and inspection images.

---

## 2. Setup & Execution

### Step 1: Dependency Installation
The execution environment is configured by installing the packages listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

### Step 2: Database Setup
The SQLite database (`instance/robot_inspection.db`) is initialized and seeded automatically during the initial server start. Manual table creation is not required.

### Step 3: Starting the Server
The Flask application is launched using the entrypoint runner:
```bash
python run.py
```
The interface is hosted locally at `http://localhost:5000/`.

### Step 4: Running Input Nodes
The input camera feed can be tested in standalone or ROS2 environments:
* **Camera Input Node**: Captures frames from default camera index 0 (generates mock line graphics if no camera is detected):
  ```bash
  python camera_node.py
  ```
Detailed telemetry structure and safety checklists are documented in [input_system.md](file:///c:/Users/Simeon/Desktop/Pi-Car/separated_projects/visual_inspection_robot/input_system.md).

---

## 3. Telemetry Console Instructions
1. The web browser is directed to `http://localhost:5000/`.
2. A new user is registered via the **Register** panel.
3. Access is granted by entering the credentials on the **Log In** screen.
4. An active path is selected by navigating to the **Select Route** menu and clicking **Configure**.
5. Execution is initiated on the **Dashboard** by clicking **START INSPECTION**, which simulates line guide tracking, checkpoint halts, image captures, and log updates.
6. Safety overrides are initiated by clicking the **EMERGENCY STOP (E-STOP)** button.
7. Event logs and previous path runs are reviewed on the **Logs & History** page.

---

## 4. Current Limitations & Future Work
* **ROS2 publishers**: The API endpoints (`/api/start`, `/api/stop`, `/api/estop`) currently log actions to the SQLite database. Future integration will bind these endpoints to publish velocity and state commands directly to ROS2 nodes.
* **Camera Stream**: Real-time camera feeds are simulated. Physical deployment will replace mock frames with actual images subscribed from `camera_node.py` via the `/camera/image_raw` topic.