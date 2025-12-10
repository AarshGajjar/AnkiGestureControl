import os
import sys
import subprocess
import socket
import threading
import json
import time

from aqt import mw
from aqt.utils import showInfo, tooltip
from aqt.qt import QAction, QMenu, QKeySequence, QShortcut, Qt
from anki.hooks import addHook
from aqt import gui_hooks

from .onboarding import check_venv_exists, run_wizard, get_python_path
from .config_ui import ConfigDialog, DEFAULT_CONFIG

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
WORKER_SCRIPT = os.path.join(ADDON_DIR, "gesture_worker.py")

class GestureServer:
    def __init__(self):
        self.server_socket = None
        self.port = 0
        self.running = False
        self.worker_process = None
        self.thread = None
        self.active_conn = None # Store active connection
        self.shortcuts = [] # Store global shortcuts
        self.setup_menu()

        # Check venv on startup
        if not check_venv_exists():
            # Defer wizard run to allow Anki to fully load
            mw.progress.timer(1000, self.prompt_onboarding, False)
        
        self.paused = False

        # Load Configuration
        self.load_config()

        # Hooks
        gui_hooks.state_did_change.append(self.on_state_change)


        # Action Method Mapping (Fixed)
        self.available_methods = {
            "action_answer_good": self.action_answer_good,
            "action_answer_again": self.action_answer_again,
            "action_answer_easy": self.action_answer_easy, 
            "action_answer_hard": self.action_answer_hard, 
            "action_scroll_down": self.action_scroll_down,
            "action_scroll_up": self.action_scroll_up,
            "action_toggle_review": self.action_toggle_review,
            "action_undo": self.action_undo,
            "action_bury": self.action_bury,
            "action_suspend": self.action_suspend,
            "action_recalibrate": self.action_recalibrate,
            "action_none": lambda: None
        }

    def prompt_onboarding(self):
        run_wizard()

    def setup_menu(self):
        menu = QMenu("Gesture Control", mw)
        mw.form.menubar.addMenu(menu)
        
        self.toggle_action = QAction("Start Gesture Control", mw)
        self.toggle_action.triggered.connect(self.toggle)
        menu.addAction(self.toggle_action)

        self.recalibrate_action = QAction("Recalibrate Gestures", mw)
        self.recalibrate_action.triggered.connect(self.action_recalibrate)
        menu.addAction(self.recalibrate_action)
        
        onboarding_action = QAction("Run Onboarding Wizard", mw)
        onboarding_action.triggered.connect(self.run_onboarding_wizard)
        menu.addAction(onboarding_action)

        config_action = QAction("Configuration", mw)
        config_action.triggered.connect(self.open_config)
        menu.addAction(config_action)

    def run_onboarding_wizard(self):
        """
        Expose the onboarding wizard even if a system Python 3.9 is present.
        Useful for users who want to switch to the portable env.
        """
        run_wizard()

    def open_config(self):
        ConfigDialog(mw).exec()
        # Reload config after close
        self.load_config()

    def load_config(self):
        self.config = mw.addonManager.getConfig(__name__) or DEFAULT_CONFIG
        self.ensure_config_structure(DEFAULT_CONFIG, self.config)
        
        # Update mappings
        self.gesture_map = self.config.get("gestures", DEFAULT_CONFIG["gestures"])
        
        # Apply shortcuts (Global)
        # Clear old shortcuts
        for s in self.shortcuts:
            s.setEnabled(False)
            s.setParent(None)
        self.shortcuts = [] 
        
        shortcuts = self.config.get("shortcuts", DEFAULT_CONFIG["shortcuts"])
        
        # Remove action shortcuts to avoid conflicts
        self.toggle_action.setShortcut(QKeySequence(""))
        self.recalibrate_action.setShortcut(QKeySequence(""))
        
        try:
            # Check for correct enum in Qt6 vs Qt5
            if hasattr(Qt, "ShortcutContext"):
                ctx = Qt.ShortcutContext.ApplicationShortcut
            else:
                ctx = Qt.ApplicationShortcut
        except AttributeError:
             ctx = 3 # Fallback to int (ApplicationShortcut is usually 3)

        if "toggle" in shortcuts and shortcuts["toggle"]:
            key = shortcuts["toggle"]
            print(f"GestureControl: Setting toggle shortcut {key}")
            s = QShortcut(QKeySequence(key), mw)
            s.setContext(ctx)
            s.activated.connect(self.toggle)
            self.shortcuts.append(s)
            self.toggle_action.setToolTip(f"Shortcut: {key}")

        if "recalibrate" in shortcuts and shortcuts["recalibrate"]:
             key = shortcuts["recalibrate"]
             s = QShortcut(QKeySequence(key), mw)
             s.setContext(ctx)
             s.activated.connect(self.action_recalibrate)
             self.shortcuts.append(s)
             self.recalibrate_action.setToolTip(f"Shortcut: {key}")

    def ensure_config_structure(self, default, current):
        for k, v in default.items():
            if k not in current:
                current[k] = v
            elif isinstance(v, dict) and isinstance(current[k], dict):
                self.ensure_config_structure(v, current[k])
        
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('127.0.0.1', 0)) # bind to free port
        self.port = self.server_socket.getsockname()[1]
        self.server_socket.listen(1)
        self.running = True
        print(f"Gesture Server listening on port {self.port}")
        
        while self.running:
            try:
                self.server_socket.settimeout(1.0)
                conn, addr = self.server_socket.accept()
                with conn:
                    print(f"Connected by {addr}")
                    self.active_conn = conn
                    buffer = ""
                    while self.running:
                        try:
                            data = conn.recv(1024)
                            if not data:
                                break
                            buffer += data.decode('utf-8')
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                if line:
                                    self.handle_message(line)
                        except socket.timeout:
                            pass
                        except Exception as e:
                             print(f"Connection error: {e}")
                             break
                    self.active_conn = None
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Server error: {e}")
    
    def handle_message(self, message):
        try:
            data = json.loads(message)
            gesture = data.get("gesture")
            
            # Map gesture (e.g. "nod_right") to action name (e.g. "action_answer_good")
            action_name = self.gesture_map.get(gesture)
            
            if action_name and action_name in self.available_methods:
                method = self.available_methods[action_name]
                mw.taskman.run_on_main(method)
                
        except json.JSONDecodeError:
            pass

    def start(self):
        if not check_venv_exists():
            showInfo("Please run the onboarding wizard first.")
            run_wizard()
            return
            
        if self.worker_process:
            tooltip("Gesture Control is already running.")
            return

        self.paused = False
        # Start Server Thread
        self.thread = threading.Thread(target=self.start_server)
        self.thread.daemon = True
        self.thread.start()

        # Wait a bit for server to spin up
        time.sleep(0.5)

        # Write current config to config.json for worker
        # Ensuring the worker reads the latest config from the standard file
        config_path = os.path.join(ADDON_DIR, "config.json")
        with open(config_path, "w") as f:
            json.dump(self.config, f, indent=4)

        # Start Worker Process
        cmd = [get_python_path(), WORKER_SCRIPT, "--port", str(self.port), "--config", config_path]
        
        # Hide console on Windows
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
        self.worker_process = subprocess.Popen(
            cmd, 
            cwd=ADDON_DIR,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        )
        
        tooltip("Gesture Control Started!")
        self.update_toggle_action_text()

    def stop(self):
        self.running = False
        if self.worker_process:
            self.worker_process.terminate()
            self.worker_process = None
        
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        
        tooltip("Gesture Control Stopped.")
        self.update_toggle_action_text()

    def toggle(self):
        if self.worker_process:
            self.stop()
        else:
            self.start()

    def update_toggle_action_text(self):
        if hasattr(self, 'toggle_action'):
             if self.worker_process:
                 self.toggle_action.setText("Stop Gesture Control")
             else:
                 self.toggle_action.setText("Start Gesture Control")

    # Actions
    def action_answer_good(self):
        if mw.reviewer.card:
            if mw.reviewer.state == "question":
                mw.reviewer._showAnswer()
            elif mw.reviewer.state == "answer":
                mw.reviewer._answerCard(3) 

    def action_answer_again(self):
         if mw.reviewer.card and mw.reviewer.state == "answer":
            mw.reviewer._answerCard(1)

    def action_answer_hard(self):
         if mw.reviewer.card and mw.reviewer.state == "answer":
            mw.reviewer._answerCard(2)

    def action_answer_easy(self):
         if mw.reviewer.card and mw.reviewer.state == "answer":
            mw.reviewer._answerCard(4)

    def action_scroll_down(self):
         if mw.reviewer.web:
             amount = self.config.get("detection", {}).get("scroll_amount", 100)
             mw.reviewer.web.eval(f"window.scrollBy(0, {amount});")

    def action_scroll_up(self):
         if mw.reviewer.web:
             amount = self.config.get("detection", {}).get("scroll_amount", 100)
             mw.reviewer.web.eval(f"window.scrollBy(0, -{amount});")

    def action_undo(self):
        mw.onUndo()

    def action_toggle_review(self):
        if mw.state == "review":
            mw.moveToState("deckBrowser")
            from aqt.utils import tooltip
            tooltip("Review Session Stopped", period=1000)
        elif mw.state == "overview":
            mw.moveToState("review")
            from aqt.utils import tooltip
            tooltip("Review Session Started", period=1000)
        elif mw.state == "deckBrowser":
            did = mw.col.decks.current()['id']
            mw.col.decks.select(did)
            mw.moveToState("review")
            from aqt.utils import tooltip
            deck_name = mw.col.decks.current()['name']
            tooltip(f"Started Review: {deck_name}", period=1000)

    def action_bury(self):
        if mw.reviewer.card and mw.state == "review":
             # Try standard method
             if hasattr(mw.reviewer, "onBuryCard"):
                 mw.reviewer.onBuryCard()
             elif hasattr(mw.reviewer, "bury_current_card"):
                 mw.reviewer.bury_current_card()
             else:
                 # Fallback/Older Anki
                 mw.checkpoint("Bury")
                 mw.reviewer.card.queue = -1
                 mw.reviewer.card.flush()
                 mw.reviewer.nextCard()
                 from aqt.utils import tooltip
                 tooltip("Card Buried")

    def action_suspend(self):
         if mw.reviewer.card and mw.state == "review":
             if hasattr(mw.reviewer, "onSuspendCard"):
                 mw.reviewer.onSuspendCard()
             elif hasattr(mw.reviewer, "suspend_current_card"):
                 mw.reviewer.suspend_current_card()
             else:
                 mw.checkpoint("Suspend")
                 mw.reviewer.card.queue = -1
                 mw.reviewer.card.flush()
                 mw.col.sched.suspendCards([mw.reviewer.card.id])
                 mw.reviewer.nextCard()
                 from aqt.utils import tooltip
                 tooltip("Card Suspended")

    def action_recalibrate(self):
        if self.active_conn:
            try:
                msg = json.dumps({"type": "command", "command": "recalibrate"}) + "\n"
                self.active_conn.sendall(msg.encode('utf-8'))
                from aqt.utils import tooltip
                tooltip("Recalibrating...", period=1000)
            except Exception as e:
                 print(f"Failed to send recalibrate: {e}")
        else:
             from aqt.utils import tooltip
             tooltip("Gesture Control not connected", period=1000)

    def on_state_change(self, new_state, old_state):
        if not self.config.get("behavior", {}).get("auto_start", False):
            return

        if new_state == "review":
            if not self.worker_process:
                self.start()
        elif old_state == "review":
            if self.worker_process:
                self.stop()

# Initialize
gesture_server = GestureServer()

# Hook shutdown to cleanup
def cleanup():
    gesture_server.stop()

addHook("unloadProfile", cleanup)
