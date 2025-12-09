import json
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget, QWidget,
    QComboBox, QSlider, QSpinBox, QPushButton, Qt, QFormLayout, QKeySequenceEdit, QKeySequence, QDoubleSpinBox
)
from aqt import mw

# Default Configuration
DEFAULT_CONFIG = {
    "gestures": {
        "nod_right": "action_answer_good",
        "nod_left": "action_answer_again",
        "nod_up": "action_hard",
        "nod_down": "action_easy",
        "hold_down": "action_scroll_down",
        "hold_up": "action_scroll_up",
        "hold_left": "action_bury",
        "hold_right": "action_suspend",
        "fist": "action_toggle_review",
        "swipe_left": "action_undo"
    },
    "detection": {
        "pitch_threshold": 12,
        "yaw_threshold": 20,
        "nod_max_time": 1.0,
        "hold_min_time": 1.0,
        "return_threshold": 8,
        "cooldown_time": 1.0,
        "scroll_cooldown": 0.1,
        "swipe_threshold": 0.15,
        "swipe_max_time": 0.5,
        "smoothing_window": 5,
        "calibration_frames": 30,
        "scroll_amount": 20
    },
    "behavior": {
        "auto_start": False,
        "show_preview": True
    },
    "mediapipe": {
        "face_mesh": {
            "max_num_faces": 1,
            "min_detection_confidence": 0.5,
            "min_tracking_confidence": 0.5
        },
        "hands": {
            "max_num_hands": 1,
            "min_detection_confidence": 0.7,
            "min_tracking_confidence": 0.5
        }
    },
    "shortcuts": {
        "toggle": "Ctrl+Shift+G",
        "recalibrate": "Ctrl+Shift+R"
    }
}

# Available Actions for Mapping
AVAILABLE_ACTIONS = {
    "action_answer_good": "Answer Good / Show Answer",
    "action_answer_again": "Answer Again",
    "action_answer_hard": "Answer Hard",
    "action_answer_easy": "Answer Easy",
    "action_scroll_down": "Scroll Down",
    "action_scroll_up": "Scroll Up",
    "action_toggle_review": "Start/Stop Review",
    "action_undo": "Undo",
    "action_bury": "Bury Card",
    "action_suspend": "Suspend Card",
    "action_recalibrate": "Recalibrate",
    "action_none": "None"
}

