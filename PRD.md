# Android Emulator Dock

## 1. Product Summary

Android Emulator Dock is a standalone Linux desktop application that provides a dedicated workspace for running and managing multiple official Android Emulator instances inside a single application window.

The application is conceptually similar to Android Studio's **Running Devices / Embedded Emulator** experience, but:

* Android Studio is not required.
* The application is independent of Android Studio.
* The application's main UI is a native Wayland client.
* Official Android Emulator instances remain the actual emulator backend.
* Emulator video, touch, mouse, and keyboard interaction are handled through the emulator's gRPC interface.
* Official emulator functionality such as Location, Sensors, Battery, Cellular, Camera, etc. is exposed through the emulator's existing Extended Controls UI rather than reimplemented.

The application must not reimplement Android emulation.

---

# 2. Goals

## Primary Goals

1. Run official Android Emulator AVDs from a standalone application.
2. Display multiple emulator instances inside one application window.
3. Provide a clean, native Linux/Wayland application experience.
4. Render emulator frames efficiently using the official emulator gRPC streaming interface.
5. Forward mouse, touch, keyboard, and wheel input through the official gRPC interface.
6. Preserve the official Android Emulator Extended Controls.
7. Provide access to the official Location UI, including its existing map-based interface.
8. Manage emulator lifecycle:

   * Discover AVDs
   * Launch
   * Boot
   * Stop
   * Restart
   * Remove from workspace
9. Support multiple simultaneously running emulators.
10. Remain independent from Android Studio at runtime and build time.

---

# 3. Non-Goals

The application must NOT attempt to recreate functionality that the official emulator already provides.

Do not implement:

* A custom Android emulator
* A custom GPS/location system
* A custom Google Maps interface
* A custom sensor interface
* A custom battery interface
* A custom cellular interface
* A custom camera simulator
* A custom fingerprint UI
* A custom screenshot system
* A custom video recording system
* A custom emulator toolbar duplicating Android's controls
* X11 window reparenting as the primary rendering mechanism
* Nested Wayland compositor hosting
* ADB-based screenshot streaming

If the official emulator already exposes a feature through Extended Controls or gRPC, use that capability instead of recreating it.

---

# 4. Platform Scope

## Supported Platform

Linux only.

## Primary Display Protocol

Wayland.

The application must be implemented as a native Wayland desktop application through Qt.

X11/XWayland may exist on the system, but the application's primary emulator rendering path must not depend on X11 window embedding.

---

# 5. Technical Architecture

## High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                  Android Emulator Dock                     │
│                  Native Qt / Wayland                       │
│                                                             │
│  ┌─────────────────────────┐ ┌─────────────────────────┐   │
│  │ Emulator Slot A         │ │ Emulator Slot B         │   │
│  │                         │ │                         │   │
│  │  GPU-backed renderer    │ │  GPU-backed renderer    │   │
│  │  gRPC frame stream      │ │  gRPC frame stream      │   │
│  │                         │ │                         │   │
│  │  Touch / Mouse / Key    │ │  Touch / Mouse / Key    │   │
│  │                         │ │                         │   │
│  │  Extended Controls      │ │  Extended Controls      │   │
│  └────────────┬────────────┘ └────────────┬────────────┘   │
│               │                           │                │
│               │ gRPC                      │ gRPC           │
└───────────────┼───────────────────────────┼────────────────┘
                │                           │
        ┌───────▼────────┐         ┌───────▼────────┐
        │ Android        │         │ Android        │
        │ Emulator A     │         │ Emulator B     │
        │                │         │                │
        │ -qt-hide-window│         │ -qt-hide-window│
        │ -grpc-use-token│         │ -grpc-use-token│
        │ gfxstream      │         │ gfxstream      │
        └────────────────┘         └────────────────┘
