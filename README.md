# Anki Gesture Control

Control Anki reviews using head gestures and hand swipes.

## Features
- **Hands-free Review**: Use head nods/turns to answer cards (Good, Again, etc.).
- **Scrolling**: Look up/down or hold a gesture to scroll long cards.
- **Configurable**: Remap any gesture to any
- **Detection Sensitivity**: Adjust thresholds for head/hand movements.
- **Auto Start/Stop**: Automatically start gesture control when entering Review mode and stop when leaving.
- **Custom Shortcuts**: Set global shortcuts for toggling control and recalibration.

## Usage
1.  **Start**: Click "Gesture Control" -> "Start Gesture Control" (or use `Ctrl+Shift+G`).
2.  **Gestures**:
    *   **Right Turn**: Answer Good
    *   **Left Turn**: Answer Again
    *   **Fist**: Toggle Review Session
    *   **Swipe Left**: Undo
3.  **Stop**: Click "Stop Gesture Control" (or use `Ctrl+Shift+G` again).

## Configuration
Go to *Gesture Control* -> *Configuration* to:
- Adjust sensitivity (how far you need to turn your head).
- Change gesture mappings.
- Configure scrolling speed and amount.
- Set custom shortcuts.

## Requirements
- Anki 2.1.50+
- Webcam
- Python 3.9

## Installation
1. Install the addon from AnkiWeb or the `.ankiaddon` file.
2. Restart Anki.
3. You will be prompted to set up the gesture environment. Follow the wizard to install dependencies (MediaPipe).
   - *Note: This requires Python 3.9 to be installed on your computer.*