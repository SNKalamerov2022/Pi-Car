import os
import sys
import time
import datetime
import random
import sqlite3
import subprocess
import threading
import queue
from flask import Flask, render_template, jsonify, request, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import cv2
import numpy as np

# Import the vision processing logic from our other file
try:
    from vision_node import process_frame, reset_crossbar_calibration, is_tracker_active
except ImportError:
    print("WARNING: Could not import vision_node. Make sure it is in the same directory.")
    def process_frame(frame, is_running=False, is_mock=False, click_coords=None, mode="line", target_color=None):
        return frame, 0.0, None, False, -1, -1
    def reset_crossbar_calibration(force=False):
        pass
    def is_tracker_active():
        return False


# Import RPi.GPIO or mock it if running on a development PC (Windows)
try:
    import RPi.GPIO as GPIO
    is_pi = True
except ImportError:
    is_pi = False
    print("WARNING: RPi.GPIO not detected. Running in MOCK mode for development/testing.")
    
    class MockGPIO:
        BCM = 11
        OUT = 3
        LOW = 0
        HIGH = 1
        def setmode(self, mode): pass
        def setup(self, pin, mode): pass
        def output(self, pin, state): pass
        def cleanup(self): pass
    GPIO = MockGPIO()

# Flask setup
app = Flask(__name__)
app.secret_key = 'pi_car_visual_inspection_secret_2026'

# Database configuration
DATABASE = 'pi_car.db'
INSPECTIONS_DIR = os.path.join('static', 'inspections')
os.makedirs(INSPECTIONS_DIR, exist_ok=True)

def get_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    cursor = db.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    # Missions list table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            max_speed INTEGER DEFAULT 50,
            num_checkpoints INTEGER DEFAULT 3
        )
    ''')
    
    # Mission History table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mission_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT UNIQUE NOT NULL,
            mission_name TEXT NOT NULL,
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT NOT NULL
        )
    ''')
    
    # Captured Inspections table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inspections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            checkpoint_id INTEGER NOT NULL,
            image_path TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT NOT NULL,
            notes TEXT
        )
    ''')
    
    # Robot log table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS robot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            message TEXT NOT NULL
        )
    ''')
    
    # Clear and seed default missions (Presets)
    cursor.execute('DELETE FROM missions')
    default_missions = [
        ("Preset 1 - Single Object", "Track path, drive for 2.5s on object detection, photo, then stop.", 40, 1),
        ("Preset 2 - Dual Object", "First target 2.5s, photo, turn left, drive 1.0s, photo, then stop.", 40, 2)
    ]
    for name, desc, speed, cp in default_missions:
        try:
            cursor.execute('INSERT INTO missions (name, description, max_speed, num_checkpoints) VALUES (?, ?, ?, ?)', 
                           (name, desc, speed, cp))
        except sqlite3.IntegrityError:
            pass
            
    db.commit()
    db.close()

# Activity logging setup (in-memory circular list + db log helper)
activity_logs = []

def log_event(message, run_id=None):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    activity_logs.append(log_line)
    if len(activity_logs) > 100:
        activity_logs.pop(0)
    print(log_line)
    
    # Write to database only if this log is associated with an active run
    if run_id is not None:
        try:
            db = get_db()
            db.execute('INSERT INTO robot_logs (run_id, message) VALUES (?, ?)', (run_id, message))
            db.commit()
            db.close()
        except Exception as e:
            print(f"Error logging to DB: {e}")


# GPIO Motor Pins Definition
IN1, IN2, IN3, IN4 = 17, 27, 22, 23

def init_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(IN1, GPIO.OUT)
    GPIO.setup(IN2, GPIO.OUT)
    GPIO.setup(IN3, GPIO.OUT)
    GPIO.setup(IN4, GPIO.OUT)
    stop_motors()
    log_event("GPIO configurations initialized successfully.")

# Stateful motor control to prevent duplicate command prints
current_motor_state = "stop"

def set_motor_state(state):
    global current_motor_state
    if state == current_motor_state:
        return
        
    current_motor_state = state
    if state == "stop":
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.LOW)
        log_event("Motors: STOP")
    elif state == "forward":
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)
        log_event("Motors: FORWARD")
    elif state == "backward":
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)
        log_event("Motors: BACKWARD")
    elif state == "left":
        # Normal left turn (swapped to fix hardware inversion)
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.HIGH)
        log_event("Motors: PIVOT LEFT")
    elif state == "right":
        # Normal right turn (swapped to fix hardware inversion)
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.HIGH)
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)
        log_event("Motors: PIVOT RIGHT")
    elif state == "gentle_left":
        # Gentle left (left wheel forward, right stops - swapped to fix hardware inversion)
        GPIO.output(IN1, GPIO.HIGH)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.LOW)
        GPIO.output(IN4, GPIO.LOW)
        log_event("Motors: GENTLE LEFT")
    elif state == "gentle_right":
        # Gentle right (right wheel forward, left stops - swapped to fix hardware inversion)
        GPIO.output(IN1, GPIO.LOW)
        GPIO.output(IN2, GPIO.LOW)
        GPIO.output(IN3, GPIO.HIGH)
        GPIO.output(IN4, GPIO.LOW)
        log_event("Motors: GENTLE RIGHT")


