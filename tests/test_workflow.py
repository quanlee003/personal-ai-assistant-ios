"""Regression coverage for retained AI/PNG boundaries and the direct workflow."""
import contextlib
import io
import json
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from iphone_assistant import direct_cli, intent, vision
from iphone_assistant.commands import UnsupportedCommand, parse_command


def response(payload):
    return SimpleNamespace(choices=[SimpleNamespace(
        finish_reason='stop', message=SimpleNamespace(refusal=None, content=json.dumps(payload)))])


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(patch.object(direct_cli, 'PROJECT_ROOT', self.root))
        self.enterContext(patch.dict('os.environ', {'AI_GATEWAY_API_KEY': 'test-only'}))

    def test_auto_settings_and_battery_through_real_intent_and_verification(self):
        args = SimpleNamespace(auto=True, listen=True, ai=True, execute=True, verify=True,
                               voice_threshold=500, silence_seconds=1.2)
        for action, value, expected_steps in [('open_app', 'Settings', 1),
                                               ('select_target', 'settings.battery', 2)]:
            with self.subTest(action=action), patch('builtins.input', side_effect=AssertionError), patch(
                    'iphone_assistant.endpoint.record_until_silence', return_value=b'audio'), patch(
                    'iphone_assistant.speech.transcribe_vietnamese', return_value='test request'), patch(
                    'iphone_assistant.wda.WDABackend') as wda, patch.object(intent, 'OpenAI') as intent_api, patch.object(
                    vision, 'OpenAI') as vision_api:
                intent_api.return_value.__enter__.return_value.chat.completions.create.return_value = response({
                    'decision': 'action', 'action': action, 'direction': 'none', 'value': value, 'message': ''})
                vision_api.return_value.__enter__.return_value.chat.completions.create.return_value = response({
                    'status': 'found', 'screen_summary': 'Settings', 'target_description': value,
                    'target_location': 'heading', 'message': 'Expected heading visible'})
                backend = wda.return_value
                backend.ready.return_value = True
                backend.battery_page_visible.side_effect = [False, True]
                backend.find_battery.return_value = 'battery-element'
                # Header sufficient for the retained pre-upload validation; never sent to a service.
                backend.screenshot.side_effect = lambda p: p.write_bytes(
                    b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 1, 1))
                result = direct_cli.run_logged_turn(args)
                self.assertEqual(result.status, 'verified_match')
                self.assertEqual(result.steps_acknowledged, expected_steps)
                backend.open_settings.assert_called_once()
                self.assertEqual(backend.click_battery.call_count, expected_steps - 1)
                self.assertEqual(intent_api.call_args.kwargs['max_retries'], 0)
                self.assertEqual(vision_api.call_args.kwargs['max_retries'], 0)
                self.assertEqual(json.loads(next(self.root.glob(
                    'runtime/direct-results/*/result.json')).read_text(encoding='utf-8'))['status'], 'verified_match')

    def test_intent_schema_rejects_removed_actions(self):
        for action in ['swipe', 'enter_text', 'submit', 'go_home', 'show_numbers', 'show_names']:
            with self.assertRaises(ValidationError):
                intent.ModelIntent(decision='action', action=action, direction='none', value='', message='')

    def test_clarification_and_stop_keep_consistent_contract(self):
        clarify = intent.ModelIntent(decision='clarify', action='none', direction='none', value='', message='Which?')
        self.assertIsNone(intent.validate_intent(clarify).command)
        stop = intent.ModelIntent(decision='action', action='stop', direction='none', value='', message='')
        self.assertEqual(intent.validate_intent(stop).command.action, 'stop')
        with self.assertRaises(intent.IntentError):
            intent.validate_intent(clarify.model_copy(update={'value': 'unexpected'}))

    def test_legacy_text_commands_are_rejected(self):
        for request in ['vuốt sang phải', 'gõ hello', 'bấm số 5', 'tìm kiếm']:
            with self.assertRaises(UnsupportedCommand):
                parse_command(request)

    def test_invalid_png_never_reaches_gateway(self):
        for raw in [b'', b'not png', b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 0, 10)]:
            p = self.root / 'bad.png'
            p.write_bytes(raw)
            with patch.object(vision, 'OpenAI') as api, self.assertRaises(vision.VisionError):
                vision.observe_screen(p, 'Check Settings', system_prompt='verification')
            api.assert_not_called()

    def test_found_without_evidence_is_rejected(self):
        observation = vision.ScreenObservation(status='found', screen_summary='Settings',
            target_description='', target_location='', message='No evidence')
        with self.assertRaises(vision.VisionError):
            vision.validate_observation(observation)


if __name__ == '__main__':
    unittest.main()
