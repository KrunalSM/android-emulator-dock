"""Integration test for launching official emulator, gRPC streaming, and input handling."""

import os
import sys
import time
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from aed.platform.sdk import find_android_sdk, get_emulator_binary
from aed.avd.discovery import list_avds
from aed.emulator.instance import EmulatorInstance
from aed.emulator.state import EmulatorState

class TestEmulatorIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create single QApplication instance for Qt tests
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_emulator_launch_stream_and_input(self):
        sdk_path = find_android_sdk()
        self.assertIsNotNone(sdk_path, "Android SDK must be found")
        emu_bin = get_emulator_binary(sdk_path)
        self.assertIsNotNone(emu_bin, "Emulator binary must be found")

        avds = list_avds(emu_bin)
        self.assertTrue(len(avds) > 0, "At least one AVD must be available")
        avd = avds[0]

        instance = EmulatorInstance(avd=avd, emulator_binary=emu_bin)

        received_frames = []
        state_history = []

        def on_frame(b, w, h, bpl):
            received_frames.append((w, h))

        def on_state(state):
            state_history.append(state)

        instance.surface.touch_down.connect(lambda x, y: None)
        instance.state_changed.connect(on_state)

        # Connect internal worker frame signal
        def on_worker_ready():
            if instance._stream_worker:
                instance._stream_worker.frame_ready.connect(on_frame)

        # Launch emulator
        instance.start()
        self.assertIn(instance.state, (EmulatorState.LAUNCHING, EmulatorState.WAITING_FOR_DISCOVERY))

        # Wait up to 35 seconds for RUNNING state and at least 1 frame
        start_time = time.time()
        while time.time() - start_time < 35:
            self.app.processEvents()
            if instance._stream_worker and on_frame not in getattr(instance, "_hooked", []):
                instance._stream_worker.frame_ready.connect(on_frame)
                instance._hooked = [on_frame]

            if instance.state == EmulatorState.RUNNING and len(received_frames) >= 1:
                break
            time.sleep(0.1)

        self.assertEqual(instance.state, EmulatorState.RUNNING, f"Emulator should reach RUNNING state. States: {state_history}")
        self.assertTrue(len(received_frames) >= 1, "Must have received at least 1 frame")

        # Test touch forwarding
        instance.surface.touch_down.emit(100, 200)
        instance.surface.touch_move.emit(120, 220)
        instance.surface.touch_up.emit(120, 220)
        self.app.processEvents()

        # Test wheel
        instance.surface.wheel_scrolled.emit(0, 120)
        self.app.processEvents()

        # Test Extended Controls (LOCATION)
        self.assertIsNotNone(instance._connection)
        show_res = instance._connection.show_extended_controls("LOCATION")
        self.assertTrue(show_res, "showExtendedControls(LOCATION) should succeed")
        time.sleep(1.0)
        self.app.processEvents()

        close_res = instance._connection.close_extended_controls()
        self.assertTrue(close_res, "closeExtendedControls() should succeed")
        self.app.processEvents()

        # Stop emulator
        instance.stop()
        self.assertEqual(instance.state, EmulatorState.STOPPED)
        logger_info = f"States: {state_history}, frames received: {len(received_frames)}"
        print(f"\n[Integration Success] {logger_info}")

if __name__ == "__main__":
    unittest.main()