class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gesture Control Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self.config = mw.addonManager.getConfig(__name__) or DEFAULT_CONFIG
        
        # Ensure deep structure exists (simple merge usually not enough for nested dicts)
        self.ensure_config_structure(DEFAULT_CONFIG, self.config)

        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        
        self.tabs.addTab(self.create_gestures_tab(), "Gestures")
        self.tabs.addTab(self.create_sensitivity_tab(), "Sensitivity")
        self.tabs.addTab(self.create_advanced_tab(), "Advanced")
        self.tabs.addTab(self.create_shortcuts_tab(), "Shortcuts")
        
        layout.addWidget(self.tabs)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_config)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        # Restore Defaults
        defaults_btn = QPushButton("Restore Defaults")
        defaults_btn.clicked.connect(self.restore_defaults)
        
        btn_layout.addWidget(defaults_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def ensure_config_structure(self, default, current):
        for k, v in default.items():
            if k not in current:
                current[k] = v
            elif isinstance(v, dict) and isinstance(current[k], dict):
                self.ensure_config_structure(v, current[k])

    def create_gestures_tab(self):
        widget = QWidget()
        scroll_area = QVBoxLayout() # Just standard layout, QScrollArea if needed
        layout = QFormLayout()
        
        self.gesture_combos = {}
        
        gesture_labels = {
            "nod_right": "Nod Right (Turn Right)",
            "nod_left": "Nod Left (Turn Left)",
            "nod_up": "Nod Up",
            "nod_down": "Nod Down",
            "hold_down": "Look Down (Hold)",
            "hold_up": "Look Up (Hold)",
            "hold_left": "Look Left (Hold)",
            "hold_right": "Look Right (Hold)",
            "fist": "Fist Gesture",
            "swipe_left": "Swipe Left (Palm)"
        }
        
        for key, label in gesture_labels.items():
            combo = QComboBox()
            # Populate actions
            for action_key, action_name in AVAILABLE_ACTIONS.items():
                combo.addItem(action_name, action_key)
            
            # Set current value
            current_action = self.config["gestures"].get(key, DEFAULT_CONFIG["gestures"].get(key))
            index = combo.findData(current_action)
            if index >= 0:
                combo.setCurrentIndex(index)
            
            self.gesture_combos[key] = combo
            layout.addRow(label, combo)
            
        widget.setLayout(layout)
        return widget

    def create_sensitivity_tab(self):
        widget = QWidget()
        layout = QFormLayout()
        
        self.sensitivity_inputs = {}
        
        # Define sliders/inputs
        controls = [
            ("pitch_threshold", "Pitch Threshold (Head Up/Down)", 5, 45, 1),
            ("yaw_threshold", "Yaw Threshold (Head Turn)", 5, 45, 1),
            ("nod_max_time", "Nod Speed (Max Duration sec)", 1, 30, 10), 
            ("hold_min_time", "Hold Trigger Time (sec)", 1, 30, 10),
            ("swipe_threshold", "Swipe Distance Threshold", 5, 50, 100),
            ("cooldown_time", "Gesture Cooldown (sec)", 1, 30, 10),
            ("scroll_cooldown", "Scroll Speed (Cooldown sec)", 1, 10, 100),
            ("scroll_amount", "Scroll Amount (Pixels)", 10, 500, 1)
        ]
        
        for key, label, min_val, max_val, scale in controls:
            val = self.config["detection"].get(key, DEFAULT_CONFIG["detection"].get(key))
            
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(int(val * scale))
            
            # Label to show value
            val_label = QLabel(str(float(slider.value()) / scale))
            
            slider.valueChanged.connect(lambda v, l=val_label, s=scale: l.setText(str(float(v)/s)))
            
            self.sensitivity_inputs[key] = (slider, scale)
            
            row_layout = QHBoxLayout()
            row_layout.addWidget(slider)
            row_layout.addWidget(val_label)
            
            layout.addRow(label, row_layout)
            
        widget.setLayout(layout)
        return widget

    def create_advanced_tab(self):
        widget = QWidget()
        layout = QFormLayout()
        self.advanced_inputs = {}

        # Detection Advanced
        detection_group = QLabel("<b>Detection Parameters</b>")
        layout.addRow(detection_group)
        
        adv_detection_controls = [
             ("smoothing_window", "Smoothing Window (Frames)", 1, 20, 1),
             ("calibration_frames", "Calibration Frames", 10, 100, 1)
        ]

        for key, label, min_val, max_val, scale in adv_detection_controls:
            val = self.config["detection"].get(key, DEFAULT_CONFIG["detection"].get(key))
            spin = QSpinBox()
            spin.setRange(min_val, max_val)
            spin.setValue(int(val))
            self.advanced_inputs[("detection", key)] = spin
            self.advanced_inputs[("detection", key)] = spin
            layout.addRow(label, spin)

        # Behavior
        behavior_group = QLabel("<b>Behavior</b>")
        layout.addRow(behavior_group)
        
        from aqt.qt import QCheckBox
        auto_start_cb = QCheckBox("Auto Start/Stop in Review")
        auto_start_cb.setChecked(self.config.get("behavior", DEFAULT_CONFIG["behavior"]).get("auto_start", False))
        self.advanced_inputs[("behavior", "auto_start")] = auto_start_cb
        layout.addRow("Auto Start:", auto_start_cb)

        show_preview_cb = QCheckBox("Show Camera Preview Window")
        show_preview_cb.setChecked(self.config.get("behavior", DEFAULT_CONFIG["behavior"]).get("show_preview", True))
        self.advanced_inputs[("behavior", "show_preview")] = show_preview_cb
        layout.addRow("Camera Preview:", show_preview_cb)

        # MediaPipe Face
        mp_face_group = QLabel("<b>MediaPipe Face</b>")
        layout.addRow(mp_face_group)
        
        mp_controls = [
             ("min_detection_confidence", "Min Detection Confidence", 0.1, 1.0, "face_mesh"),
             ("min_tracking_confidence", "Min Tracking Confidence", 0.1, 1.0, "face_mesh"),
        ]
        
        for key, label, min_val, max_val, sub_key in mp_controls:
             val = self.config["mediapipe"][sub_key].get(key, DEFAULT_CONFIG["mediapipe"][sub_key].get(key))
             spin = QDoubleSpinBox()
             spin.setRange(min_val, max_val)
             spin.setSingleStep(0.1)
             spin.setValue(float(val))
             self.advanced_inputs[("mediapipe", sub_key, key)] = spin
             layout.addRow(label, spin)

        # MediaPipe Hands
        mp_hand_group = QLabel("<b>MediaPipe Hands</b>")
        layout.addRow(mp_hand_group)
        
        mp_hand_controls = [
             ("min_detection_confidence", "Min Detection Confidence", 0.1, 1.0, "hands"),
             ("min_tracking_confidence", "Min Tracking Confidence", 0.1, 1.0, "hands"),
        ]
        
        for key, label, min_val, max_val, sub_key in mp_hand_controls:
             val = self.config["mediapipe"][sub_key].get(key, DEFAULT_CONFIG["mediapipe"][sub_key].get(key))
             spin = QDoubleSpinBox()
             spin.setRange(min_val, max_val)
             spin.setSingleStep(0.1)
             spin.setValue(float(val))
             self.advanced_inputs[("mediapipe", sub_key, key)] = spin
             layout.addRow(label, spin)

        widget.setLayout(layout)
        return widget

    def create_shortcuts_tab(self):
        widget = QWidget()
        layout = QFormLayout()
        self.shortcut_inputs = {}
        
        shortcuts = {
            "toggle": "Toggle Gesture Control",
            "recalibrate": "Recalibrate"
        }
        
        for key, label in shortcuts.items():
            current_key_str = self.config.get("shortcuts", DEFAULT_CONFIG["shortcuts"]).get(key, "")
            seq = QKeySequence(current_key_str)
            edit = QKeySequenceEdit(seq)
            self.shortcut_inputs[key] = edit
            layout.addRow(label, edit)
        
        widget.setLayout(layout)
        return widget

    def save_config(self):
        # Save Gestures
        for key, combo in self.gesture_combos.items():
            self.config["gestures"][key] = combo.currentData()
            
        # Save Sensitivity
        for key, (slider, scale) in self.sensitivity_inputs.items():
            self.config["detection"][key] = float(slider.value()) / scale
            
        # Save Advanced
        for key_tuple, widget in self.advanced_inputs.items():
            if key_tuple[0] == "behavior":
                cat, key = key_tuple
                if "behavior" not in self.config: self.config["behavior"] = {}
                self.config[cat][key] = widget.isChecked()
            elif len(key_tuple) == 2: # detection
                cat, key = key_tuple
                self.config[cat][key] = widget.value()
            elif len(key_tuple) == 3: # mediapipe
                cat, sub, key = key_tuple
                self.config[cat][sub][key] = widget.value()

        # Save Shortcuts
        if "shortcuts" not in self.config: self.config["shortcuts"] = {}
        for key, edit in self.shortcut_inputs.items():
            seq = edit.keySequence()
            self.config["shortcuts"][key] = seq.toString(QKeySequence.SequenceFormat.PortableText)

        mw.addonManager.writeConfig(__name__, self.config)
        self.accept()

    def restore_defaults(self):
        # Reset to defaults
        import copy
        self.config = copy.deepcopy(DEFAULT_CONFIG)
        
        # We need to close and reopen or refresh all widgets. 
        # For simplicity, we'll just close and let user reopen, 
        # or implement simple refresh logic (tedious). 
        # Easier: Just close with a message "Defaults restored. Please reopen config."
        mw.addonManager.writeConfig(__name__, self.config)
        self.accept()
