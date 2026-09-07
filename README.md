# Android Emulator Dock (AED)

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Wayland-green.svg)](https://wayland.freedesktop.org/)
[![Qt Version](https://img.shields.io/badge/Qt-6-41CD52.svg)](https://www.qt.io/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

**Android Emulator Dock (AED)** is an open-source, standalone Linux desktop application designed to host and manage multiple official Android Emulator instances within a unified, high-performance workspace.

Unlike traditional setups that attempt fragile X11 window reparenting or compositor nesting, AED communicates directly with official Android Emulator instances over authenticated **gRPC**. Frames are rendered via hardware-accelerated OpenGL surfaces inside a native Wayland client, and user inputs are routed through the emulator's official controller APIs.

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────┐
│                  Android Emulator Dock (AED)                    │
│                     Native Qt 6 / Wayland                        │
│                                                                  │
│  ┌──────────────────────────────┐ ┌───────────────────────────┐  │
│  │ Emulator Slot A (e.g. Phone) │ │ Emulator Slot B (Tablet)  │  │
│  │                              │ │                           │  │
│  │   QOpenGLWidget Surface      │ │   QOpenGLWidget Surface   │  │
│  │   streamScreenshot (~60 FPS) │ │   streamScreenshot        │  │
│  │   Touch / Mouse / Wheel      │ │   Touch / Mouse / Wheel   │  │
│  │                              │ │                           │  │
│  │   Toolbar & Extended Controls│ │   Toolbar & Ext Controls  │  │
│  └──────────────┬───────────────┘ └─────────────┬─────────────┘  │
│                 │                               │                │
│                 │ gRPC                          │ gRPC           │
└─────────────────┼───────────────────────────────┼────────────────┘
                  │                               │
          ┌───────▼────────┐              ┌───────▼────────┐
          │ Android        │              │ Android        │
          │ Emulator A     │              │ Emulator B     │
          │                │              │                │
          │ -qt-hide-window│              │ -qt-hide-window│
          │ -grpc-use-token│              │ -grpc-use-token│
          │ Pulse/PipeWire │              │ Pulse/PipeWire │
          └────────────────┘              └────────────────┘
```

### Key Highlights
- **Native Wayland Client**: Built on Qt 6 with zero dependence on X11 window reparenting (`XReparentWindow`), `XEmbed`, or nested Wayland compositors.
- **Official Emulator gRPC Streaming**: Receives display buffers directly using `EmulatorController.streamScreenshot` (RGBA8888) and displays them via a dedicated OpenGL viewport.
- **Complete Feature Parity**:
  - **Full Audio & Microphone Support**: Retains host PulseAudio / PipeWire sinks and sources for media playback and microphone input.
  - **Native Boot Animation**: Displays official Android boot animations without black frames.
  - **Compact Navigation Toolbar**: Instant access to `Back`, `Home`, `Recents`, `Power`, `Volume Up/Down`, `Rotate 90°`, and display `Screenshot`.
  - **"More" Official Controls Menu**: Direct invocation of official emulator Extended Controls panes (Location / Google Maps UI, Virtual Sensors, Battery, Cellular, Camera, Fingerprint, Fold/Posture, Snapshots, Screen Recording, etc.) via `UiController.showExtendedControls`.
- **Multi-Device Workspace**: Run and arrange multiple emulators side-by-side (Single, Two-Column, and 2x2 Grid layouts).
- **Android Studio Independent**: Completely standalone; does not require Android Studio to be installed or running.
- **Enterprise Security**: Authentication tokens are strictly isolated in memory and scrubbed from all logs and diagnostics.

---

## Prerequisites

Before running AED, ensure your Linux environment has:
- **Operating System**: Linux with Wayland desktop session (GNOME, KDE Plasma, Sway, Hyprland, etc.) or X11 fallback.
- **Python**: Version 3.10 or higher.
- **Android SDK**: Official Android SDK with command-line tools and emulator (`emulator >= 34.0.0`).
  - AED automatically discovers the SDK from `$ANDROID_HOME`, `$ANDROID_SDK_ROOT`, `PATH`, or standard Linux paths (`~/Android/Sdk`, `/opt/android-sdk`, etc.).
- **Host Audio**: PulseAudio or PipeWire with PulseAudio compatibility (`pipewire-pulse`).

---

## Installation & Setup

### 1. Clone Repository
```bash
git clone https://github.com/your-org/android-emulator-dock.git
cd android-emulator-dock
```

### 2. Set Up Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -e .
```
This installs the required dependencies (`PyQt6`, `grpcio`, `protobuf`) and registers the `android-emulator-dock` and `aed` console commands.

---

## Usage

### Launching AED
Run AED directly using the installed entrypoint:
```bash
android-emulator-dock
```
Or run as a module:
```bash
PYTHONPATH=src:proto python3 -m aed.main
```

### Quick Walkthrough
1. **Discovering AVDs**: Upon startup, AED automatically scans your Android SDK installation and populates the **AVD** dropdown on the top toolbar.
2. **Adding Emulators to Workspace**:
   - Select an AVD and click **+ Add to Workspace**.
   - Each emulator slot has its own controls, status badge, and frame rate counter.
3. **Starting Emulators**:
   - Click **Start** on an emulator slot.
   - AED boots the emulator headlessly, discovers its ephemeral gRPC port and token, and starts the video stream.
4. **Interaction**:
   - Click or drag inside the display area for touch events.
   - Use your mouse scroll wheel to trigger vertical or horizontal scrolling.
   - Type on your keyboard to forward key events.
   - Use the slot toolbar for Android navigation (`Back`, `Home`, `Recents`), hardware keys (`Volume`, `Power`), rotation, and screenshots.
5. **Advanced Settings & Location**:
   - Click **⋮ More ▾** to access official emulator tools (e.g. Google Maps Location simulation, battery charging levels, simulated incoming phone calls).
6. **Workspace Layouts**:
   - Switch between **Auto**, **Single**, **Two Columns**, and **Grid** using the top toolbar layout selector.

---

## Project Structure

```text
android-emulator-dock/
├── docs/
│   ├── architecture.md           # Deep architectural specification
│   └── development.md            # Detailed developer and testing guide
├── proto/                        # Compiled Python gRPC stubs
│   ├── emulator_controller_pb2.py
│   ├── emulator_controller_pb2_grpc.py
│   ├── ui_controller_service_pb2.py
│   └── ui_controller_service_pb2_grpc.py
├── src/aed/
│   ├── avd/                      # AVD discovery and INI parser
│   ├── connection/               # gRPC client, streaming thread, screenshot service
│   ├── emulator/                 # Process manager, lifecycle state machine, discovery
│   ├── logging_util/             # Secret-scrubbing structured logger
│   ├── platform/                 # SDK auto-discovery utilities
│   ├── renderer/                 # Hardware-accelerated QOpenGLWidget surface
│   ├── ui/                       # Main window, toolbars, dark theme & palettes
│   └── workspace/                # Multi-emulator slot and layout managers
├── tests/
│   ├── test_unit.py              # Unit tests for discovery, parsing, and states
│   ├── test_wayland.py           # Native Wayland client verification test
│   ├── test_integration.py       # Single emulator lifecycle & streaming integration test
│   ├── test_multi_emulator.py    # Simultaneous multi-instance isolation test
│   └── test_feature_parity.py    # Complete feature parity integration test
├── pyproject.toml                # Open-source packaging and metadata specification
├── LICENSE                       # Apache 2.0 License
├── README.md                     # Project documentation
└── PRD.md                        # Product requirements document
```

---

## Running the Test Suite

AED includes a comprehensive test suite covering unit tests, Wayland platform checks, and live emulator integration tests:

```bash
# Run all unit tests and Wayland verification
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_unit.py"
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_wayland.py"

# Run end-to-end integration and multi-emulator isolation tests (requires at least 2 AVDs)
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_integration.py"
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_multi_emulator.py"
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_feature_parity.py"
```

---

## Contributing

We welcome contributions from the community! To contribute:

1. **Fork the Repository** on GitHub.
2. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. **Make Your Changes**:
   - Adhere to the core principle: **host the official emulator via gRPC; do not reimplement emulator internals or use window embedding**.
   - Keep secrets/tokens redacted from all logs and diagnostics.
   - Maintain unit and integration tests for new functionality.
4. **Run Verification**:
   ```bash
   PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_*.py"
   ```
5. **Commit and Push**:
   ```bash
   git commit -m "feat: describe your change"
   git push origin feature/my-new-feature
   ```
6. **Open a Pull Request**.

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for complete details.