```

---

# 6. Emulator Launch Architecture

Each emulator must be launched using the hosting-oriented flags:

```text
-qt-hide-window
-grpc-use-token
-idle-grpc-timeout 300
```

The application must not expose an emulator's main Qt window as its primary UI.

`-qt-hide-window` prevents the emulator's normal device window from being presented while keeping the emulator's internal functionality available.

`-grpc-use-token` enables authenticated gRPC communication.

`-idle-grpc-timeout` prevents abandoned emulator processes from remaining indefinitely alive without communication.

The implementation must verify the actual installed emulator version and capabilities rather than assuming that every future emulator release behaves identically.

---

# 7. Emulator Discovery

The application must independently locate the Android SDK and emulator installation.

It must not require Android Studio.

Possible sources include:

* `ANDROID_HOME`
* `ANDROID_SDK_ROOT`
* standard Linux SDK locations
* user-configured SDK path
* PATH lookup
* known emulator binary locations

The application should provide a settings option to explicitly select the Android SDK location if automatic discovery fails.

The implementation must not assume environment variables are already configured.

---

# 8. AVD Discovery

The application should discover available AVDs using the official emulator/SDK tooling.

The UI should show:

* AVD name
* AVD identifier
* Device/profile information where available
* Android version/API level where available
* Current running state
* Optional architecture/device metadata

Launching an AVD should use the official emulator executable.

Do not recreate AVD management internally.

---

# 9. gRPC Discovery

After launching an emulator, the application must discover its gRPC endpoint and authentication token.

The emulator creates discovery information in the user's runtime directory, for example:

```text
$XDG_RUNTIME_DIR/avd/running/
```

with files similar to:

```text
pid_<PID>.ini
```

The application should monitor this directory and detect newly launched emulator instances.

The discovery layer must extract information such as:

```text
grpc.port
grpc.token
port.serial
port.adb
avd.id
avd.name
emulator.version
```

Do not pass authentication tokens through command-line arguments.

---

# 10. Emulator Connection Layer

All emulator communication must be isolated behind a dedicated abstraction.

Suggested architecture:

```text
EmulatorManager
      │
      ├── EmulatorInstance
      │       │
      │       └── EmulatorConnection
      │               ├── GrpcTransport
      │               ├── FrameStream
      │               ├── InputController
      │               └── UiController
      │
      └── EmulatorDiscovery
```

The UI must never directly manipulate raw gRPC stubs.

This layer is important because the emulator gRPC interface contains experimental APIs and may change between emulator releases.

The protocol implementation must therefore be replaceable without redesigning the UI.

---

# 11. Rendering

## Primary Rendering Mechanism

Use:

```text
EmulatorController.streamScreenshot
```

to receive emulator frames.

The implementation should support the most efficient available transport.

The feasibility investigation demonstrated approximately 55 FPS streaming with zero dropped packets, and identified gRPC streaming as the preferred architecture.

The renderer should use GPU-backed rendering where practical.

Candidate Qt implementations:

* QOpenGLWidget
* QQuickItem / Qt Quick texture pipeline
* another appropriate Qt GPU-backed surface

The implementation agent should benchmark the available approaches and select the cleanest performant option.

Do not prematurely lock the renderer to one Qt class if a better implementation is discovered during the POC.

---

# 12. Frame Scaling and Resizing

The emulator stream must adapt to the size of its UI slot.

When an emulator panel changes size:

```text
UI slot size
      ↓
requested stream dimensions
      ↓
EmulatorController.streamScreenshot
      ↓
renderer
```

Avoid scaling huge frames on the CPU when the emulator can provide an appropriately sized frame.

Aspect ratio must be preserved.

The user should be able to resize the application and rearrange emulator slots without restarting the emulator.

---

# 13. Input

Input must be translated from Qt/Wayland events into official emulator gRPC input APIs.

Support:

### Touch

Use:

```text
sendTouch
streamInputEvent
```

Support:

* touch down
* touch move
* touch up
* multiple touch points

### Keyboard

Use:

```text
sendKey
```

Support:

* normal keyboard input
* modifiers
* hardware key codes where appropriate
* Unicode input where supported

### Mouse

Use:

```text
sendMouse
injectWheel
```

Support:

* left button
* right button
* middle button
* pointer movement
* wheel scrolling

Coordinate conversion must correctly account for:

* emulator frame dimensions
* widget dimensions
* aspect-ratio letterboxing
* device rotation

---

# 14. Extended Controls

The application must expose an action such as:

```text
⋮ / ⚙ / Extended Controls
```

which invokes the official emulator Extended Controls.

Use:

```text
UiController.showExtendedControls(...)
```

rather than recreating these controls.

The official Location UI must be preserved.

The feasibility investigation verified that the official Location/Sensor controls can be summoned even when the main emulator window is hidden.

---

# 15. Location

Location is explicitly an official-emulator feature.

Do NOT build:

* custom map
* custom route editor
* custom GPS simulator
* custom GPX/KML parser
* custom location injection protocol

Instead:

```text
Dock
  ↓
UiController
  ↓
Official Extended Controls
  ↓
Location
```

This preserves the emulator's existing Location functionality.

---

# 16. Wayland Strategy

Wayland is a first-class requirement.

The application must not depend on:

* XEmbed
* XReparentWindow
* X11 window IDs
* XWayland window parenting
* emulator window capture
* nested Wayland compositor hosting

The feasibility investigation found that the bundled emulator Qt runtime does not provide a Wayland platform plugin and therefore cannot be treated as a native Wayland client for direct embedding.

Therefore the architecture must be:

```text
Official Emulator
       │
       │ gRPC
       ▼