def stop_motors(): set_motor_state("stop")
def move_forward(): set_motor_state("forward")
def move_backward(): set_motor_state("backward")
def turn_left(): set_motor_state("left")
def turn_right(): set_motor_state("right")

# Initialize DB and GPIO on start
init_db()
init_gpio()

# ----------------------------------------------------
# ROS2 Mock Node Architecture (Threads & Queues)
# ----------------------------------------------------

# Mock ROS2 Topics (Thread-safe queues)
# Queues hold latest data and drop old data to mimic ROS2 real-time topics
class ROS2Topic:
    def __init__(self, name):
        self.name = name
        self.lock = threading.Lock()
        self.msg = None
        
    def publish(self, msg):
        with self.lock:
            self.msg = msg
            
    def read(self):
        with self.lock:
            return self.msg

# ROS2 Topics
topic_camera_raw = ROS2Topic('/camera/image_raw')
topic_line_error = ROS2Topic('/vision/line_error')
topic_marker_detected = ROS2Topic('/vision/marker_detected')
topic_cmd_vel = ROS2Topic('/cmd_vel')
topic_tracker_init = ROS2Topic('/vision/tracker_init')

# Global state managers
latest_frame = None
latest_mask = None
camera_lock = threading.Lock()

# Autonomous Mission Parameters
active_run_id = None
mission_state = "IDLE"          # IDLE, RUNNING, INSPECTION, COMPLETED, ABORTED, MANUAL
inspection_substate = None
target_checkpoints = 3
checkpoints_visited = 0
active_mission_name = "None"
is_mock_sensor_mode = False     # Toggle to simulate markers on desk
active_mode = "line"            # "line" or "color"
selected_color = "red"          # "red", "green", "blue", "yellow"

# Multi-Target click list
clicked_targets = []

# Approach phase timers & flags
approaching_checkpoint = False
checkpoint_approach_start = 0.0
approaching_color = False
color_approach_start_time = 0.0
dual_object_phase = None
dual_object_phase_start = 0.0

# Approach duration configurations
APPROACH_DURATION = 0.5 #Seconds to drive towards the line obstacle (~30 cm)
COLOR_APPROACH_DURATION = 2.0  # Seconds to drive towards the color target



# Helper function to capture a clean frame and save it to the inspection database
def capture_inspection_photo(checkpoint_num):
    global latest_frame, active_run_id
    with camera_lock:
        if latest_frame is not None:
            frame_to_save = latest_frame.copy()
        else:
            # Create a fallback frame
            frame_to_save = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame_to_save, f"CHECKPOINT {checkpoint_num} - INSPECTION FAIL", 
                        (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
    filename = f"checkpoint_{active_run_id}_{checkpoint_num}.jpg"
    filepath = os.path.join(INSPECTIONS_DIR, filename)
    cv2.imwrite(os.path.join('static', 'inspections', filename), frame_to_save)
    
    # Save to SQLite database
    try:
        db = get_db()
        db.execute('''
            INSERT INTO inspections (run_id, checkpoint_id, image_path, status, notes) 
            VALUES (?, ?, ?, ?, ?)
        ''', (active_run_id, checkpoint_num, f"/static/inspections/{filename}", "OK", f"Automated inspection at checkpoint {checkpoint_num} completed successfully."))
        db.commit()
        db.close()
    except Exception as e:
        log_event(f"Database error saving checkpoint image: {e}", active_run_id)

# 1. Camera Node (Publishes camera frames to topic_camera_raw)
# PERFORMANCE: Reduced resolution to 320x240, increased frame interval
def camera_node():
    global latest_frame
    log_event("ROS2 Node [camera_node] starting...")
    camera = None
    
    # Try opening camera indices
    for idx in [0, -1]:
        try:
            temp_cam = cv2.VideoCapture(idx)
            if temp_cam.isOpened():
                camera = temp_cam
                log_event(f"ROS2 Node [camera_node] successfully connected to camera (index: {idx}).")
                break
        except Exception:
            pass
            
    if camera is None or not camera.isOpened():
        log_event("ROS2 Node [camera_node] ERROR: Camera hardware not found. Running in image mock mode.")
        # Setup dummy frame stream
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        dummy_frame[:, :, 0] = 50 # Dark blue background
        
        # Add visual tracks for test
        cv2.rectangle(dummy_frame, (280, 280), (360, 480), (40, 40, 40), -1) # Line
        cv2.putText(dummy_frame, "MOCK TRACK FEED", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 240, 255), 2)
        
        while True:
            frame_copy = dummy_frame.copy()
            now_str = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-4]
            cv2.putText(frame_copy, f"TIME: {now_str}", (50, 430), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            
            with camera_lock:
                latest_frame = frame_copy
            topic_camera_raw.publish(frame_copy)
            time.sleep(0.1)
            
    # Original resolution, with buffer optimization to reduce latency
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 15)
    # Reduce camera buffer so we always grab the latest frame
    camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    while True:
        success, frame = camera.read()
        if not success or frame is None:
            time.sleep(0.03)
            continue
            
        topic_camera_raw.publish(frame)
        time.sleep(0.08)

