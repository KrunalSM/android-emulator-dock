"""Integration test verifying two simultaneous emulator instances."""

import sys
import time
import unittest
from PyQt6.QtWidgets import QApplication

from aed.platform.sdk import find_android_sdk, get_emulator_binary
from aed.avd.discovery import list_avds
from aed.emulator.instance import EmulatorInstance
from aed.emulator.state import EmulatorState

class TestMultiEmulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_two_emulators_simultaneously(self):
        sdk_path = find_android_sdk()
        self.assertIsNotNone(sdk_path)
        emu_bin = get_emulator_binary(sdk_path)
        self.assertIsNotNone(emu_bin)

        avds = list_avds(emu_bin)
        self.assertGreaterEqual(len(avds), 2, "Need at least 2 AVDs for multi-emulator test")

        inst1 = EmulatorInstance(avd=avds[0], emulator_binary=emu_bin)
        inst2 = EmulatorInstance(avd=avds[1], emulator_binary=emu_bin)

        frames1 = []
        frames2 = []

        def on_f1(b, w, h, bpl):
            frames1.append((w, h))

        def on_f2(b, w, h, bpl):
            frames2.append((w, h))

        try:
            print(f"\nStarting Emulator 1: {avds[0].name}")
            inst1.start()
            print(f"Starting Emulator 2: {avds[1].name}")
            inst2.start()

            start_t = time.time()
            while time.time() - start_t < 45:
                self.app.processEvents()
                if inst1._stream_worker and on_f1 not in getattr(inst1, "_h", []):
                    inst1._stream_worker.frame_ready.connect(on_f1)
                    inst1._h = [on_f1]
                if inst2._stream_worker and on_f2 not in getattr(inst2, "_h", []):
                    inst2._stream_worker.frame_ready.connect(on_f2)
                    inst2._h = [on_f2]

                if inst1.state == EmulatorState.RUNNING and inst2.state == EmulatorState.RUNNING:
                    if len(frames1) >= 5 and len(frames2) >= 5:
                        break
                time.sleep(0.1)

            self.assertEqual(inst1.state, EmulatorState.RUNNING, "Instance 1 should be RUNNING")
            self.assertEqual(inst2.state, EmulatorState.RUNNING, "Instance 2 should be RUNNING")
            self.assertGreaterEqual(len(frames1), 5)
            self.assertGreaterEqual(len(frames2), 5)

            # Check distinct PIDs and ports
            self.assertNotEqual(inst1._pid, inst2._pid)
            self.assertNotEqual(inst1._discovery_info.grpc_port, inst2._discovery_info.grpc_port)

            # Test independent input
            inst1.surface.touch_down.emit(50, 50)
            inst2.surface.touch_down.emit(100, 100)
            self.app.processEvents()

            # Test stopping inst1 while inst2 continues running
            print("Stopping Instance 1, verifying Instance 2 remains RUNNING...")
            inst1.stop()
            self.assertEqual(inst1.state, EmulatorState.STOPPED)

            count_before = len(frames2)
            for _ in range(15):
                self.app.processEvents()
                time.sleep(0.1)

            self.assertEqual(inst2.state, EmulatorState.RUNNING, "Instance 2 must still be RUNNING")
            self.assertGreater(len(frames2), count_before, "Instance 2 must continue receiving frames")

        finally:
            inst1.stop()
            inst2.stop()
            self.app.processEvents()

if __name__ == "__main__":
    unittest.main()
