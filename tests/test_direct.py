import ast
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from iphone_assistant.commands import Command
from iphone_assistant.direct import execute
from iphone_assistant import direct, wda


class DirectTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backend = Mock()
        self.backend.ready.return_value = True
        self.backend.screenshot.side_effect = lambda p: p.write_bytes(b'image')
        self.command = Command('open_app', {'app_name': 'Cài đặt'})

    def run_action(self, **kwargs):
        return execute(self.command, self.backend, self.root,
                       confirmed=True, dry_run=False, **kwargs)

    def test_default_dry_run_and_cancellation_do_not_touch_backend(self):
        self.assertEqual(execute(self.command, self.backend, self.root).status, 'dry_run')
        self.assertEqual(execute(self.command, self.backend, self.root, dry_run=False).status, 'canceled')
        self.assertEqual(self.backend.mock_calls, [])

    def test_ambiguous_unsupported_and_stop_do_not_execute(self):
        for command, status in [(None, 'needs_clarification'),
                                (Command('stop'), 'canceled'),
                                (Command('open_app', {'app_name': 'Cài đặt rồi bật Wi-Fi'}), 'target_not_found'),
                                (Command('select_target', {'target': '1'}), 'needs_clarification')]:
            self.assertEqual(execute(command, self.backend, self.root, confirmed=True, dry_run=False).status, status)
        self.assertEqual(self.backend.mock_calls, [])

    def test_acknowledgement_never_means_verified(self):
        result = self.run_action()
        self.assertEqual(result.status, 'action_sent')
        self.assertTrue(result.action_acknowledged)
        self.backend.open_settings.assert_called_once()
        self.assertEqual(self.backend.screenshot.call_count, 2)

    def test_timeout_never_retries_or_verifies(self):
        self.backend.open_settings.side_effect = TimeoutError()
        verify = Mock()
        result = self.run_action(verify=verify)
        self.assertEqual(result.status, 'verification_uncertain')
        self.assertFalse(result.action_acknowledged)
        self.backend.open_settings.assert_called_once()
        verify.assert_not_called()

    def test_failure_before_action_stops(self):
        self.backend.ready.side_effect = ConnectionError()
        self.assertEqual(self.run_action().status, 'error')
        self.backend.open_settings.assert_not_called()

    def test_verification_results_and_errors(self):
        for decision, expected in [('found', 'verified_match'), ('not_found', 'verified_mismatch'),
                                   ('clarify', 'verification_uncertain')]:
            self.assertEqual(self.run_action(verify=lambda p: (decision, 'evidence')).status, expected)
        self.assertEqual(self.run_action(verify=Mock(side_effect=RuntimeError())).status, 'verification_uncertain')

    def test_fresh_evidence_and_no_previous_target_reuse(self):
        first = self.run_action()
        second = self.run_action()
        self.assertNotEqual(first.before_image, second.before_image)
        self.backend.reset_mock()
        self.assertEqual(execute(None, self.backend, self.root, confirmed=True, dry_run=False).status, 'needs_clarification')
        self.backend.open_settings.assert_not_called()

    def test_direct_modules_do_not_import_audio_or_legacy_executor(self):
        for module in (direct, wda):
            tree = ast.parse(Path(module.__file__).read_text(encoding='utf-8'))
            imports = [node.module or '' for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
            self.assertFalse(any(x.split('.')[-1] in {'tts', 'voice_control', 'numbered_vision', 'pyttsx3'} for x in imports))

    def test_transport_timeout_is_a_single_attempt(self):
        backend = object.__new__(wda.WDABackend)
        backend.tunnel = {'userspaceTunPort': 28101, 'address': '::1'}
        with patch.object(wda.socket, 'create_connection', side_effect=TimeoutError()) as connect:
            with self.assertRaises(TimeoutError):
                backend.open_settings()
            connect.assert_called_once()


if __name__ == '__main__':
    unittest.main()