# 2. Vision Node (Subscribes to topic_camera_raw, publishes to line_error and marker_detected)
# PERFORMANCE: Only run vision when mission is RUNNING; otherwise skip heavy CV work
def vision_node():
    global latest_frame, latest_mask, active_mode, selected_color
    log_event("ROS2 Node [vision_node] starting...")
    frame_counter = 0
    while True:
        frame = topic_camera_raw.read()
        if frame is None:
            time.sleep(0.05)
            continue
        
        frame_counter += 1
        
        # Check for new tracker initialization clicks
        click_coords = topic_tracker_init.read()
        if click_coords is not None:
            topic_tracker_init.publish(None)
        
        # Run vision pipeline with active mode and selected color
        processed_frame, error, thresholded, marker_detected, bm_y_max, bm_y_min = process_frame(
            frame, 
            is_running=(mission_state == "RUNNING"),
            click_coords=click_coords,
            mode=active_mode,
            target_color=selected_color
        )
        
        with camera_lock:
            latest_frame = processed_frame
            if thresholded is not None:
                latest_mask = cv2.cvtColor(thresholded, cv2.COLOR_GRAY2BGR)
            else:
                latest_mask = None
            
        topic_line_error.publish(error)
        topic_marker_detected.publish((marker_detected, bm_y_max, bm_y_min))
        
        time.sleep(0.08)


# 3. Mission Node (Handles visual inspection state-machine & photo timing)
def mission_node_worker():
    global mission_state, checkpoints_visited, target_checkpoints, active_run_id, active_mission_name, is_mock_sensor_mode, active_mode, selected_color
    log_event("ROS2 Node [mission_node] starting...")
    
    last_mission_state = "IDLE"
    drive_start_time = 0.0
    
    while True:
        if mission_state == "PRE_START":
            log_event(f"Starting simplified timed drive mission: {active_mission_name} in mode: {active_mode}", active_run_id)
            mission_state = "RUNNING"
            drive_start_time = time.time()
            topic_cmd_vel.publish("forward")
            last_mission_state = "PRE_START"
            time.sleep(0.1)
            continue
            
        if mission_state == "RUNNING":
            if last_mission_state != "RUNNING":
                # Ensure we reset start time if state was changed elsewhere to RUNNING
                drive_start_time = time.time()
                topic_cmd_vel.publish("forward")
                log_event(f"Mission state transitioned to RUNNING. Mode: {active_mode}. Driving forward.", active_run_id)
            
            last_mission_state = "RUNNING"
            
            # Keep commanding forward to keep motors rotating
            topic_cmd_vel.publish("forward")
            
            # Determine target duration based on mode
            target_duration = 1.0 if active_mode == "color" else 2.0
            
            elapsed = time.time() - drive_start_time
            if elapsed >= target_duration:
                log_event(f"{target_duration} seconds elapsed for mode {active_mode}. Stopping robot...", active_run_id)
                topic_cmd_vel.publish("stop")
                time.sleep(1.0)
                
                # Capture verification photo (Checkpoint 1)
                checkpoints_visited = 1
                capture_inspection_photo(1)
                log_event("Verification image captured.", active_run_id)
                
                mission_state = "COMPLETED"
                log_event("Mission complete!", active_run_id)
                
                # Update database run entry
                try:
                    db = get_db()
                    db.execute('UPDATE mission_history SET end_time = CURRENT_TIMESTAMP, status = ? WHERE run_id = ?', 
                               ("COMPLETED", active_run_id))
                    db.commit()
                    db.close()
                except Exception as e:
                    print(f"Error updating DB: {e}")
        else:
            last_mission_state = mission_state
            if mission_state in ["COMPLETED", "ABORTED"]:
                topic_cmd_vel.publish("stop")
                time.sleep(0.5)
            
        time.sleep(0.1)


