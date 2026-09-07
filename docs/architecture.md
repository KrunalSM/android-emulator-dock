# Android Emulator Dock (AED) Architecture

## 1. System Overview
Android Emulator Dock is a standalone Linux application that hosts multiple official Android Emulator instances inside a single native Wayland application window using Qt 6.

### Architectural Model: Official gRPC vs Window Embedding
```text
┌─────────────────────────────────────────────────────────────┐
│                  Android Emulator Dock                      │
│                  Native Qt 6 / Wayland                      │
│                                                             │
│  ┌─────────────────────────┐ ┌─────────────────────────┐   │
│  │ Emulator Slot A         │ │ Emulator Slot B         │   │
│  │                         │ │                         │   │
│  │  QOpenGLWidget Renderer │ │  QOpenGLWidget Renderer │   │
│  │  streamScreenshot       │ │  streamScreenshot       │   │
│  │  Touch / Mouse / Wheel  │ │  Touch / Mouse / Wheel  │   │
│  │                         │ │                         │   │
│  │  Extended Controls      │ │  Extended Controls      │   │
│  └────────────┬────────────┘ └────────────┬────────────┘   │
│               │                           │                │
│               │ gRPC                      │ gRPC           │
└───────────────┼───────────────────────────┼────────────────┘
                │                           │
        ┌───────▼────────┐         ┌───────▼────────┐
        │ Official       │         │ Official       │
        │ Android Emu A  │         │ Android Emu B  │
        │ -qt-hide-window│         │ -qt-hide-window│
        │ -grpc-use-token│         │ -grpc-use-token│
        │ gfxstream      │         │ gfxstream      │
        └────────────────┘         └────────────────┘
```

## 2. Core Decisions
- **NO Window Embedding**: No XEmbed, XReparentWindow, XWayland reparenting, or nested compositors.
- **Headless Hosting Mode**: Official emulator launched with:
  ```bash
  -qt-hide-window -grpc-use-token -idle-grpc-timeout 300 -no-audio -no-boot-anim
  ```
- **Discovery**: Automatically monitors `$XDG_RUNTIME_DIR/avd/running/pid_<PID>.ini` for `grpc.port`, `grpc.token`, serial, and ADB ports.
- **Security**: Authentication tokens are treated strictly as secrets, stored securely in memory, never written to disk, and redacted from all logging statements.
- **Official Extended Controls**: The Location UI (Google Maps route planner, GPS injection), Battery, Sensors, Cellular, etc. are invoked directly using `UiController.showExtendedControls(PaneEntry)`.

## 3. Subsystem Breakdown
1. **`aed.platform.sdk`**: Independently discovers Android SDK from custom settings, environment variables (`ANDROID_HOME`, `ANDROID_SDK_ROOT`), PATH, and standard Linux locations without assuming shell setup.
2. **`aed.avd`**: Discovers available AVDs and parses `.ini` configuration files.
3. **`aed.emulator.discovery`**: Watches for running AVD instance `.ini` discovery files in the runtime directory.
4. **`aed.connection.client`**: High-level abstraction over `EmulatorController` and `UiController` gRPC services.
5. **`aed.connection.stream_worker`**: Dedicated background `QThread` running asynchronous frame streaming, preventing any UI stalls.
6. **`aed.renderer.emulator_surface`**: Hardware-accelerated `QOpenGLWidget` performing letterboxing, aspect ratio scaling, and normalized coordinate translation for touch and mouse events.
7. **`aed.workspace`**: Visual emulator slots, layout management (Single, Two-Column, 2x2 Grid), status badges, and FPS counters.
