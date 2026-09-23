import os
import sys
from pathlib import Path

# Ensure repo src/ and proto/ are in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "proto"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QProcess, QProcessEnvironment, QSettings
from PyQt6.QtWidgets import QApplication

from aed.avd.model import AvdInfo
from aed.emulator.instance import EmulatorInstance
from aed.emulator.launcher import EmulatorLauncher, GpuMode
from aed.emulator.state import EmulatorState
from aed.ui.main_window import MainWindow
from aed.workspace.slot import EmulatorSlot


class TestGpuRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.app.setApplicationName("Android Emulator Dock")
        cls.app.setOrganizationName("AED")

    def setUp(self):
        # Ensure fresh QSettings for each test
        settings = QSettings("AED", "Android Emulator Dock")
        settings.remove("gpu_rendering")

    def tearDown(self):
        settings = QSettings("AED", "Android Emulator Dock")
        settings.remove("gpu_rendering")

    def test_gpu_mode_enum_and_defaults(self):
        self.assertEqual(GpuMode.from_string("automatic"), GpuMode.AUTOMATIC)
        self.assertEqual(GpuMode.from_string("default"), GpuMode.AUTOMATIC)
        self.assertEqual(GpuMode.from_string(""), GpuMode.AUTOMATIC)
        self.assertEqual(GpuMode.from_string(None), GpuMode.AUTOMATIC)
        self.assertEqual(GpuMode.from_string("unknown"), GpuMode.AUTOMATIC)

        self.assertEqual(GpuMode.from_string("nvidia"), GpuMode.NVIDIA)
        self.assertEqual(GpuMode.from_string("NVIDIA"), GpuMode.NVIDIA)
        self.assertEqual(GpuMode.from_string("nvidia gpu"), GpuMode.NVIDIA)
        self.assertEqual(GpuMode.from_string("gpu_nvidia"), GpuMode.NVIDIA)

        self.assertEqual(GpuMode.AUTOMATIC.display_name(), "Automatic / Default")
        self.assertEqual(GpuMode.NVIDIA.display_name(), "NVIDIA GPU")

    def test_build_arguments_default(self):
        args = EmulatorLauncher.build_arguments("Medium_Phone", GpuMode.AUTOMATIC)
        self.assertIn("-avd", args)
        self.assertIn("Medium_Phone", args)
        self.assertIn("-qt-hide-window", args)
        self.assertIn("-grpc-use-token", args)
        self.assertNotIn("-gpu", args)
        self.assertNotIn("host", args)

    def test_build_arguments_nvidia(self):
        args = EmulatorLauncher.build_arguments("Medium_Phone", GpuMode.NVIDIA)
        self.assertIn("-avd", args)
        self.assertIn("Medium_Phone", args)
        self.assertIn("-qt-hide-window", args)
        self.assertIn("-grpc-use-token", args)
        self.assertIn("-gpu", args)
        self.assertIn("host", args)
        gpu_idx = args.index("-gpu")
        self.assertEqual(args[gpu_idx + 1], "host")

    def test_build_process_environment_default(self):
        # Save baseline os.environ
        before_environ = dict(os.environ)

        env = EmulatorLauncher.build_process_environment(GpuMode.AUTOMATIC)
        # Should not have forced NVIDIA offload variables
        # And crucially, os.environ must NOT be modified
        self.assertEqual(dict(os.environ), before_environ)

    def test_build_process_environment_nvidia_isolated(self):
        # Save baseline os.environ
        before_environ = dict(os.environ)
        # Ensure our test process environment does not have them set globally
        os.environ.pop("__NV_PRIME_RENDER_OFFLOAD", None)
        os.environ.pop("__GLX_VENDOR_LIBRARY_NAME", None)

        env = EmulatorLauncher.build_process_environment(GpuMode.NVIDIA)
        self.assertEqual(env.value("__NV_PRIME_RENDER_OFFLOAD"), "1")
        self.assertEqual(env.value("__GLX_VENDOR_LIBRARY_NAME"), "nvidia")

        # Crucial check: os.environ of the parent process must NOT be modified!
        self.assertNotIn("__NV_PRIME_RENDER_OFFLOAD", os.environ)
        self.assertNotIn("__GLX_VENDOR_LIBRARY_NAME", os.environ)

    def test_nvidia_availability_check(self):
        # On this machine, NVIDIA device nodes or nvidia-smi exist
        available, reason = EmulatorLauncher.check_nvidia_availability()
        self.assertTrue(available)
        self.assertIsNone(reason)

    @patch("pathlib.Path.exists", return_value=False)
    @patch("shutil.which", return_value=None)
    def test_nvidia_availability_check_failure(self, mock_which, mock_exists):
        available, reason = EmulatorLauncher.check_nvidia_availability()
        self.assertFalse(available)
        self.assertIsNotNone(reason)
        self.assertIn("NVIDIA", reason)
        self.assertIn("Automatic / Default", reason)

    def test_multiple_emulators_independent_environments(self):
        """Verify multiple emulator instances receive independent process configurations."""
        proc_auto = EmulatorLauncher.create_process(GpuMode.AUTOMATIC)
        proc_nvidia1 = EmulatorLauncher.create_process(GpuMode.NVIDIA)
        proc_nvidia2 = EmulatorLauncher.create_process(GpuMode.NVIDIA)

        env_auto = proc_auto.processEnvironment()
        env_nv1 = proc_nvidia1.processEnvironment()
        env_nv2 = proc_nvidia2.processEnvironment()

        # Automatic has no nvidia variables
        self.assertFalse(env_auto.contains("__NV_PRIME_RENDER_OFFLOAD"))
        self.assertFalse(env_auto.contains("__GLX_VENDOR_LIBRARY_NAME"))

        # Both NVIDIA processes have their own environment copies
        self.assertEqual(env_nv1.value("__NV_PRIME_RENDER_OFFLOAD"), "1")
        self.assertEqual(env_nv1.value("__GLX_VENDOR_LIBRARY_NAME"), "nvidia")
        self.assertEqual(env_nv2.value("__NV_PRIME_RENDER_OFFLOAD"), "1")
        self.assertEqual(env_nv2.value("__GLX_VENDOR_LIBRARY_NAME"), "nvidia")

        # Parent process os.environ is still clean
        self.assertNotIn("__NV_PRIME_RENDER_OFFLOAD", os.environ)
        self.assertNotIn("__GLX_VENDOR_LIBRARY_NAME", os.environ)

    def test_emulator_instance_gpu_mode_behavior(self):
        avd = AvdInfo(name="TestAVD", id="TestAVD", path=None)
        dummy_bin = Path("/usr/bin/true")

        # 1. Default mode is AUTOMATIC
        inst = EmulatorInstance(avd=avd, emulator_binary=dummy_bin)
        self.assertEqual(inst.gpu_mode, GpuMode.AUTOMATIC)
        self.assertFalse(inst.has_custom_gpu_override)

        # 2. Can change GPU mode while stopped
        inst.gpu_mode = GpuMode.NVIDIA
        self.assertEqual(inst.gpu_mode, GpuMode.NVIDIA)

        # 3. Custom override flag
        inst.set_custom_gpu_mode(GpuMode.AUTOMATIC)
        self.assertEqual(inst.gpu_mode, GpuMode.AUTOMATIC)
        self.assertTrue(inst.has_custom_gpu_override)

        # 4. Cannot change GPU mode when RUNNING
        inst.state = EmulatorState.RUNNING
        inst.gpu_mode = GpuMode.NVIDIA
        self.assertEqual(inst.gpu_mode, GpuMode.AUTOMATIC)

    def test_fallback_when_nvidia_unavailable(self):
        avd = AvdInfo(name="TestAVD", id="TestAVD", path=None)
        dummy_bin = Path("/usr/bin/true")
        inst = EmulatorInstance(avd=avd, emulator_binary=dummy_bin, gpu_mode=GpuMode.NVIDIA)

        errors = []
        inst.error_occurred.connect(lambda msg: errors.append(msg))

        with patch.object(EmulatorLauncher, "check_nvidia_availability", return_value=(False, "NVIDIA unavailable")):
            inst.start()
            self.assertEqual(inst.state, EmulatorState.FAILED)
            self.assertEqual(len(errors), 1)
            self.assertIn("NVIDIA unavailable", errors[0])
            self.assertIsNone(inst._process)

        # User switches back to Automatic / Default and restarts
        inst.gpu_mode = GpuMode.AUTOMATIC
        self.assertTrue(inst.state.can_start())
        # With automatic, start proceeds past check
        mock_proc = MagicMock(spec=QProcess)
        mock_proc.waitForStarted.return_value = True
        mock_proc.processId.return_value = 12345
        mock_proc.state.return_value = QProcess.ProcessState.NotRunning
        with patch.object(EmulatorLauncher, "create_process", return_value=mock_proc):
            inst.start()
            self.assertEqual(inst.state, EmulatorState.WAITING_FOR_DISCOVERY)
            self.assertEqual(inst._pid, 12345)
            mock_proc.start.assert_called_once()
            args = mock_proc.start.call_args[0][1]
            self.assertNotIn("-gpu", args)
            inst.stop()

    def test_persistence_in_main_window(self):
        window = MainWindow()
        try:
            # Default is automatic
            self.assertEqual(window.current_gpu_mode, "automatic")
            self.assertEqual(window.gpu_combo.currentText(), "Automatic / Default")

            # Switch to NVIDIA
            idx_nv = window.gpu_combo.findData("nvidia")
            self.assertGreaterEqual(idx_nv, 0)
            window.gpu_combo.setCurrentIndex(idx_nv)
            self.assertEqual(window.current_gpu_mode, "nvidia")

            # Check QSettings
            settings = QSettings("AED", "Android Emulator Dock")
            self.assertEqual(settings.value("gpu_rendering"), "nvidia")

            # Close and reopen new window, verify it loads NVIDIA
            window2 = MainWindow()
            try:
                self.assertEqual(window2.current_gpu_mode, "nvidia")
                self.assertEqual(window2.gpu_combo.currentText(), "NVIDIA GPU")
            finally:
                window2.close()

            # Switch back to Automatic
            idx_auto = window.gpu_combo.findData("automatic")
            window.gpu_combo.setCurrentIndex(idx_auto)
            self.assertEqual(window.current_gpu_mode, "automatic")
            self.assertEqual(settings.value("gpu_rendering"), "automatic")
        finally:
            window.close()

    def test_toggle_behavior_preserves_running_instances(self):
        """Toggle behavior:
        Automatic -> NVIDIA -> Automatic
        New launches use the currently selected configuration.
        Already-running instances are not unexpectedly modified.
        """
        window = MainWindow()
        try:
            # Create two dummy AVDs
            avd1 = AvdInfo(name="AVD_1", id="AVD_1", path=None)
            avd2 = AvdInfo(name="AVD_2", id="AVD_2", path=None)

            dummy_bin = Path("/usr/bin/true")
            window._emulator_bin = dummy_bin

            # 1. Start with Automatic
            window.gpu_combo.setCurrentIndex(window.gpu_combo.findData("automatic"))
            inst1 = EmulatorInstance(avd=avd1, emulator_binary=dummy_bin, gpu_mode=window.current_gpu_mode)
            slot1 = EmulatorSlot(instance=inst1, parent=window.workspace)
            window.workspace.add_slot(slot1)

            # Slot 1 should have Automatic
            self.assertEqual(inst1.gpu_mode, GpuMode.AUTOMATIC)
            self.assertTrue(slot1.gpu_badge.isHidden())

            # Simulate inst1 is now RUNNING
            inst1.state = EmulatorState.RUNNING

            # 2. Toggle global setting to NVIDIA
            window.gpu_combo.setCurrentIndex(window.gpu_combo.findData("nvidia"))
            self.assertEqual(window.current_gpu_mode, "nvidia")

            # inst1 is RUNNING -> must remain RUNNING and retain AUTOMATIC!
            self.assertEqual(inst1.state, EmulatorState.RUNNING)
            self.assertEqual(inst1.gpu_mode, GpuMode.AUTOMATIC)

            # Add AVD 2 while NVIDIA is active
            inst2 = EmulatorInstance(avd=avd2, emulator_binary=dummy_bin, gpu_mode=window.current_gpu_mode)
            slot2 = EmulatorSlot(instance=inst2, parent=window.workspace)
            window.workspace.add_slot(slot2)

            # AVD 2 gets NVIDIA configuration
            self.assertEqual(inst2.gpu_mode, GpuMode.NVIDIA)
            self.assertFalse(slot2.gpu_badge.isHidden())

            # 3. Toggle global setting back to Automatic
            window.gpu_combo.setCurrentIndex(window.gpu_combo.findData("automatic"))
            self.assertEqual(window.current_gpu_mode, "automatic")

            # inst1 is still RUNNING with AUTOMATIC
            self.assertEqual(inst1.state, EmulatorState.RUNNING)
            self.assertEqual(inst1.gpu_mode, GpuMode.AUTOMATIC)

            # inst2 was STOPPED, so it updates to Automatic!
            self.assertEqual(inst2.gpu_mode, GpuMode.AUTOMATIC)
            self.assertTrue(slot2.gpu_badge.isHidden())

            # 4. If inst2 has custom override set via slot menu
            slot2._set_gpu_mode(GpuMode.NVIDIA)
            self.assertEqual(inst2.gpu_mode, GpuMode.NVIDIA)
            self.assertFalse(slot2.gpu_badge.isHidden())
            self.assertTrue(inst2.has_custom_gpu_override)

            # Toggling global setting again will NOT overwrite inst2's custom override
            window.gpu_combo.setCurrentIndex(window.gpu_combo.findData("automatic"))
            self.assertEqual(inst2.gpu_mode, GpuMode.NVIDIA)
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