# 4. Control Node (Processes line error and publishes commands to topic_cmd_vel)
def control_node():
    log_event("ROS2 Node [control_node] starting...")
    while True:
        # Dormant/disabled for the simplified timed drive
        time.sleep(0.5)


# 5. Motor Node (Listens to topic_cmd_vel and writes to GPIO)
# PERFORMANCE: Faster polling = lower command latency
def motor_node_worker():
    log_event("ROS2 Node [motor_node] starting...")
    while True:
        cmd = topic_cmd_vel.read()
        if cmd:
            set_motor_state(cmd)
        time.sleep(0.02)

# Initialize background mock-ROS2 threads
t_cam = threading.Thread(target=camera_node, daemon=True)
t_vis = threading.Thread(target=vision_node, daemon=True)
t_mis = threading.Thread(target=mission_node_worker, daemon=True)
t_con = threading.Thread(target=control_node, daemon=True)
t_mot = threading.Thread(target=motor_node_worker, daemon=True)

t_cam.start()
t_vis.start()
t_mis.start()
t_con.start()
t_mot.start()

# ----------------------------------------------------
# User Authentication Helpers & Filters
# ----------------------------------------------------
def login_required(f):
    import functools
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------------------------------------------
# Web Application Routing (HTTP Server)
# ----------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            return render_template('register.html', error="Username and password are required.")
            
        db = get_db()
        cursor = db.cursor()
        
        # Check if username exists
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        if cursor.fetchone():
            db.close()
            return render_template('register.html', error="Username already registered.")
            
        # Hash password and insert
        hashed = generate_password_hash(password)
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, hashed))
        db.commit()
        db.close()
        
        return render_template('register.html', success="Registration successful! You may log in now.")
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        db.close()
        
        if row and check_password_hash(row['password_hash'], password):
            session['username'] = username
            log_event(f"Terminal authorized: operator '{username}' logged in.")
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid operator ID or security key.")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.pop('username', None)
    if username:
        log_event(f"Terminal de-authorized: operator '{username}' logged out.")
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    return render_template('index.html')

# Video streaming route
# PERFORMANCE: Lower JPEG quality (50%), longer frame interval (100ms = ~10fps)
@app.route('/video_feed')
def video_feed():
    feed_type = request.args.get('type', 'processed')
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 50]
    def generate_frames():
        global latest_frame, latest_mask
        while True:
            with camera_lock:
                if feed_type == 'mask':
                    frame_to_send = latest_mask
                else:
                    frame_to_send = latest_frame
            if frame_to_send is not None:
                ret, buffer = cv2.imencode('.jpg', frame_to_send, encode_params)
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(0.1)
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/control', methods=['POST'])
@login_required
def control_robot():
    global mission_state
    if mission_state == "RUNNING" or mission_state == "INSPECTION":
        return jsonify({
            "status": "error",
            "message": "Manual override locked during autonomous mission execution."
        }), 400
        
    data = request.get_json()
    action = data.get('action', 'stop').lower()
    
    # Transition out of ABORTED or COMPLETED when manual input is received
    if action != 'stop':
        mission_state = "MANUAL"
    else:
        mission_state = "IDLE"
        
    topic_cmd_vel.publish(action)
    return jsonify({
        "status": "success",
        "action": action,
        "message": f"Command {action.upper()} published to /cmd_vel."
    })

# System Stats Helpers
start_time = time.time()

def get_wifi_signal():
    try:
        with open("/proc/net/wireless", "r") as f:
            lines = f.readlines()
            if len(lines) > 2:
                parts = lines[2].split()
                if len(parts) > 3:
                    level = int(float(parts[3].replace('.', '')))
                    return level
    except Exception:
        pass
    return random.randint(-48, -42)

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = float(f.read().strip()) / 1000.0
            return round(temp, 1)
    except Exception:
        return 43.5

def get_uptime_str():
    elapsed = int(time.time() - start_time)
    hours = elapsed // 3600
    minutes = (elapsed % 3600) // 60
    seconds = elapsed % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