Native Wayland Dock
       │
       ▼
GPU-backed Qt renderer
```

The emulator's Extended Controls popup may still appear through XWayland because it is produced by the emulator's bundled Qt runtime. This is acceptable for the initial product because the primary emulator display remains inside the native Wayland application.

---

# 17. Multi-Emulator Support

The application must support multiple emulator instances simultaneously.

Each instance must have:

* independent emulator process
* independent gRPC channel
* independent token
* independent discovery record
* independent ADB connection
* independent renderer
* independent input routing
* independent lifecycle state

The architecture must never use global emulator connection state.

The feasibility investigation verified simultaneous emulator operation with independently allocated serial, ADB, and gRPC ports.

---

# 18. Workspace Layout

The initial UI should support at least:

### Single

```text
┌─────────────────────┐
│                     │
│     Emulator        │
│                     │
└─────────────────────┘
```

### Two-column

```text
┌──────────────┬──────────────┐
│              │              │
│ Emulator A   │ Emulator B   │
│              │              │
└──────────────┴──────────────┘
```

### Grid

```text
┌──────────────┬──────────────┐
│ Emulator A   │ Emulator B   │
├──────────────┼──────────────┤
│ Emulator C   │ Emulator D   │
└──────────────┴──────────────┘
```

The layout engine should be independent from emulator management.

Future layouts should be possible without modifying the emulator protocol layer.

---

# 19. Emulator Slot

Each slot should provide:

* emulator display
* AVD name
* connection state
* boot state
* optional FPS/debug information
* start/stop/restart actions
* Extended Controls action
* remove-from-workspace action

The UI should remain visually lightweight.

Avoid rebuilding Android Studio's entire IDE.

---

# 20. Emulator Lifecycle

States should include at least:

```text
Discovered
Launching
Starting
WaitingForGrpc
Connecting
Booting
Running
Stopping
Stopped
Failed
Disconnected
```

Cold boot may take approximately 10-15 seconds, while snapshot loading may be significantly faster. The UI must therefore provide a clear loading state rather than appearing frozen.

---

# 21. Existing Emulator Attachment

If practical, the application should support attaching to already-running official emulator instances discovered through the runtime directory.

This should be implemented only if it can be done reliably.

It is preferable to support it because it avoids unnecessarily restarting an already-running emulator.

However, it must not compromise the core launch workflow.

---

# 22. Error Handling

Errors must be understandable to users.

Examples:

```text
Android SDK not found.

Configure your Android SDK location in Settings.
```

```text
Unable to connect to emulator gRPC service.

The emulator may still be starting.
```

```text
Emulator exited unexpectedly.

View logs for details.
```

```text
This emulator version does not expose the required gRPC interface.
```

The application should retain useful diagnostic logs.

---

# 23. Logging

Provide structured application logs.

Recommended categories:

```text
app
avd
emulator
grpc
render
input
ui
wayland
```

Debug logging should make it possible to diagnose:

* emulator launch command
* PID
* discovery file
* gRPC endpoint
* connection state
* frame stream state
* frame dimensions
* input events
* Extended Controls requests
* emulator process termination

Never log gRPC authentication tokens.

---

# 24. Performance Requirements

Target:

* 60 FPS emulator display where emulator/device workload permits
* low input latency
* no unnecessary CPU-side frame conversion
* no unnecessary frame copies
* smooth resizing
* multiple emulators without blocking the UI thread

The UI thread must never perform blocking gRPC calls.

Each emulator should have asynchronous connection/streaming work.

---

# 25. Threading

A reasonable model:

```text
UI Thread
    │
    ├── Layout
    ├── Input event collection
    └── Rendering coordination

Per Emulator
    │
    ├── gRPC connection
    ├── Frame streaming
    ├── Input RPC
    └── Emulator process monitoring
