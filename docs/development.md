# Development & Testing Guide

## Prerequisites
- Linux OS (Tested on Wayland desktop, e.g. Fedora 44)
- Python 3.10+
- Qt 6 (PyQt6 6.10+)
- `grpcio`, `grpcio-tools`, `protobuf`
- Official Android SDK with command-line tools & emulator (`>= 34.0.0`)

## Project Structure
```text
AED/
├── bin/
│   └── android-emulator-dock    # Executable launcher script
├── docs/
│   ├── architecture.md          # Architectural specification
│   └── development.md           # Development & testing guide
├── proto/                       # Precompiled gRPC Python stubs
├── src/aed/
│   ├── avd/                     # AVD discovery and models
│   ├── connection/              # gRPC client & streaming thread
│   ├── emulator/                # Emulator lifecycle, process, discovery
│   ├── logging_util/            # Secret-scrubbing logger
│   ├── platform/                # SDK path detection
│   ├── renderer/                # QOpenGLWidget hardware surface
│   ├── ui/                      # Main window & toolbars
│   └── workspace/               # Workspace layouts & slots
├── tests/                       # Unit & integration tests
├── PRD.md
└── README.md
```

## Running Tests
Run all unit and integration tests:
```bash
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_*.py"
```

## Running the Application
```bash
./bin/android-emulator-dock
```