@app.route('/api/stats')
@login_required
def api_stats():
    global mission_state, checkpoints_visited, target_checkpoints, active_mission_name, active_mode, selected_color, current_motor_state, inspection_substate
    cam_status = "OK" if latest_frame is not None else "OFFLINE"
    joy_status = "OK" if os.path.exists('/dev/input/js0') else "DISCONNECTED"
    
    # Read target detection status for telemetry feedback
    marker_data = topic_marker_detected.read()
    target_visible = False
    bm_y_max = -1
    bm_y_min = -1
    if isinstance(marker_data, tuple) and len(marker_data) == 3:
        target_visible, bm_y_max, bm_y_min = marker_data
    
    # Map mission state to user-friendly strings for Zadanie 19
    friendly_state = mission_state
    if mission_state == "IDLE":
        friendly_state = "WAITING"
    elif mission_state == "PRE_START":
        friendly_state = "WAITING"
    elif mission_state == "MANUAL":
        friendly_state = "MANUAL CONTROL"
    elif mission_state == "RUNNING":
        # Check if we are detecting a marker right now
        raw_marker = False
        if active_mode == "color":
            raw_marker = target_visible
        else:
            if isinstance(marker_data, tuple) and len(marker_data) == 3:
                raw_marker = marker_data[0]
            elif marker_data:
                raw_marker = bool(marker_data)
        
        if raw_marker:
            friendly_state = "DETECTING MARKER"
        else:
            friendly_state = "FOLLOWING ROUTE"
    elif mission_state == "INSPECTION":
        friendly_state = inspection_substate or "STOPPED FOR INSPECTION"
    elif mission_state == "COMPLETED":
        friendly_state = "COMPLETED"
    elif mission_state == "ABORTED":
        friendly_state = "ERROR STATE"

    return jsonify({
        "wifi": get_wifi_signal(),
        "temp": get_cpu_temp(),
        "uptime": get_uptime_str(),
        "camera_status": cam_status,
        "joystick_status": joy_status,
        "motors_status": "OK" if is_pi else "MOCK_MODE",
        "mission_state": friendly_state,
        "checkpoints_visited": checkpoints_visited,
        "target_checkpoints": target_checkpoints,
        "active_mission": active_mission_name,
        "is_mock_sensor": is_mock_sensor_mode,
        "active_mode": active_mode,
        "selected_color": selected_color,
        "target_visible": target_visible,
        "target_height": (bm_y_max - bm_y_min) if target_visible else 0,
        "current_action": current_motor_state
    })


@app.route('/api/logs')
@login_required
def api_logs():
    return jsonify({
        "logs": activity_logs
    })

# ----------------------------------------------------
# Mission Execution Control APIs
# ----------------------------------------------------

@app.route('/api/missions/list')
@login_required
def api_missions_list():
    db = get_db()
    rows = db.execute('SELECT * FROM missions').fetchall()
    db.close()
    missions_list = [dict(r) for r in rows]
    return jsonify({
        "missions": missions_list
    })

@app.route('/api/mission/start', methods=['POST'])
@login_required
def api_mission_start():
    global mission_state, checkpoints_visited, target_checkpoints, active_run_id, active_mission_name, is_mock_sensor_mode, active_mode, selected_color
    
    data = request.get_json() or {}
    mode = data.get('mode', 'line')
    target_color = data.get('target_color', 'red')
    
    if mode == 'color':
        active_mode = 'color'
        selected_color = target_color
        active_mission_name = f"Color Search - {target_color.upper()}"
        target_checkpoints = 1
        checkpoints_visited = 0
        is_mock_sensor_mode = False
    else:
        active_mode = 'line'
        mission_id = data.get('mission_id')
        mock_sensor = bool(data.get('mock_sensor', False))
        
        db = get_db()
        mission = db.execute('SELECT * FROM missions WHERE id = ?', (mission_id,)).fetchone()
        
        if not mission:
            db.close()
            return jsonify({"status": "error", "message": "Mission ID not found."}), 404
            
        if is_tracker_active():
            active_mission_name = "Target-Click Inspection"
            target_checkpoints = 1
            checkpoints_visited = 0
            is_mock_sensor_mode = False
        else:
            active_mission_name = mission['name']
            target_checkpoints = mission['num_checkpoints']
            checkpoints_visited = 0
            is_mock_sensor_mode = mock_sensor
        db.close()
    
    # Generate run ID
    active_run_id = f"RUN_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Log mission history record
    db = get_db()
    db.execute('''
        INSERT INTO mission_history (run_id, mission_name, status) 
        VALUES (?, ?, ?)
    ''', (active_run_id, active_mission_name, "RUNNING"))
    db.commit()
    db.close()
    
    log_event(f"Visual Inspection mission [{active_mission_name}] started by user '{session.get('username')}' in mode '{active_mode}'.", active_run_id)
    global clicked_targets, approaching_checkpoint, approaching_color, dual_object_phase
    clicked_targets = []
    topic_tracker_init.publish([])
    approaching_checkpoint = False
    approaching_color = False
    dual_object_phase = None
    reset_crossbar_calibration()
    log_event("Vision crossbar calibration history cleared.", active_run_id)
    mission_state = "PRE_START"
    topic_cmd_vel.publish("stop")
    
    return jsonify({
        "status": "success",
        "run_id": active_run_id,
        "mission_name": active_mission_name,
        "target_checkpoints": target_checkpoints
    })