```

The exact threading model may differ if Qt's asynchronous facilities provide a cleaner architecture.

The key requirement is that emulator communication must never block the UI.

---

# 26. Security

gRPC tokens must be treated as credentials.

Requirements:

* never display tokens in normal UI
* never write tokens to application logs
* never pass tokens through command-line arguments
* keep communication local to the emulator's intended endpoint
* use the emulator-provided authentication mechanism
* validate discovery information before connecting

---

# 27. Dependencies

Suggested stack:

```text
Language: C++20
UI: Qt 6
Build: CMake
RPC: gRPC
Protocol: official Android Emulator protobuf definitions
Platform: Linux / Wayland
```

The implementation agent may adjust the exact Qt UI technology between Qt Widgets and Qt Quick based on rendering benchmarks.

Avoid introducing large frameworks unless they solve a concrete requirement.

---

# 28. Project Structure

Suggested structure:

```text
android-emulator-dock/
├── CMakeLists.txt
├── README.md
├── LICENSE
├── docs/
│   ├── architecture.md
│   └── development.md
├── proto/
├── src/
│   ├── app/
│   ├── avd/
│   ├── emulator/
│   │   ├── EmulatorManager
│   │   ├── EmulatorInstance
│   │   ├── EmulatorConnection
│   │   ├── EmulatorDiscovery
│   │   ├── EmulatorProcess
│   │   ├── FrameStream
│   │   ├── InputController
│   │   └── UiController
│   ├── rendering/
│   ├── workspace/
│   ├── ui/
│   ├── platform/
│   └── logging/
├── tests/
└── tools/
```

The final structure may differ if the implementation agent has a better justified organization.

---

# 29. Development Phases

## Phase 0: Verified Emulator Integration

Before implementing the full UI:

1. Locate emulator executable.
2. Launch an AVD with hosting flags.
3. Discover the runtime `.ini`.
4. Extract gRPC endpoint/token.
5. Establish authenticated gRPC connection.
6. Stream frames.
7. Display frames in a minimal Qt Wayland application.
8. Send touch.
9. Send keyboard input.
10. Open official Extended Controls.
11. Verify Location UI.
12. Run two emulator instances simultaneously.

This phase must produce a working minimal vertical slice.

---

## Phase 1: Single Emulator

Implement:

* AVD discovery
* emulator launch
* gRPC discovery
* frame rendering
* input
* lifecycle
* Extended Controls
* loading/error states

---

## Phase 2: Workspace

Implement:

* emulator slots
* layouts
* adding/removing emulators
* resizing
* focus handling

---

## Phase 3: Multi-Emulator

Implement:

* multiple independent connections
* simultaneous rendering
* independent lifecycle
* resource management

---

## Phase 4: Polish

Implement:

* settings
* SDK path configuration
* logging
* keyboard shortcuts
* persistent workspace layout
* better error reporting
* performance diagnostics

---

# 30. Testing

Automated tests should cover:

### Unit Tests

* runtime discovery parser
* `.ini` parser
* AVD parsing
* lifecycle state transitions
* coordinate transformation
* layout calculations

### Integration Tests

* launch emulator
* discover gRPC
* authenticate
* receive frame
* send touch
* send key
* open Extended Controls
* close Extended Controls
* attach to running emulator where supported

### Multi-Instance Tests

* launch two AVDs
* connect both
* stream both
* interact with each independently
* stop one while the other remains active

### Wayland Tests

Test on at least one native Wayland desktop environment.

The application must not require emulator X11 window embedding for the primary display.

---

# 31. Acceptance Criteria

The MVP is successful when all of the following are true:

* [ ] Android Studio is not installed or required.
* [ ] The application discovers the Android SDK/emulator.
* [ ] The application discovers AVDs.
* [ ] The application launches an AVD using hosting mode.
* [ ] The emulator's normal desktop window does not need to be embedded.
* [ ] The emulator display appears inside the application's native Wayland window.
* [ ] Frames stream smoothly.
* [ ] Touch works.
* [ ] Keyboard input works.
* [ ] Mouse input works.
* [ ] Wheel input works.
* [ ] Emulator resizing works.
* [ ] Official Extended Controls can be opened.
* [ ] Official Location UI works.
* [ ] Two or more emulators can run simultaneously.
* [ ] Each emulator remains independently controllable.
* [ ] Emulator crashes/disconnects are handled gracefully.
* [ ] Authentication tokens are never exposed in logs.
* [ ] No X11 window reparenting is required for the main emulator display.

---

# 32. Compatibility Philosophy

The gRPC interface must be treated as an external integration boundary.

The application should:

1. Detect emulator capabilities.
2. Detect incompatible versions.
3. Fail gracefully when required APIs are unavailable.
4. Keep the protocol implementation isolated.
5. Avoid hardcoding assumptions about future emulator versions.

The feasibility investigation confirms that the architecture works with the tested official emulator version, but also identifies experimental/deprecation risk in parts of the gRPC interface.

---

# 33. Core Product Principle

The application should be **a host, not another emulator UI**.

Whenever the official emulator already provides functionality:

```text
USE IT.
```

Whenever Android Studio already communicates with the emulator through an official mechanism:

```text
PREFER THAT MECHANISM.
```

Whenever a feature would require recreating Google's emulator behavior:

```text
STOP AND REUSE THE OFFICIAL INTERFACE.
```

The value of Android Emulator Dock is the workspace, orchestration, Wayland-native presentation, and multi-device experience, not reinventing the Android Emulator.
