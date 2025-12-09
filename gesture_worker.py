import cv2
import mediapipe as mp
import numpy as np
import socket
import json
import time
import argparse
import sys
from collections import deque

class IPCClient:
    def __init__(self, port):
        self.port = port
        self.socket = None
        self.connected = False
        self.connect()

    def connect(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('127.0.0.1', self.port))
            self.connected = True
            print(f"Connected to Anki on port {self.port}")
        except Exception as e:
            print(f"Failed to connect to Anki: {e}")
            self.connected = False

    def send(self, data):
        if not self.connected:
            self.connect()
            if not self.connected:
                return

        try:
            message = json.dumps(data) + "\n"
            self.socket.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending data: {e}")
            self.connected = False
            self.socket.close()

    def receive_noblock(self):
        if not self.connected:
            return None
        try:
            self.socket.setblocking(False)
            try:
                data = self.socket.recv(1024)
                if data:
                    return data.decode('utf-8')
            except BlockingIOError:
                pass
            except socket.error:
                pass
            finally:
                self.socket.setblocking(True)
        except Exception:
            pass
        return None

    def close(self):
        if self.socket:
            self.socket.close()

class GestureController:
    def __init__(self, port, config_path="config.json"):
        # IPC Setup
        self.client = IPCClient(port)
        
        # Load configuration
        self.config = self.load_config(config_path)
        
        # MediaPipe setup
        self.mp_face_mesh = mp.solutions.face_mesh
        face_config = self.config.get("mediapipe", {}).get("face_mesh", {})
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=face_config.get("max_num_faces", 1),
            refine_landmarks=face_config.get("refine_landmarks", True),
            min_detection_confidence=face_config.get("min_detection_confidence", 0.5),
            min_tracking_confidence=face_config.get("min_tracking_confidence", 0.5)
        )
        
        self.mp_hands = mp.solutions.hands
        hands_config = self.config.get("mediapipe", {}).get("hands", {})
        self.hands = self.mp_hands.Hands(
            max_num_hands=hands_config.get("max_num_hands", 1),
            min_detection_confidence=hands_config.get("min_detection_confidence", 0.7),
            min_tracking_confidence=hands_config.get("min_tracking_confidence", 0.5)
        )
        
        # Gesture detection parameters from config
        detection_config = self.config.get("detection", {})
        self.PITCH_THRESHOLD = detection_config.get("pitch_threshold", 12)
        self.YAW_THRESHOLD = detection_config.get("yaw_threshold", 20)
        self.NOD_MAX_TIME = detection_config.get("nod_max_time", 1.0)
        self.HOLD_MIN_TIME = detection_config.get("hold_min_time", 1.0)
        self.RETURN_THRESHOLD = detection_config.get("return_threshold", 8)
        self.COOLDOWN_TIME = detection_config.get("cooldown_time", 1.0)
        self.SMOOTHING_WINDOW = detection_config.get("smoothing_window", 5)
        self.calibration_frames = detection_config.get("calibration_frames", 30)
        self.SCROLL_COOLDOWN = detection_config.get("scroll_cooldown", 0.1)
        self.HAND_COOLDOWN = detection_config.get("hand_cooldown", 1.0)
        self.SWIPE_THRESHOLD = detection_config.get("swipe_threshold", 0.15)
        self.SWIPE_MAX_TIME = detection_config.get("swipe_max_time", 0.5)
        
        self.show_preview = self.config.get("behavior", {}).get("show_preview", True)
        
        # State tracking
        self.pitch_history = deque(maxlen=self.SMOOTHING_WINDOW)
        self.yaw_history = deque(maxlen=self.SMOOTHING_WINDOW)
        
        self.neutral_pitch = None
        self.neutral_yaw = None
        self.calibration_count = 0
        
        self.last_gesture_time = 0
        self.gesture_start_time = None
        self.current_gesture = None
        self.gesture_triggered = False
        self.gesture_type = None  # 'nod' or 'hold'
        self.max_deviation = 0  # Track maximum deviation during gesture
        
        # Scroll parameters
        self.scroll_active = False
        self.last_scroll_time = 0
        
        # Hand gesture state
        self.last_hand_gesture_time = 0
        self.hand_prev_x = None
        self.swipe_start_time = None
        self.swipe_start_x = None
    
    def load_config(self, config_path):
        """Load configuration from JSON file"""
        # Default config mainly for detection parameters. 
        # Action mapping is less critical here as we just send the gesture name.
        default_config = {
            "detection": {
                "pitch_threshold": 12,
                "yaw_threshold": 20,
                "nod_max_time": 1.0,
                "hold_min_time": 1.0,
                "return_threshold": 8,
                "cooldown_time": 1.0,
                "smoothing_window": 5,
                "calibration_frames": 30,
                "scroll_cooldown": 0.1,
                "hand_cooldown": 1.0,
                "swipe_threshold": 0.15,
                "swipe_max_time": 0.5
            },
            "behavior": {
                "show_preview": True
            },
            "mediapipe": {
                "face_mesh": {
                    "max_num_faces": 1,
                    "refine_landmarks": True,
                    "min_detection_confidence": 0.5,
                    "min_tracking_confidence": 0.5
                },
                "hands": {
                    "max_num_hands": 1,
                    "min_detection_confidence": 0.7,
                    "min_tracking_confidence": 0.5
                }
            }
        }
        
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Simple merge for detection params
                if "detection" in user_config:
                    default_config["detection"].update(user_config["detection"])
                if "behavior" in user_config:
                    if "behavior" not in default_config: default_config["behavior"] = {}
                    default_config["behavior"].update(user_config["behavior"])
                if "mediapipe" in user_config:
                    if "face_mesh" in user_config["mediapipe"]:
                        default_config["mediapipe"]["face_mesh"].update(user_config["mediapipe"]["face_mesh"])
                    if "hands" in user_config["mediapipe"]:
                        default_config["mediapipe"]["hands"].update(user_config["mediapipe"]["hands"])
                return default_config
        except Exception:
            # If fail, return defaults
            return default_config

    def calculate_head_pose(self, landmarks, img_w, img_h):
        """Calculate head pose angles from facial landmarks"""
        # Get 3D coordinates for key points
        nose_tip = np.array([landmarks[1].x, landmarks[1].y, landmarks[1].z])
        nose_bridge = np.array([landmarks[168].x, landmarks[168].y, landmarks[168].z])
        chin = np.array([landmarks[152].x, landmarks[152].y, landmarks[152].z])
        
        left_eye = np.array([landmarks[33].x, landmarks[33].y, landmarks[33].z])
        right_eye = np.array([landmarks[263].x, landmarks[263].y, landmarks[263].z])
        
        forehead = np.array([landmarks[10].x, landmarks[10].y, landmarks[10].z])
        
        # Calculate yaw (left/right) from eye positions
        eye_center = (left_eye + right_eye) / 2
        eye_distance = np.linalg.norm(right_eye - left_eye)
        nose_to_center = nose_tip[0] - eye_center[0]
        yaw = np.arctan2(nose_to_center, eye_distance) * 180 / np.pi * 2
        
        # Calculate pitch (up/down) using vertical relationships
        nose_vector = nose_tip - nose_bridge
        nose_angle = np.arctan2(nose_vector[1], -nose_vector[2]) * 180 / np.pi
        
        vertical_ratio = (nose_tip[1] - eye_center[1]) / (chin[1] - eye_center[1] + 0.001)
        
        pitch = nose_angle * 0.7 + (vertical_ratio - 0.3) * 100 * 0.3
        
        return pitch, yaw
    
    def smooth_angles(self, pitch, yaw):
        """Apply moving average smoothing"""
        self.pitch_history.append(pitch)
        self.yaw_history.append(yaw)
        
        smooth_pitch = np.mean(self.pitch_history)
        smooth_yaw = np.mean(self.yaw_history)
        
        return smooth_pitch, smooth_yaw
    
    def calibrate_neutral(self, pitch, yaw):
        """Calibrate neutral head position"""
        if self.calibration_count < self.calibration_frames:
            self.pitch_history.append(pitch)
            self.yaw_history.append(yaw)
            self.calibration_count += 1
            return False
        
        if self.neutral_pitch is None:
            self.neutral_pitch = np.mean(self.pitch_history)
            self.neutral_yaw = np.mean(self.yaw_history)
            self.pitch_history.clear()
            self.yaw_history.clear()
            print(f"Calibration complete! Neutral: pitch={self.neutral_pitch:.1f}, yaw={self.neutral_yaw:.1f}")
        
        return True
    
    def detect_fist(self, hand_landmarks):
        """Detect if hand is making a fist"""
        wrist = hand_landmarks.landmark[0]
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        middle_tip = hand_landmarks.landmark[12]
        ring_tip = hand_landmarks.landmark[16]
        pinky_tip = hand_landmarks.landmark[20]
        
        index_mcp = hand_landmarks.landmark[5]
        middle_mcp = hand_landmarks.landmark[9]
        ring_mcp = hand_landmarks.landmark[13]
        pinky_mcp = hand_landmarks.landmark[17]
        
        fingers_curled = 0
        
        # Check if tips are below MCPs (for upright hand)
        # Note: This simple logic assumes hand is roughly upright. 
        # A more robust check uses distance from wrist, but this works for basic fist.
        if index_tip.y > index_mcp.y: fingers_curled += 1
        if middle_tip.y > middle_mcp.y: fingers_curled += 1
        if ring_tip.y > ring_mcp.y: fingers_curled += 1
        if pinky_tip.y > pinky_mcp.y: fingers_curled += 1
        
        palm_center_x = (index_mcp.x + pinky_mcp.x) / 2
        thumb_curled = abs(thumb_tip.x - palm_center_x) < abs(index_mcp.x - palm_center_x) * 0.8
        
        return fingers_curled >= 4 and thumb_curled
    
    def detect_palm(self, hand_landmarks):
        """Detect if hand is showing open palm"""
        index_tip = hand_landmarks.landmark[8]
        middle_tip = hand_landmarks.landmark[12]
        ring_tip = hand_landmarks.landmark[16]
        pinky_tip = hand_landmarks.landmark[20]
        
        index_mcp = hand_landmarks.landmark[5]
        middle_mcp = hand_landmarks.landmark[9]
        ring_mcp = hand_landmarks.landmark[13]
        pinky_mcp = hand_landmarks.landmark[17]
        
        fingers_extended = 0
        
        if index_tip.y < index_mcp.y: fingers_extended += 1
        if middle_tip.y < middle_mcp.y: fingers_extended += 1
        if ring_tip.y < ring_mcp.y: fingers_extended += 1
        if pinky_tip.y < pinky_mcp.y: fingers_extended += 1
        
        return fingers_extended >= 3
    
    def detect_swipe(self, hand_landmarks):
        """Detect palm swipe gesture (left swipe for undo)"""
        current_time = time.time()
        palm_x = hand_landmarks.landmark[9].x  # Middle finger MCP
        
        is_palm = self.detect_palm(hand_landmarks)
        
        if is_palm:
            if self.swipe_start_x is None:
                # Start tracking swipe
                self.swipe_start_x = palm_x
                self.swipe_start_time = current_time
                self.hand_prev_x = palm_x
            else:
                # Check for swipe motion
                elapsed = current_time - self.swipe_start_time
                distance = self.swipe_start_x - palm_x  # Positive = left swipe
                
                if elapsed < self.SWIPE_MAX_TIME:
                    if distance > self.SWIPE_THRESHOLD:
                        # Left swipe detected
                        self.swipe_start_x = None
                        self.swipe_start_time = None
                        return "swipe_left"
                else:
                    # Timeout, reset
                    self.swipe_start_x = palm_x
                    self.swipe_start_time = current_time
        else:
            # Reset if not palm
            self.swipe_start_x = None
            self.swipe_start_time = None
        
        return None
    
    def detect_head_gesture(self, pitch, yaw):
        """Detect head gestures with nod vs hold distinction"""
        current_time = time.time()
        
        # Calculate relative angles from neutral position
        rel_pitch = pitch - self.neutral_pitch
        rel_yaw = yaw - self.neutral_yaw
        
        # Check cooldown period (skip for continuous scrolling of hold gestures)
        if self.gesture_type != "hold" and current_time - self.last_gesture_time < self.COOLDOWN_TIME:
            return None
        
        # Detect current gesture direction based on thresholds
        detected_gesture = None
        current_deviation = 0
        
        # Prioritize the axis with larger deviation
        if abs(rel_yaw) > abs(rel_pitch) * 1.2:  # Horizontal movement dominant
            if rel_yaw > self.YAW_THRESHOLD:
                detected_gesture = "right"
                current_deviation = abs(rel_yaw)
            elif rel_yaw < -self.YAW_THRESHOLD:
                detected_gesture = "left"
                current_deviation = abs(rel_yaw)
        elif abs(rel_pitch) > abs(rel_yaw) * 0.6:  # Vertical movement dominant
            if rel_pitch > self.PITCH_THRESHOLD:
                detected_gesture = "down"
                current_deviation = abs(rel_pitch)
            elif rel_pitch < -self.PITCH_THRESHOLD:
                detected_gesture = "up"
                current_deviation = abs(rel_pitch)
        
        # Check if returned to near-neutral (for nod completion)
        near_neutral = (abs(rel_pitch) < self.RETURN_THRESHOLD and 
                       abs(rel_yaw) < self.RETURN_THRESHOLD)
        
        # State machine logic
        if detected_gesture:
            if self.current_gesture != detected_gesture:
                # New gesture started
                self.current_gesture = detected_gesture
                self.gesture_start_time = current_time
                self.gesture_triggered = False
                self.max_deviation = current_deviation
                self.gesture_type = None
            else:
                # Continue same gesture
                self.max_deviation = max(self.max_deviation, current_deviation)
                elapsed = current_time - self.gesture_start_time
                
                # Check if it's a hold (sustained beyond hold time)
                if elapsed >= self.HOLD_MIN_TIME and not self.gesture_triggered:
                    self.gesture_triggered = True
                    self.gesture_type = "hold"
                    self.last_gesture_time = current_time
                    # Initialize scroll time to allow immediate continuous scrolling
                    self.last_scroll_time = current_time - self.SCROLL_COOLDOWN
                    return (detected_gesture, "hold")
                
                # For hold gestures (scroll), continue triggering
                if self.gesture_type == "hold" and detected_gesture in ["up", "down"]:
                    if current_time - self.last_scroll_time >= self.SCROLL_COOLDOWN:
                        self.last_scroll_time = current_time
                        return (detected_gesture, "hold")
        
        elif near_neutral and self.current_gesture:
            # Returned to neutral - check if it was a nod
            elapsed = current_time - self.gesture_start_time
            
            if elapsed < self.NOD_MAX_TIME and not self.gesture_triggered:
                # It's a nod (quick gesture)
                self.gesture_triggered = True
                self.gesture_type = "nod"
                self.last_gesture_time = current_time
                result = (self.current_gesture, "nod")
                self.current_gesture = None
                self.gesture_start_time = None
                return result
            else:
                # Too slow or already triggered, just reset
                self.current_gesture = None
                self.gesture_start_time = None
                self.gesture_triggered = False
                self.gesture_type = None
        
        return None
    
    def send_gesture(self, gesture_name, gesture_type):
        """Send gesture to Anki via IPC"""
        self.client.send({
            "type": "gesture",
            "gesture": gesture_name,
            "action_type": gesture_type  # 'nod', 'hold', 'hand'
        })
    
    def draw_info(self, frame, pitch, yaw, gesture_data, hand_gesture):
        """Draw information overlay on frame"""
        h, w = frame.shape[:2]
        
        # Draw calibration status or gesture info
        if self.neutral_pitch is None:
            progress = int((self.calibration_count / self.calibration_frames) * 100)
            cv2.putText(frame, f"Calibrating... {progress}%", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(frame, "Keep head in neutral position", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        else:
            rel_pitch = pitch - self.neutral_pitch
            rel_yaw = yaw - self.neutral_yaw
            
            cv2.putText(frame, f"Pitch: {rel_pitch:+.1f}deg", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, f"Yaw: {rel_yaw:+.1f}deg", (10, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            if self.current_gesture and not self.gesture_triggered:
                elapsed = time.time() - self.gesture_start_time
                
                # Show nod progress
                if elapsed < self.NOD_MAX_TIME:
                    nod_progress = (elapsed / self.NOD_MAX_TIME) * 100
                    cv2.putText(frame, f"Nod: {self.current_gesture} {nod_progress:.0f}%", 
                               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                # Show hold progress
                elif elapsed < self.HOLD_MIN_TIME:
                    hold_progress = (elapsed / self.HOLD_MIN_TIME) * 100
                    cv2.putText(frame, f"Hold: {self.current_gesture} {hold_progress:.0f}%", 
                               (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 165, 0), 2)
            
            if gesture_data:
                gesture, gtype = gesture_data
                cv2.putText(frame, f"HEAD: {gesture.upper()} ({gtype})", (10, h - 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        if hand_gesture:
            cv2.putText(frame, f"HAND: {hand_gesture.upper()}", (10, h - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 2)
    
    def run(self):
        """Main loop"""
        cap = cv2.VideoCapture(0)
        
        print("Starting Gesture Worker...")
        
        while cap.isOpened():
            # Check for messages from Anki
            incoming = self.client.receive_noblock()
            if incoming:
                try:
                    # Handle multiple json per read if concatenated
                    parts = incoming.strip().split('\n')
                    for part in parts:
                        if not part: continue
                        cmd = json.loads(part)
                        if cmd.get("type") == "command" and cmd.get("command") == "recalibrate":
                            print("Received recalibrate command")
                            self.neutral_pitch = None
                            self.neutral_yaw = None
                            self.calibration_count = 0
                            self.pitch_history.clear()
                            self.yaw_history.clear()
                except json.JSONDecodeError:
                    pass

            ret, frame = cap.read()
            if not ret:
                break
            
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process face
            face_results = self.face_mesh.process(rgb_frame)
            
            # Process hands
            hand_results = self.hands.process(rgb_frame)
            
            head_gesture_data = None
            hand_gesture_name = None
            
            # Head gesture detection
            if face_results.multi_face_landmarks:
                landmarks = face_results.multi_face_landmarks[0].landmark
                h, w = frame.shape[:2]
                
                # Calculate head pose
                pitch, yaw = self.calculate_head_pose(landmarks, w, h)
                
                # Apply smoothing
                smooth_pitch, smooth_yaw = self.smooth_angles(pitch, yaw)
                
                # Calibrate or detect gestures
                if not self.calibrate_neutral(smooth_pitch, smooth_yaw):
                    self.draw_info(frame, smooth_pitch, smooth_yaw, None, None)
                else:
                    head_gesture_data = self.detect_head_gesture(smooth_pitch, smooth_yaw)
                    if head_gesture_data:
                        gesture_dir, gesture_mode = head_gesture_data
                        # Send specific gesture string like "nod_right", "hold_up"
                        # Or generic object
                        gesture_full_name = f"{gesture_mode}_{gesture_dir}"
                        self.send_gesture(gesture_full_name, "head")
            
            # Hand gesture detection
            if hand_results.multi_hand_landmarks:
                for hand_landmarks in hand_results.multi_hand_landmarks:
                    # Draw hand landmarks
                    mp.solutions.drawing_utils.draw_landmarks(
                        frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    
                    current_time = time.time()
                    
                    # Check for swipe first (higher priority)
                    swipe = self.detect_swipe(hand_landmarks)
                    if swipe and current_time - self.last_hand_gesture_time > self.HAND_COOLDOWN:
                        hand_gesture_name = swipe
                        self.send_gesture(hand_gesture_name, "hand")
                        self.last_hand_gesture_time = current_time
                    # Then check for fist
                    elif self.detect_fist(hand_landmarks):
                        if current_time - self.last_hand_gesture_time > self.HAND_COOLDOWN:
                            hand_gesture_name = "fist"
                            self.send_gesture(hand_gesture_name, "hand")
                            self.last_hand_gesture_time = current_time
            
            # Draw info overlay
            if self.show_preview:
                if face_results.multi_face_landmarks and self.neutral_pitch is not None:
                    self.draw_info(frame, smooth_pitch, smooth_yaw, head_gesture_data, hand_gesture_name)
                
                cv2.imshow('Gesture Controller', frame)
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    print("Recalibrating...")
                    self.neutral_pitch = None
                    self.neutral_yaw = None
                    self.calibration_count = 0
                    self.pitch_history.clear()
                    self.yaw_history.clear()
            else:
                 # No preview
                 pass
        
        cap.release()
        cv2.destroyAllWindows()
        self.client.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True, help="Port to connect to Anki")
    parser.add_argument("--config", type=str, default="config.json", help="Path to configuration file")
    args = parser.parse_args()
    
    controller = GestureController(args.port, args.config)
    controller.run()