@app.route('/api/mission/stop', methods=['POST'])
@login_required
def api_mission_stop():
    global mission_state, active_run_id
    if mission_state == "IDLE":
        return jsonify({"status": "error", "message": "No active mission to halt."}), 400
        
    log_event("EMERGENCY STOP (E-Stop) triggered! Autonomous path follower halted.", active_run_id)
    mission_state = "ABORTED"
    topic_cmd_vel.publish("stop")
    
    # Update mission status in DB
    try:
        db = get_db()
        db.execute('UPDATE mission_history SET end_time = CURRENT_TIMESTAMP, status = ? WHERE run_id = ?', 
                   ("ABORTED", active_run_id))
        db.commit()
        db.close()
    except Exception as e:
        print(e)
        
    return jsonify({
        "status": "success",
        "message": "Emergency Stop processed. Autonomous execution aborted."
    })

@app.route('/api/set_mode', methods=['POST'])
@login_required
def api_set_mode():
    global active_mode, mission_state
    if mission_state in ["RUNNING", "INSPECTION", "PRE_START"]:
        return jsonify({"status": "error", "message": "Cannot switch modes during an active mission."}), 400
        
    data = request.get_json() or {}
    mode = data.get('mode', 'line')
    if mode in ['line', 'color']:
        active_mode = mode
        log_event(f"Vision active mode set to: {mode.upper()}")
        return jsonify({"status": "success", "mode": active_mode})
    return jsonify({"status": "error", "message": "Invalid mode specified."}), 400

@app.route('/api/track_init', methods=['POST'])
@login_required
def api_track_init():
    global clicked_targets
    data = request.json
    x = data.get('x')
    y = data.get('y')
    if x is not None and y is not None:
        clicked_targets.append((int(x), int(y)))
        if len(clicked_targets) > 2:
            clicked_targets.pop(0)
        topic_tracker_init.publish(list(clicked_targets))
        log_event(f"Vision System: Click-to-Track target added at ({x}, {y}). Total marked: {len(clicked_targets)}/2")
        return jsonify({"status": "success", "targets_count": len(clicked_targets)})
    return jsonify({"status": "error", "message": "Invalid coordinates"}), 400

@app.route('/api/track_clear', methods=['POST'])
@login_required
def api_track_clear():
    global clicked_targets
    clicked_targets = []
    topic_tracker_init.publish([])
    reset_crossbar_calibration(force=True)
    log_event("Vision System: Click-to-Track cleared by operator.")
    return jsonify({"status": "success"})

@app.route('/api/mission/history')
@login_required
def api_mission_history():
    db = get_db()
    # Fetch recent runs
    runs = db.execute('SELECT * FROM mission_history ORDER BY start_time DESC LIMIT 10').fetchall()
    # Fetch captured inspections
    inspections = db.execute('SELECT * FROM inspections ORDER BY timestamp DESC LIMIT 20').fetchall()
    db.close()
    
    return jsonify({
        "runs": [dict(r) for r in runs],
        "inspections": [dict(i) for i in inspections]
    })

# ----------------------------------------------------
# WiFi Network Management APIs (nmcli wrapper)
# ----------------------------------------------------

