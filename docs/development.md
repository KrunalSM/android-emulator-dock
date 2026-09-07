# Contributor & Development Guide

Thank you for contributing to **Android Emulator Dock (AED)**! This document provides technical context and guidelines to help you set up your development environment, run tests, and contribute effectively.

---

## 1. Architectural Philosophy

1. **Host, Don't Reimplement**:
   - The official emulator provides mature, hardware-accelerated emulation, sensors, network simulation, and extended UI.
   - Use official gRPC endpoints (`EmulatorController`, `UiController`) and extended controls rather than building custom clones.
2. **Native Wayland**:
   - Primary emulator display rendering MUST remain native Wayland.
   - Do NOT use X11 window reparenting (`XReparentWindow`), `XEmbed`, or nested Wayland compositors.
3. **No Singleton State**:
   - Every emulator instance must have independent processes, channels, tokens, frame queues, and renderers.
4. **Security**:
   - Authentication tokens must never be logged, printed to standard output, stored on disk, or exposed in UI strings.
   - Use `aed.logging_util.get_logger` for all logging.

---

## 2. Environment Setup

### Prerequisites
- Linux OS with Wayland session support
- Python 3.10+
- Android SDK with command-line tools & emulator
- Git

### Editable Installation
```bash
git clone https://github.com/your-org/android-emulator-dock.git
cd android-emulator-dock
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" || pip install -e .
```

---

## 3. Running the Application

Launch the dock:
```bash
android-emulator-dock
```
Or directly via Python:
```bash
PYTHONPATH=src:proto python3 -m aed.main
```

---

## 4. Testing & Verification

AED includes automated unit and integration tests:

### Unit Tests
Verify discovery parsers, state transitions, and secret scrubbing:
```bash
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_unit.py"
```

### Wayland Integration Test
Verify native Wayland client initialization:
```bash
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_wayland.py"
```

### End-to-End & Parity Tests
Verify headless emulator boot, gRPC frame streaming, input dispatch, Extended Controls, and screenshot service:
```bash
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_feature_parity.py"
```

### Multi-Instance Test
Verify two independent emulators streaming simultaneously:
```bash
PYTHONPATH=src:proto python3 -m unittest discover -s tests -p "test_multi_emulator.py"
```

---

## 5. Code Style & Submitting PRs

1. Follow PEP 8 guidelines.
2. Ensure new components are decoupled (e.g., UI must not depend directly on raw gRPC stubs; use `EmulatorConnection`).
3. Maintain test coverage for any new features or bug fixes.
4. Open a pull request with a descriptive title and summary of changes.
