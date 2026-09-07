# Android Emulator Dock

**Android Emulator Dock (AED)** is a standalone Linux desktop application that hosts multiple official Android Emulator instances in a single native Wayland application window.

## Highlights
- **Native Wayland**: Pure Qt 6 application with zero dependence on X11 window reparenting or compositor nesting.
- **Official gRPC Integration**: Directly streams frames using `EmulatorController.streamScreenshot` and forwards touch, mouse, wheel, and keyboard events.
- **Preserved Official Controls**: Full access to the official emulator Extended Controls (Location / Google Maps UI, Battery, Cellular, Sensors, Camera).
- **Multi-Emulator Workspace**: Organize multiple running devices in Single, Two-Column, or Grid layouts.
- **Secure by Design**: Authentication tokens are redacted from all diagnostics and logs.
- **Android Studio Independent**: Runs standalone without requiring Android Studio to be installed.

## Getting Started

### Launching
```bash
./bin/android-emulator-dock
```

### Running Tests
```bash
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_*.py"
```
