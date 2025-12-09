import sys
import os
import subprocess
import threading
import urllib.request
import tempfile
import time
import shutil
import zipfile
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QProgressBar, QWizard, QWizardPage, QMessageBox, QTextEdit,
    QDesktopServices, QUrl
)
from aqt import mw

ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
PORTABLE_ENV_DIR = os.path.join(ADDON_DIR, "python_env")
# Fallback to .venv for legacy or if explicitly set
VENV_DIR = os.path.join(ADDON_DIR, ".venv")

if sys.platform == "win32":
    PYTHON_VENV_PATH = os.path.join(PORTABLE_ENV_DIR, "python.exe")
else:
    PYTHON_VENV_PATH = os.path.join(PORTABLE_ENV_DIR, "bin", "python")

import platform
import stat

# Base Release URL - User must update this to their repo releases
RELEASE_BASE_URL = "https://github.com/AarshGajjar/AnkiGestureControl/releases/download/v1.0"

def get_platform_key():
    system = platform.system().lower() # windows, linux, darwin
    machine = platform.machine().lower() # amd64, x86_64, aarch64, arm64
    
    if system == "windows":
        return "win32_AMD64"
    elif system == "linux" and machine == "x86_64":
        return "linux_x86_64"
    elif system == "darwin":
        if machine == "x86_64":
            return "macos_x86_64"
        elif machine in ["arm64", "aarch64"]:
            return "macos_aarch64"
    
    return None

class OnboardingWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gesture Control Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        
        self.addPage(IntroPage())
        
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

class IntroPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Welcome to Gesture Control")
        self.setSubTitle("This addon requires a dedicated Python environment.")
        
        layout = QVBoxLayout()
        
        self.info_label = QLabel(
            "To run advanced gesture recognition, we need a compatible Python environment.<br><br>"
            "The addon can automatically download a portable version, or you can use an existing system Python 3.9."
        )
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.button_layout = QVBoxLayout()
        
        self.check_btn = QPushButton("Check for Environment")
        self.check_btn.clicked.connect(self.check_environment)
        self.button_layout.addWidget(self.check_btn)
        
        self.download_btn = QPushButton("Download Portable Environment")
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setVisible(False)
        self.button_layout.addWidget(self.download_btn)

        layout.addLayout(self.button_layout)
        
        self.python_path = None
        self.setLayout(layout)
    
    def initializePage(self):
        self.check_environment()

    def check_environment(self):
        self.status_label.setText("Checking...")
        self.status_label.setStyleSheet("")
        self.download_btn.setVisible(False)
        
        # 1. Check for Portable Environment (Prioritized)
        portable_python = self._get_local_python_path()
        if os.path.exists(portable_python):
             self._set_found(portable_python, "Portable Environment found!")
             return

        # 2. Check for System Python 3.9 (Fallback)
        found_system = self._check_system_python()
        if found_system:
             self._set_found(found_system, f"System Python found: {found_system}")
             return
            
        # 3. Not Found
        self.status_label.setText("No compatible Python environment found.")
        self.status_label.setStyleSheet("color: red")
        self.python_path = None
        
        # Enable Download
        self.download_btn.setVisible(True)
        self.download_btn.setEnabled(True)
        
        # Check if platform is supported for auto-download
        key = get_platform_key()
        
        # TEMPORARY: Only Windows is hosted right now
        if key and not key.startswith("win32"):
             self.download_btn.setText(f"Manual Install Required ({key} support coming soon)")
             self.download_btn.setEnabled(False)
             # self.check_btn.setEnabled(True) # Ensure they can re-check after manual install
        elif not key:
            self.download_btn.setText("Manual Install Required (Platform Unsupported)")
            self.download_btn.setEnabled(False) 
        else:
            self.download_btn.setText(f"Download Portable Environment ({key})")

        self.completeChanged.emit()

    def _get_local_python_path(self):
        if sys.platform == "win32":
            return os.path.join(PORTABLE_ENV_DIR, "python.exe")
        return os.path.join(PORTABLE_ENV_DIR, "bin", "python3")

    def _check_system_python(self):
        candidates = ["python3.9", "python3", "python", "py"]
        if sys.platform == "win32":
            # Add common windows paths
            candidates.extend([
                os.path.join(os.environ.get("ProgramFiles", ""), "Python39", "python.exe"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python39", "python.exe")
            ])

        for cmd in candidates:
            try:
                # If cmd is a path, verify existence first
                if os.path.sep in cmd and not os.path.exists(cmd):
                    continue
                    
                args = [cmd, "--version"]
                if cmd == "py": args = ["py", "-3.9", "--version"]

                output = subprocess.check_output(args, stderr=subprocess.STDOUT, startupinfo=self._get_startup_info()).decode().strip()
                if "3.9" in output:
                    # Resolve path
                    if os.path.sep in cmd:
                        return cmd
                    if cmd == "py":
                        return "py -3.9"
                    
                    # Resolve 'python' to absolute path
                    return subprocess.check_output(
                        ["where" if sys.platform == "win32" else "which", cmd], 
                        startupinfo=self._get_startup_info()
                    ).decode().strip().split('\n')[0]
            except:
                continue
        return None

    def _get_startup_info(self):
        if sys.platform == "win32":
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            return si
        return None

    def _set_found(self, path, msg):
        self.python_path = path
        self.status_label.setText(msg)
        self.status_label.setStyleSheet("color: green")
        self.completeChanged.emit()

    def start_download(self):
        self.download_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        thread = threading.Thread(target=self._run_download_process)
        thread.start()

    def _run_download_process(self):
        try:
            # Determine URL
            key = get_platform_key()
            if not key:
                raise Exception("Unsupported platform")
            
            zip_name = f"python_env_{key}.zip"
            url = f"{RELEASE_BASE_URL}/{zip_name}"

            # 1. Download
            self.update_status(f"Downloading {zip_name}...", "blue")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, "env.zip")
                
                def report(block_num, block_size, total_size):
                    if total_size > 0:
                        percent = int((block_num * block_size * 100) / total_size)
                        mw.taskman.run_on_main(lambda: self.progress_bar.setValue(percent))

                urllib.request.urlretrieve(url, zip_path, reporthook=report)
                
                # 2. Extract
                self.update_status("Extracting...", "blue")
                
                # Ensure destination assumes empty
                if os.path.exists(PORTABLE_ENV_DIR):
                    shutil.rmtree(PORTABLE_ENV_DIR)
                os.makedirs(PORTABLE_ENV_DIR)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Simple extraction
                    zip_ref.extractall(PORTABLE_ENV_DIR)
                
                # 3. Post-Install (Fix Permissions on Unix)
                if sys.platform != "win32":
                    self.update_status("Setting permissions...", "blue")
                    bin_dir = os.path.join(PORTABLE_ENV_DIR, "bin")
                    if os.path.exists(bin_dir):
                        for root, dirs, files in os.walk(bin_dir):
                            for f in files:
                                fpath = os.path.join(root, f)
                                # Add executable permission
                                st = os.stat(fpath)
                                os.chmod(fpath, st.st_mode | stat.S_IEXEC)

            self.update_status("Installation complete!", "green")
            mw.taskman.run_on_main(lambda: self.check_environment())

        except Exception as e:
            self.update_status(f"Error: {str(e)}", "red")
            mw.taskman.run_on_main(lambda: self._reset_ui())

    def update_status(self, text, color=""):
        def _update():
            self.status_label.setText(text)
            if color:
                self.status_label.setStyleSheet(f"color: {color}")
        mw.taskman.run_on_main(_update)

    def _reset_ui(self):
        self.download_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def isComplete(self):
        return self.python_path is not None

