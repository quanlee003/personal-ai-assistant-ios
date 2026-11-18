from pathlib import Path
import contextlib
import io
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from iphone_assistant.commands import Command
from iphone_assistant.direct import execute, parse_direct_command, is_battery, validate_command
from iphone_assistant.wda import WDABackend, TargetChangedError
from iphone_assistant import direct_cli
from iphone_assistant.speech import SpeechInputError


class BatteryTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backend = Mock()
        self.backend.ready.return_value = True
        self.backend.screenshot.side_effect = lambda p: p.write_bytes(b'png')
        self.backend.battery_page_visible.side_effect = [False, True]
        self.backend.find_battery.return_value = 'element'
        self.command = Command('select_target', {'target': 'settings.battery'})

    def run_action(self, **kwargs):
        return execute(self.command, self.backend, self.root, confirmed=True, dry_run=False, **kwargs)

    def test_parser_allows_only_complete_battery_requests(self):
        for phrase in ['mở Pin', 'mở phần Pin trong Cài đặt', 'mở mục Pin']:
            self.assertTrue(is_battery(parse_direct_command(phrase)))
        for phrase in ['mở phần Pin rồi bật tiết kiệm pin', 'mở pin và bật phần trăm pin']:
            try:
                command = parse_direct_command(phrase)
            except ValueError:
                continue
            self.assertIsNotNone(validate_command(command))

    def test_preview_and_cancellation_do_not_touch_device(self):
        self.assertEqual(execute(self.command, self.backend, self.root).status, 'dry_run')
        self.assertEqual(execute(self.command, self.backend, self.root, dry_run=False).status, 'canceled')
        self.assertEqual(self.backend.mock_calls, [])

    def test_two_steps_then_verification(self):
        result = self.run_action(verify=lambda p: ('found', 'Pin visible'))
        self.assertEqual(result.status, 'verified_match')
        self.assertEqual((result.steps_attempted, result.steps_acknowledged), (2, 2))
        self.backend.open_settings.assert_called_once()
        self.backend.click_battery.assert_called_once_with('element')
        self.assertTrue((Path(result.before_image).parent / 'before-click.png').is_file())

    def test_missing_target_reports_partial_launch_and_no_click(self):
        self.backend.find_battery.return_value = None
        verify = Mock()
        result = self.run_action(verify=verify)
        self.assertEqual(result.status, 'target_not_found')
        self.assertTrue(result.action_acknowledged)
        self.assertEqual(result.steps_acknowledged, 1)
        self.backend.click_battery.assert_not_called()
        verify.assert_not_called()

    def test_click_timeout_no_retry_and_partial_counts(self):
        self.backend.click_battery.side_effect = TimeoutError()
        verify = Mock()
        result = self.run_action(verify=verify)
        self.assertEqual(result.status, 'verification_uncertain')
        self.assertEqual((result.steps_attempted, result.steps_acknowledged), (2, 1))
        self.backend.click_battery.assert_called_once()
        verify.assert_not_called()

    def test_wrong_screen_after_click_never_calls_ai_or_retries(self):
        self.backend.battery_page_visible.side_effect = [False, False]
        verify = Mock()
        result = self.run_action(verify=verify)
        self.assertEqual(result.error_code, 'battery_page_unconfirmed')
        self.backend.click_battery.assert_called_once()
        verify.assert_not_called()

    def test_already_on_battery_does_not_click(self):
        self.backend.battery_page_visible.side_effect = [True, True]
        result = self.run_action()
        self.assertEqual(result.status, 'action_sent')
        self.assertEqual(result.steps_acknowledged, 1)
        self.backend.find_battery.assert_not_called()
        self.backend.click_battery.assert_not_called()


