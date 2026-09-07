"""Unit tests for Android Emulator Dock components."""

import unittest
import tempfile
from pathlib import Path
from PyQt6.QtCore import QRectF, QPointF
from aed.logging_util import SecretScrubbingFormatter
from aed.avd.discovery import parse_ini_file
from aed.emulator.discovery import parse_discovery_ini
from aed.emulator.state import EmulatorState
from aed.renderer.emulator_surface import EmulatorSurface

class TestSecretScrubbing(unittest.TestCase):
    def test_scrub_bearer_token(self):
        formatter = SecretScrubbingFormatter()
        import logging
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Sending header Bearer 123456789abcdef to server",
            args=(), exc_info=None
        )
        res = formatter.format(record)
        self.assertNotIn("123456789abcdef", res)
        self.assertIn("Bearer [REDACTED]", res)

    def test_scrub_ini_token(self):
        formatter = SecretScrubbingFormatter()
        import logging
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Parsed config grpc.token=secret_token_value_abc",
            args=(), exc_info=None
        )
        res = formatter.format(record)
        self.assertNotIn("secret_token_value_abc", res)
        self.assertIn("grpc.token=[REDACTED]", res)

class TestIniParsing(unittest.TestCase):
    def test_parse_ini_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".ini", delete=False) as f:
            f.write("# comment\nkey1 = value1\nkey2=value2\n; comment 2\n")
            path = Path(f.name)
        try:
            res = parse_ini_file(path)
            self.assertEqual(res["key1"], "value1")
            self.assertEqual(res["key2"], "value2")
        finally:
            path.unlink()

class TestDiscoveryIni(unittest.TestCase):
    def test_parse_discovery_ini(self):
        with tempfile.NamedTemporaryFile("w", prefix="pid_99999_", suffix=".ini", delete=False) as f:
            f.write("grpc.port=8554\ngrpc.token=secret123\navd.id=TestAVD\nport.serial=5554\n")
            path = Path(f.name)
        try:
            # rename to exact pid_99999.ini
            target = path.parent / "pid_99999.ini"
            path.rename(target)
            info = parse_discovery_ini(target)
            self.assertIsNotNone(info)
            self.assertEqual(info.pid, 99999)
            self.assertEqual(info.grpc_port, 8554)
            self.assertEqual(info.grpc_token, "secret123")
            self.assertEqual(info.avd_id, "TestAVD")
            self.assertEqual(info.port_serial, 5554)
        finally:
            if target.exists():
                target.unlink()

class TestStateTransitions(unittest.TestCase):
    def test_states(self):
        self.assertTrue(EmulatorState.STOPPED.can_start())
        self.assertTrue(EmulatorState.FAILED.can_start())
        self.assertFalse(EmulatorState.RUNNING.can_start())
        self.assertTrue(EmulatorState.RUNNING.is_active())
        self.assertTrue(EmulatorState.BOOTING.is_active())
        self.assertFalse(EmulatorState.STOPPED.is_active())

if __name__ == "__main__":
    unittest.main()