@app.route('/api/wifi/status')
@login_required
def api_wifi_status():
    """Return current WiFi connection status: SSID, signal, IP address."""
    if not is_pi:
        return jsonify({
            "connected": True,
            "ssid": "MockNetwork",
            "signal": 72,
            "ip": "192.168.0.99",
            "mac": "AA:BB:CC:DD:EE:FF"
        })
    try:
        # Get active WiFi connection name
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'NAME,TYPE,DEVICE', 'con', 'show', '--active'],
            capture_output=True, text=True, timeout=10
        )
        ssid = None
        for line in result.stdout.strip().split('\n'):
            parts = line.split(':')
            if len(parts) >= 3 and parts[1] == '802-11-wireless' and parts[2]:
                ssid = parts[0]
                break

        if not ssid:
            return jsonify({"connected": False, "ssid": None, "signal": 0, "ip": None, "mac": None})

        # Get signal strength
        signal = 0
        sig_result = subprocess.run(
            ['nmcli', '-t', '-f', 'SIGNAL,IN-USE', 'dev', 'wifi', 'list'],
            capture_output=True, text=True, timeout=10
        )
        for line in sig_result.stdout.strip().split('\n'):
            parts = line.split(':')
            if len(parts) >= 2 and parts[1].strip() == '*':
                try:
                    signal = int(parts[0])
                except ValueError:
                    pass
                break

        # Get IP address from wlan0
        ip_addr = None
        mac_addr = None
        ip_result = subprocess.run(
            ['ip', '-4', '-o', 'addr', 'show', 'wlan0'],
            capture_output=True, text=True, timeout=5
        )
        if ip_result.stdout.strip():
            for part in ip_result.stdout.split():
                if '/' in part and '.' in part:
                    ip_addr = part.split('/')[0]
                    break

        mac_result = subprocess.run(
            ['cat', '/sys/class/net/wlan0/address'],
            capture_output=True, text=True, timeout=5
        )
        mac_addr = mac_result.stdout.strip() or None

        return jsonify({
            "connected": True,
            "ssid": ssid,
            "signal": signal,
            "ip": ip_addr,
            "mac": mac_addr
        })
    except Exception as e:
        log_event(f"WiFi status check error: {e}")
        return jsonify({"connected": False, "ssid": None, "signal": 0, "ip": None, "mac": None, "error": str(e)})


@app.route('/api/wifi/scan')
@login_required
def api_wifi_scan():
    """Scan for available WiFi networks."""
    if not is_pi:
        return jsonify({"networks": [
            {"ssid": "MockNetwork", "signal": 72, "security": "WPA2", "in_use": True},
            {"ssid": "Neighbor_5G", "signal": 45, "security": "WPA2", "in_use": False},
            {"ssid": "FreeWiFi", "signal": 30, "security": "Open", "in_use": False}
        ]})
    try:
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'dev', 'wifi', 'list', '--rescan', 'yes'],
            capture_output=True, text=True, timeout=20
        )
        networks = []
        seen_ssids = set()
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split(':')
            if len(parts) >= 4:
                ssid = parts[0].strip()
                if not ssid or ssid in seen_ssids:
                    continue
                seen_ssids.add(ssid)
                try:
                    signal = int(parts[1])
                except ValueError:
                    signal = 0
                security = parts[2] if parts[2] else 'Open'
                in_use = parts[3].strip() == '*'
                networks.append({
                    "ssid": ssid,
                    "signal": signal,
                    "security": security,
                    "in_use": in_use
                })
        # Sort by signal strength descending
        networks.sort(key=lambda x: x['signal'], reverse=True)
        return jsonify({"networks": networks})
    except Exception as e:
        log_event(f"WiFi scan error: {e}")
        return jsonify({"networks": [], "error": str(e)})


@app.route('/api/wifi/saved')
@login_required
def api_wifi_saved():
    """List all saved WiFi connections."""
    if not is_pi:
        return jsonify({"connections": [
            {"name": "MockNetwork", "autoconnect": True, "active": True},
            {"name": "OtherNetwork", "autoconnect": True, "active": False}
        ]})
    try:
        # Get all saved WiFi connections
        result = subprocess.run(
            ['nmcli', '-t', '-f', 'NAME,TYPE,AUTOCONNECT', 'con', 'show'],
            capture_output=True, text=True, timeout=10
        )
        # Get active connection name
        active_result = subprocess.run(
            ['nmcli', '-t', '-f', 'NAME,TYPE,DEVICE', 'con', 'show', '--active'],
            capture_output=True, text=True, timeout=10
        )
        active_names = set()
        for line in active_result.stdout.strip().split('\n'):
            parts = line.split(':')
            if len(parts) >= 3 and parts[1] == '802-11-wireless' and parts[2]:
                active_names.add(parts[0])

        connections = []
        for line in result.stdout.strip().split('\n'):
            parts = line.split(':')
            if len(parts) >= 3 and parts[1] == '802-11-wireless':
                name = parts[0]
                autoconnect = parts[2].lower() == 'yes'
                connections.append({
                    "name": name,
                    "autoconnect": autoconnect,
                    "active": name in active_names
                })
        return jsonify({"connections": connections})
    except Exception as e:
        log_event(f"WiFi saved list error: {e}")
        return jsonify({"connections": [], "error": str(e)})


