# Anki Gesture Control

An addon for Anki that allows you to control your reviews using head and hand gestures, providing a hands-free learning experience.

## Features

*   **Hands-Free Control**: Answer cards, scroll, and perform other actions without touching your keyboard or mouse.
*   **Gesture-Based Actions**: Use intuitive head nods, turns, and hand gestures to control Anki.
*   **Customizable Gesture Mapping**: Easily remap gestures to a wide range of Anki actions to fit your workflow.
*   **Adjustable Sensitivity**: Fine-tune the sensitivity of gesture detection to match your preferences and environment.
*   **On-the-Fly Recalibration**: Quickly recalibrate your neutral head position for optimal performance.
*   **Camera Preview**: An optional real-time camera feed to help you position yourself and see the gesture detection in action.
*   **Automatic Start/Stop**: Configure the addon to automatically start gesture detection when you begin a review session and stop when you're done.
*   **Configurable Shortcuts**: Set your own global keyboard shortcuts for common actions like toggling gesture control and recalibrating.

## Installation and Setup

1.  **Install the Addon**: Download the addon from the AnkiWeb addon page or install it manually.
1.  **Install the Addon**: Download the addon from the AnkiWeb addon page or install it manually.
2.  **Run the Onboarding Wizard**: The first time you start Anki after installing the addon, an onboarding wizard will appear.
    *   **Windows**: The wizard can **automatically download** a portable Python environment, so no manual setup is needed!
    *   **Mac/Linux**: The wizard will check for Python 3.9. If not found, you will need to install it manually.
    *   The wizard sets up a dedicated environment for the gesture recognition library.

## How to Use

1.  **Start/Stop Gesture Control**:
    *   Go to the **Gesture Control** menu in Anki's main window and select **Start Gesture Control**.
    *   Alternatively, use the default shortcut `Ctrl+Shift+G`.
2.  **Perform Gestures**:
    *   Position yourself in front of your webcam.
    *   If the camera preview is enabled, you will see a window with your video feed.
    *   Perform one of the supported gestures (see the table below).
3.  **Recalibrate**:
    *   If you change your position or the gesture detection feels off, you can recalibrate at any time.
    *   Go to the **Gesture Control** menu and select **Recalibrate Gestures**.
    *   Alternatively, use the default shortcut `Ctrl+Shift+R`.

## Gestures

The addon recognizes the following gestures. You can customize the action associated with each gesture in the configuration settings.

| Gesture | Default Action | Description |
| --- | --- | --- |
| **Nod Right** | Answer Good / Show Answer | Quickly turn your head to the right and back to the center. |
| **Nod Left** | Answer Again | Quickly turn your head to the left and back to the center. |
| **Nod Up** | Answer Hard | Quickly nod your head up and back to the center. |
| **Nod Down** | Answer Easy | Quickly nod your head down and back to the center. |
| **Look Right (Hold)** | Suspend Card | Turn your head to the right and hold the position. |
| **Look Left (Hold)** | Bury Card | Turn your head to theleft and hold the position. |
| **Look Up (Hold)** | Scroll Up | Look up and hold the position to scroll up on long cards. |
| **Look Down (Hold)** | Scroll Down | Look down and hold the position to scroll down on long cards. |
| **Fist** | Start/Stop Review | Make a fist with your hand in front of the camera. |
| **Swipe Left (Palm)**| Undo | Swipe your open palm from right to left across the camera's view. |

## Actions

You can map any of the gestures to the following actions:

*   **Answer Good / Show Answer**: Marks the card as "Good" or shows the answer if it's hidden.
*   **Answer Again**: Marks the card as "Again".
*   **Answer Hard**: Marks the card as "Hard".
*   **Answer Easy**: Marks the card as "Easy".
*   **Scroll Down**: Scrolls down on the current card.
*   **Scroll Up**: Scrolls up on the current card.
*   **Start/Stop Review**: Toggles the review session.
*   **Undo**: Undoes the last action.
*   **Bury Card**: Buries the current card.
*   **Suspend Card**: Suspends the current card.
*   **Recalibrate**: Recalibrates the neutral head position.
*   **None**: No action.

## Configuration

You can access the configuration dialog by going to the **Gesture Control** menu and selecting **Configuration**. The settings are divided into several tabs:

*   **Gestures**: Map gestures to actions.
*   **Sensitivity**: Adjust the thresholds for gesture detection, such as how far you need to turn your head or how long you need to hold a pose.
*   **Advanced**: Configure more advanced options, including:
    *   Behavioral settings like auto-start and the camera preview.
    *   Fine-tune the underlying `MediaPipe` settings for face and hand detection.
*   **Shortcuts**: Change the keyboard shortcuts for toggling gesture control and recalibrating.

## Requirements

*   Anki 2.1.50+
*   A webcam
*   **Mac/Linux**: Supported via automatic portable download (or Manual System Python 3.9).
*   **Windows**: Supported via automatic portable download.
