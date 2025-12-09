import sys
import os
import subprocess
import threading
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QWizard, QWizardPage, QMessageBox, QTextEdit
)
from aqt import mw

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(ADDON_DIR, ".venv")

if sys.platform == "win32":
    PYTHON_VENV_PATH = os.path.join(VENV_DIR, "Scripts", "python.exe")
else:
    PYTHON_VENV_PATH = os.path.join(VENV_DIR, "bin", "python")

class OnboardingWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gesture Control Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        
        self.addPage(IntroPage())
        self.addPage(InstallPage())
        
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

class IntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to Gesture Control")
        # Don't use setSubTitle if we want rich text or more control, but it's fine for simple text.
        self.setSubTitle("This addon requires a one-time setup to install necessary libraries.")
        
        layout = QVBoxLayout()
        
        info_label = QLabel(
            "To run advanced gesture recognition, we need to create a dedicated environment "
            "with <b>Python 3.9</b>.<br><br>"
            "Please ensure you have Python 3.9 installed on your system.<br>"
            "If not, please download it from python.org."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        self.check_btn = QPushButton("Check for Python 3.9")
        self.check_btn.clicked.connect(self.check_python)
        layout.addWidget(self.check_btn)
        
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        self.python_path = None
        self.setLayout(layout)
    
    def check_python(self):
        # simple check for python3.9 or python
        candidates = ["python3.9", "python3", "python", "py"]
        found = False
        
        for cmd in candidates:
            try:
                # Check version
                if cmd == "py":
                     # Windows launcher support
                     args = ["py", "-3.9", "--version"]
                else:
                    args = [cmd, "--version"]

                output = subprocess.check_output(args, stderr=subprocess.STDOUT).decode().strip()
                if "3.9" in output:
                    self.status_label.setText(f"Found: {output}")
                    self.status_label.setStyleSheet("color: green")
                    
                    if cmd == "py":
                        self.python_path = "py -3.9" # Special marker for launcher
                    else:
                        # Get absolute path
                        self.python_path = subprocess.check_output(
                            ["where" if sys.platform == "win32" else "which", cmd]
                        ).decode().strip().split('\n')[0]
                    
                    found = True
                    self.completeChanged.emit() # enable Next button
                    break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        
        if not found:
            self.status_label.setText("Python 3.9 not found. Please install it and try again.")
            self.status_label.setStyleSheet("color: red")
            self.python_path = None
            self.completeChanged.emit()

    def isComplete(self):
        return self.python_path is not None

class InstallPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Installing Dependencies")
        
        layout = QVBoxLayout()
        
        self.status = QLabel("Ready to install...")
        layout.addWidget(self.status)
        
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Installation logs will appear here...")
        layout.addWidget(self.log_area)
        
        layout.addStretch()
        
        self.install_btn = QPushButton("Start Installation")
        self.install_btn.clicked.connect(self.start_install)
        layout.addWidget(self.install_btn)
        
        self.setLayout(layout)
        self.is_finished = False

    def start_install(self):
        self.install_btn.setEnabled(False)
        self.progress.setValue(0)
        self.log_area.clear()
        
        # Get python path from previous page
        intro_page = self.wizard().page(0)
        self.python_cmd = intro_page.python_path
        
        thread = threading.Thread(target=self.run_install)
        thread.start()

    def run_install(self):
        try:
            # Common flags for hiding window on Windows
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW

            def run_command(args, description):
                self.update_status(description)
                self.append_log(f"\n> {' '.join(args)}\n")
                
                process = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    startupinfo=startupinfo,
                    creationflags=creationflags,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    universal_newlines=True
                )
                
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        self.append_log(line.strip())
                
                if process.returncode != 0:
                    raise subprocess.CalledProcessError(process.returncode, args)

            # 1. Create Venv
            cmd_base = []
            if self.python_cmd.startswith("py -"): # Handle py launcher
                # py -3.9 -> ["py", "-3.9"]
                parts = self.python_cmd.split()
                cmd_base = parts + ["-m", "venv"]
            else:
                cmd_base = [self.python_cmd, "-m", "venv"]
            
            run_command(cmd_base + [VENV_DIR], "Creating virtual environment...")
            
            # 2. Upgrade pip
            run_command([PYTHON_VENV_PATH, "-m", "pip", "install", "--upgrade", "pip"], "Upgrading pip...")
            
            # 3. Install requirements
            req_path = os.path.join(ADDON_DIR, "requirements.txt")
            run_command([PYTHON_VENV_PATH, "-m", "pip", "install", "-r", req_path], "Installing libraries...")
            
            self.update_status("Installation complete!", 100)
            self.is_finished = True
            mw.taskman.run_on_main(self.enable_finish)

        except subprocess.CalledProcessError as e:
            self.update_status(f"Error (Exit Code {e.returncode})", 0)
            self.append_log(f"Command failed: {e.cmd}")
            self.is_finished = False
        except Exception as e:
            self.update_status(f"Unexpected Error: {e}", 0)
            self.append_log(str(e))
            self.is_finished = False

    def update_status(self, text, percent=None):
        mw.taskman.run_on_main(lambda: self._update_ui_status(text, percent))

    def append_log(self, text):
        mw.taskman.run_on_main(lambda: self._append_ui_log(text))

    def _update_ui_status(self, text, percent):
        self.status.setText(text)
        if percent is not None:
            self.progress.setValue(percent)

    def _append_ui_log(self, text):
        self.log_area.append(text)
        sb = self.log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def enable_finish(self):
        self.completeChanged.emit()

    def isComplete(self):
        return self.is_finished

def check_venv_exists():
    return os.path.exists(PYTHON_VENV_PATH)

def run_wizard():
    mw.gesture_wizard = w = OnboardingWizard(mw)
    w.exec()