@app.route('/api/wifi/connect', methods=['POST'])
@login_required
def api_wifi_connect():
    """Connect to a saved network by name, or add a new network with SSID+password."""
    data = request.get_json() or {}
    ssid = data.get('ssid', '').strip()
    password = data.get('password', '').strip()

    if not ssid:
        return jsonify({"status": "error", "message": "SSID is required."}), 400

    if not is_pi:
        log_event(f"WiFi: Mock connect to '{ssid}'")
        return jsonify({"status": "success", "message": f"Mock connected to {ssid}"})

    try:
        # Check if this is already a saved connection
        check = subprocess.run(
            ['nmcli', '-t', '-f', 'NAME,TYPE', 'con', 'show'],
            capture_output=True, text=True, timeout=10
        )
        saved_names = []
        for line in check.stdout.strip().split('\n'):
            parts = line.split(':')
            if len(parts) >= 2 and parts[1] == '802-11-wireless':
                saved_names.append(parts[0])

        if ssid in saved_names and not password:
            # Switch to existing saved connection
            result = subprocess.run(
                ['nmcli', 'con', 'up', ssid],
                capture_output=True, text=True, timeout=30
            )
        else:
            # Add new network or reconnect with new password
            cmd = ['nmcli', 'dev', 'wifi', 'connect', ssid]
            if password:
                cmd += ['password', password]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )

        if result.returncode == 0:
            log_event(f"WiFi: Successfully connected to '{ssid}'")
            return jsonify({"status": "success", "message": f"Connected to {ssid}"})
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            log_event(f"WiFi: Failed to connect to '{ssid}': {error_msg}")
            return jsonify({"status": "error", "message": error_msg}), 500
    except subprocess.TimeoutExpired:
        return jsonify({"status": "error", "message": "Connection attempt timed out."}), 504
    except Exception as e:
        log_event(f"WiFi connect error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/wifi/forget', methods=['POST'])
@login_required
def api_wifi_forget():
    """Remove a saved WiFi network by connection name."""
    data = request.get_json() or {}
    name = data.get('name', '').strip()

    if not name:
        return jsonify({"status": "error", "message": "Connection name is required."}), 400

    if not is_pi:
        log_event(f"WiFi: Mock forget '{name}'")
        return jsonify({"status": "success", "message": f"Mock removed {name}"})

    try:
        result = subprocess.run(
            ['nmcli', 'con', 'delete', name],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            log_event(f"WiFi: Removed saved network '{name}'")
            return jsonify({"status": "success", "message": f"Removed {name}"})
        else:
            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            log_event(f"WiFi: Failed to remove '{name}': {error_msg}")
            return jsonify({"status": "error", "message": error_msg}), 500
    except Exception as e:
        log_event(f"WiFi forget error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# Cleanup GPIO when server stops
def shutdown():
    print("Cleaning up GPIO configurations...")
    if is_pi:
        GPIO.cleanup()

# Joystick Controller Background Thread
def joystick_thread():
    log_event("Starting background joystick thread...")
    import struct
    
    EVENT_FORMAT = 'IhBB'
    EVENT_SIZE = struct.calcsize(EVENT_FORMAT)
    
    y_axis = 0
    x_axis = 0
    
    while True:
        try:
            with open('/dev/input/js0', 'rb') as f:
                log_event("Joystick/Gamepad device opened successfully!")
                while True:
                    event = f.read(EVENT_SIZE)
                    if not event:
                        break
                    t, val, ev_type, num = struct.unpack(EVENT_FORMAT, event)
                    clean_type = ev_type & ~0x80 # strip init flag
                    
                    if clean_type == 2: # AXIS event
                        # Left stick vertical (1) or D-pad vertical (7)
                        if num in [1, 7]:
                            y_axis = val
                        # Left stick horizontal (0) or D-pad horizontal (6)
                        elif num in [0, 6]:
                            x_axis = val
                            
                        # If mission is running autonomously, ignore gamepad driving
                        if mission_state == "RUNNING":
                            continue
                            
                        # Determine robot action based on y_axis and x_axis
                        if y_axis < -16000:
                            topic_cmd_vel.publish("forward")
                        elif y_axis > 16000:
                            topic_cmd_vel.publish("backward")
                        elif x_axis < -16000:
                            topic_cmd_vel.publish("left")
                        elif x_axis > 16000:
                            topic_cmd_vel.publish("right")
                        else:
                            topic_cmd_vel.publish("stop")
        except Exception as e:
            time.sleep(2.0)

# Start background joystick thread
jt = threading.Thread(target=joystick_thread, daemon=True)
jt.start()

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        shutdown()
    finally:
        shutdown()