def get_python_path():
    """
    Returns the path to the python executable to use.
    Prioritizes Portable Environment, then System Python.
    Returns None if none found.
    """
    # 1. Portable
    if os.path.exists(PYTHON_VENV_PATH):
        return PYTHON_VENV_PATH
    
    # 2. System (Reuse logic from IntroPage, but simplified/headless)
    # We can't easily reuse the instance method without refactoring, 
    # so we'll duplicate the simple check logic or instantiate wizard? 
    # Instantiating wizard is heavy. Let's pull the logic out to a standalone function.
    return _find_system_python()

def _find_system_python():
    candidates = ["python3.9", "python3", "python", "py"]
    if sys.platform == "win32":
        candidates.extend([
            os.path.join(os.environ.get("ProgramFiles", ""), "Python39", "python.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Python", "Python39", "python.exe")
        ])

    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    for cmd in candidates:
        try:
            if os.path.sep in cmd and not os.path.exists(cmd):
                continue
                
            args = [cmd, "--version"]
            if cmd == "py": args = ["py", "-3.9", "--version"]

            output = subprocess.check_output(args, stderr=subprocess.STDOUT, startupinfo=startupinfo).decode().strip()
            if "3.9" in output:
                if os.path.sep in cmd: return cmd
                if cmd == "py": return "py -3.9"
                
                # Resolve
                return subprocess.check_output(
                    ["where" if sys.platform == "win32" else "which", cmd], 
                    startupinfo=startupinfo
                ).decode().strip().split('\n')[0]
        except:
            continue
    return None

def check_venv_exists():
    return get_python_path() is not None

def run_wizard():
    mw.gesture_wizard = w = OnboardingWizard(mw)
    w.exec()
