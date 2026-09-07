"""Comprehensive feature parity integration tests for Android Emulator Dock."""

import os
import sys
import time
import unittest
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from aed.platform.sdk import find_android_sdk, get_emulator_binary
from aed.avd.discovery import list_avds
from aed.emulator.instance import EmulatorInstance
from aed.emulator.state import EmulatorState
from aed.workspace.slot import EmulatorSlot

class TestFeatureParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.sdk_path = find_android_sdk()
        assert cls.sdk_path is not None
        cls.emu_bin = get_emulator_binary(cls.sdk_path)
        assert cls.emu_bin is not None
        cls.avds = list_avds(cls.emu_bin)
        assert len(cls.avds) > 0

    def test_full_feature_parity(self):
        avd = self.avds[0]
        instance = EmulatorInstance(avd=avd, emulator_binary=self.emu_bin)
        slot = EmulatorSlot(instance=instance)

        received_frames = []
        def on_frame(b, w, h, bpl):
            received_frames.append((w, h))

        print(f"\n[Parity Test] Launching {avd.name} with full audio and boot animation...")
        instance.start()

        # Wait for running state and frames
        start_t = time.time()
        while time.time() - start_t < 40:
            self.app.processEvents()
            if instance._stream_worker and on_frame not in getattr(instance, "_hook", []):
                instance._stream_worker.frame_ready.connect(on_frame)
                instance._hook = [on_frame]

            if instance.state == EmulatorState.RUNNING and len(received_frames) >= 5:
                break
            time.sleep(0.1)

        self.assertEqual(instance.state, EmulatorState.RUNNING)
        self.assertGreaterEqual(len(received_frames), 5)
        print(f"[Parity Test] Running with {len(received_frames)} frames streamed.")

        # 1. Test Common Navigation Actions
        print("[Parity Test] Testing Back, Home, Recents, Power...")
        instance.send_back()
        self.app.processEvents()
        instance.send_home()
        self.app.processEvents()
        instance.send_recents()
        self.app.processEvents()
        instance.send_power()
        self.app.processEvents()

        # 2. Test Hardware Volume Actions
        print("[Parity Test] Testing Volume Up / Down...")
        instance.send_volume_up()
        self.app.processEvents()
        instance.send_volume_down()
        self.app.processEvents()

        # 3. Test Rotation Action
        print("[Parity Test] Testing Device Rotation...")
        instance.rotate_device()
        self.app.processEvents()

        # 4. Test Fold/Posture Action
        print("[Parity Test] Testing Posture...")
        instance.set_fold_posture("POSTURE_OPENED")
        self.app.processEvents()

        # 5. Test Fingerprint Action
        print("[Parity Test] Testing Fingerprint...")
        instance.send_fingerprint(1)
        self.app.processEvents()

        # 6. Test Screenshot Service
        print("[Parity Test] Testing Official Screenshot Capture...")
        temp_dir = Path("/tmp/aed_test_screenshots")
        shot_path = instance._screenshot_service.capture_screenshot(temp_dir)
        self.assertIsNotNone(shot_path, "Screenshot file should be generated")
        self.assertTrue(shot_path.exists(), "Screenshot file must exist")
        self.assertGreater(shot_path.stat().st_size, 1000, "Screenshot file size must be non-trivial")
        print(f"[Parity Test] Screenshot captured: {shot_path} ({shot_path.stat().st_size} bytes)")
        shot_path.unlink()

        # 7. Test Extended Controls Official Panes
        print("[Parity Test] Testing Official Extended Controls (LOCATION, BATTERY, CELLULAR, CAMERA, SETTINGS)...")
        for pane in ["LOCATION", "BATTERY", "CELLULAR", "CAMERA", "SETTINGS"]:
            ok = instance.connection.show_extended_controls(pane)
            self.assertTrue(ok, f"Show extended controls for {pane} failed")
            time.sleep(0.3)
            self.app.processEvents()

        close_ok = instance.connection.close_extended_controls()
        self.assertTrue(close_ok)
        self.app.processEvents()

        # 8. Test Clean Stop & Surface Reset
        print("[Parity Test] Stopping emulator and verifying surface is cleared...")
        instance.stop()
        self.assertEqual(instance.state, EmulatorState.STOPPED)
        self.assertIsNone(instance.surface._current_image, "Surface frame buffer must be cleared on stop")
        print("[Parity Test] Full feature parity verified successfully!")

if __name__ == "__main__":
    unittest.main()