class BatteryBackendTests(unittest.TestCase):
    def setUp(self):
        self.backend = object.__new__(WDABackend)
        self.backend.session_id = 'fresh-session'
        self.backend._battery_element = 'fresh-element'
        self.backend.settings_foreground = Mock(return_value=True)
        self.backend.session_request = Mock()

    def test_no_or_multiple_matches_no_target(self):
        for matches in [[], [{'ELEMENT': 'a'}, {'ELEMENT': 'b'}]]:
            self.backend.session_request.return_value = {'value': matches}
            self.assertIsNone(self.backend.find_battery())
            self.assertIsNone(self.backend._battery_element)

    def test_click_revalidates_and_consumes_element(self):
        self.backend.session_request.side_effect = [
            {'value': 'com.apple.settings.battery'}, {'value': 'XCUIElementTypeButton'},
            {'value': True}, {'value': True}, {'value': None}]
        self.backend.click_battery('fresh-element')
        self.assertEqual(self.backend.session_request.call_args.args,
                         ('POST', '/element/fresh-element/click', {}))
        with self.assertRaises(TargetChangedError):
            self.backend.click_battery('fresh-element')
        self.assertEqual(self.backend.session_request.call_count, 5)

    def test_foreground_switch_blocks_click(self):
        self.backend.settings_foreground.return_value = False
        with self.assertRaises(TargetChangedError):
            self.backend.click_battery('fresh-element')
        self.backend.session_request.assert_not_called()

    def test_changed_attributes_block_click(self):
        self.backend.session_request.return_value = {'value': 'different-button'}
        with self.assertRaises(TargetChangedError):
            self.backend.click_battery('fresh-element')
        self.assertTrue(all(c.args[0] == 'GET' for c in self.backend.session_request.call_args_list))

    def test_battery_row_is_not_battery_page(self):
        for title, expected in [('Cài đặt', False), ('Pin', True), ('Battery', True)]:
            self.backend.session_request.return_value = {'value':
                f'<XCUIElementTypeApplication><XCUIElementTypeNavigationBar name="{title}" visible="true"/>'
                '<XCUIElementTypeButton name="com.apple.settings.battery"/></XCUIElementTypeApplication>'}
            self.assertEqual(self.backend.battery_page_visible(), expected)


class AudioDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def test_battery_intent_uses_battery_specific_verification(self):
        args = SimpleNamespace(auto=True, listen=False, ai=True, execute=True, verify=True)
        command = Command('select_target', {'target': 'settings.battery'})
        intent = SimpleNamespace(decision='action', command=command)
        def execute_checked(cmd, backend, output, **options):
            self.assertEqual(cmd, command)
            decision, _ = options['verify'](Path('after.png'))
            self.assertEqual(decision, 'found')
            from iphone_assistant.direct import ActionResult
            return ActionResult('verified_match', 'matched')
        with patch('builtins.input', side_effect=AssertionError('Unexpected prompt')), patch(
                'iphone_assistant.intent.understand_intent', return_value=intent), patch(
                'iphone_assistant.wda.WDABackend'), patch.object(direct_cli, 'execute', side_effect=execute_checked), patch(
                'iphone_assistant.verification.verify_screen',
                return_value=SimpleNamespace(status='found', message='matched')) as verify:
            self.assertEqual(direct_cli.run_turn(args, 'mở phần Pin trong Cài đặt').status, 'verified_match')
            self.assertIn('chỉ có hàng Pin trên trang chính chưa đủ', verify.call_args.args[1])

    def test_capture_reason_is_preserved_and_never_transcribed(self):
        args = SimpleNamespace(auto=True, listen=True, voice_threshold=500, silence_seconds=1.2)
        with patch('iphone_assistant.endpoint.record_until_silence', side_effect=SpeechInputError('local', code='no_speech')), patch(
                'iphone_assistant.speech.transcribe_vietnamese') as transcribe:
            result = direct_cli.run_turn(args)
            self.assertEqual(result.error_code, 'no_speech')
            self.assertFalse(result.action_attempted)
            transcribe.assert_not_called()

    def test_transcription_error_identifies_stage_without_exposing_exception(self):
        args = SimpleNamespace(auto=True, listen=True, voice_threshold=500, silence_seconds=1.2)
        with patch('iphone_assistant.endpoint.record_until_silence', return_value=b'audio'), patch(
                'iphone_assistant.speech.transcribe_vietnamese', side_effect=SpeechInputError('private-value')):
            result = direct_cli.run_turn(args)
            self.assertEqual(result.error_code, 'transcription_error')
            self.assertNotIn('private-value', result.message)


if __name__ == '__main__':
    unittest.main()
