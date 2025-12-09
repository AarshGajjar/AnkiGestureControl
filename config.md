# Configuration

## Structures

### `gestures`
Map specific gestures to Anki actions.
- Keys: `nod_right`, `nod_left`, `nod_up`, `nod_down`, `hold_up`, `hold_down`, `fist`, `swipe_left`.
- Values: `action_answer_good`, `action_answer_again`, `action_bury`, `action_suspend`, etc.

### `detection`
Parameters for gesture recognition.
- `pitch_threshold`: Angle (degrees) for up/down detection.
- `yaw_threshold`: Angle (degrees) for left/right detection.
- `nod_max_time`: Max duration (seconds) for a quick nod.
- `hold_min_time`: Min duration (seconds) to trigger a "hold" action (like scroll).
- `scroll_amount`: Pixels to scroll per event.

### `behavior`
- `auto_start`: (bool) If true, automatically starts gesture control when entering Review mode, and stops when leaving.
- `show_preview`: (bool) If true, shows the camera feed with debug overlays. Set to false to run in background.

### `mediapipe`
Advanced CV parameters.
- `min_detection_confidence`: Lower values detect faces easier but may have false positives.
- `smoothing_window`: Number of frames to average for stable tracking.

### `shortcuts`
Keyboard shortcuts for the addon.
- `toggle`: Start/Stop tracking.
- `recalibrate`: Reset neutral head position.
