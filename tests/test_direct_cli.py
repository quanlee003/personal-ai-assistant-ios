import contextlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from iphone_assistant import direct_cli as cli
from iphone_assistant.direct import ActionResult
from iphone_assistant.commands import Command


class DirectCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.enterContext(patch.object(cli, 'PROJECT_ROOT', self.root))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))

    def test_final_results_are_separate_and_do_not_store_transcripts(self):
        with patch.object(cli, 'run_turn', return_value=ActionResult('verified_match', 'matched')):
            cli.run_logged_turn(None, 'private transcript')
            cli.run_logged_turn(None, 'another transcript')
        records = list(self.root.rglob('result.json'))
        self.assertEqual(len(records), 2)
        for record in records:
            data = json.loads(record.read_text(encoding='utf-8'))
            self.assertEqual(data['status'], 'verified_match')
            self.assertIn('finished_at', data)
            self.assertNotIn('transcript', record.read_text(encoding='utf-8'))

    def test_interrupted_turn_keeps_incomplete_record(self):
        with patch.object(cli, 'run_turn', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                cli.run_logged_turn(None)
        data = json.loads(next(self.root.rglob('result.json')).read_text(encoding='utf-8'))
        self.assertEqual(data['status'], 'incomplete')
        self.assertNotIn('finished_at', data)

    def test_initial_write_failure_prevents_any_work(self):
        with patch.object(Path, 'mkdir', side_effect=OSError), patch.object(cli, 'run_turn') as run:
            with self.assertRaises(OSError):
                cli.run_logged_turn(None)
            run.assert_not_called()

    def test_final_write_failure_does_not_replay_action(self):
        with patch.object(Path, 'replace', side_effect=[None, OSError]), patch.object(
                cli, 'run_turn', return_value=ActionResult('action_sent', 'sent')) as run:
            with self.assertRaises(SystemExit):
                cli.run_logged_turn(None)
            run.assert_called_once()

    def test_session_uses_fresh_requests_and_stops_on_uncertainty(self):
        with patch('sys.argv', ['direct_cli', '--session']), patch('builtins.input', side_effect=[
                'mở Cài đặt', 'mơ hồ', 'mở Cài đặt']), patch.object(cli, 'run_logged_turn', side_effect=[
                    ActionResult('dry_run', ''), ActionResult('needs_clarification', ''),
                    ActionResult('verification_uncertain', '')]) as run:
            with self.assertRaises(SystemExit) as exit_result:
                cli.main()
            self.assertEqual(exit_result.exception.code, 1)
            self.assertEqual([call.args[1] for call in run.call_args_list],
                             ['mở Cài đặt', 'mơ hồ', 'mở Cài đặt'])

    def test_quit_and_turn_limit(self):
        for responses, expected in [(['/quit'], 0), (['mở Cài đặt'], 1)]:
            with patch('sys.argv', ['direct_cli', '--session', '--max-turns', '1']), patch(
                    'builtins.input', side_effect=responses), patch.object(cli, 'run_logged_turn',
                    return_value=ActionResult('dry_run', '')) as run:
                cli.main()
                self.assertEqual(run.call_count, expected)

    def test_offline_preview_and_cancel_never_construct_backend(self):
        args = SimpleNamespace(listen=False, ai=False, execute=False, verify=False)
        with patch('iphone_assistant.wda.WDABackend') as backend:
            self.assertEqual(cli.run_turn(args, 'mở Cài đặt').status, 'dry_run')
            args.execute = True
            with patch('builtins.input', return_value=''):
                self.assertEqual(cli.run_turn(args, 'mở Cài đặt').status, 'canceled')
            backend.assert_not_called()

    def voice_mocks(self, transcript):
        record = self.enterContext(patch('iphone_assistant.speech.record_wav', return_value=b'audio'))
        transcribe = self.enterContext(patch('iphone_assistant.speech.transcribe_vietnamese', return_value=transcript))
        backend = self.enterContext(patch('iphone_assistant.wda.WDABackend'))
        return record, transcribe, backend

    def test_voice_correction_replaces_transcript_before_ai(self):
        record, transcribe, backend = self.voice_mocks('mở mở cái đất')
        args = SimpleNamespace(listen=True, ai=True, execute=True, verify=False)
        intent = SimpleNamespace(decision='action', command=Command('open_app', {'app_name': 'Settings'}))
        with patch('builtins.input', side_effect=['mở Cài đặt', 'y', '']), patch(
                'iphone_assistant.intent.understand_intent', return_value=intent) as understand:
            self.assertEqual(cli.run_turn(args).status, 'canceled')
            understand.assert_called_once_with('mở Cài đặt', system_prompt=cli.DIRECT_PROMPT)
        record.assert_called_once()
        transcribe.assert_called_once_with(b'audio')
        backend.assert_not_called()  # Correction does not authorize execution.

    def test_voice_enter_preserves_transcript_and_scope_validation(self):
        self.voice_mocks('mở Cài đặt')
        args = SimpleNamespace(listen=True, ai=False, execute=False, verify=False)
        with patch('builtins.input', return_value='   '):
            self.assertEqual(cli.run_turn(args).status, 'dry_run')
        with patch('builtins.input', return_value='mở Cài đặt rồi bật Wi-Fi'):
            self.assertNotEqual(cli.run_turn(args).status, 'dry_run')

    def test_voice_review_cancel_or_interrupt_stops_before_ai(self):
        _, _, backend = self.voice_mocks('mở Cài đặt')
        args = SimpleNamespace(listen=True, ai=True, execute=True, verify=True)
        with patch('iphone_assistant.intent.understand_intent') as understand:
            for value in ['/cancel', '/QUIT', '/exit']:
                with patch('builtins.input', return_value=value):
                    self.assertEqual(cli.run_turn(args).status, 'canceled')
            for interruption in [KeyboardInterrupt, EOFError]:
                with patch('builtins.input', side_effect=interruption):
                    self.assertEqual(cli.run_turn(args).status, 'canceled')
            understand.assert_not_called()
            backend.assert_not_called()

    def test_correction_is_not_reused_on_next_voice_turn(self):
        self.voice_mocks('không rõ')
        args = SimpleNamespace(listen=True, ai=False, execute=False, verify=False)
        with patch('builtins.input', side_effect=['mở Cài đặt', '']):
            self.assertEqual(cli.run_turn(args).status, 'dry_run')
            self.assertEqual(cli.run_turn(args).status, 'needs_clarification')

    def test_auto_runs_and_verifies_without_any_keyboard_input(self):
        args = SimpleNamespace(auto=True, listen=True, ai=True, execute=True, verify=True,
                               voice_threshold=500, silence_seconds=1.2)
        intent = SimpleNamespace(decision='action', command=Command('open_app', {'app_name': 'Settings'}))
        with patch('builtins.input', side_effect=AssertionError('Unexpected prompt')), patch(
                'iphone_assistant.endpoint.record_until_silence', return_value=b'audio') as record, patch(
                'iphone_assistant.speech.transcribe_vietnamese', return_value='mở Cài đặt'), patch(
                'iphone_assistant.intent.understand_intent', return_value=intent), patch(
                'iphone_assistant.wda.WDABackend') as backend, patch(
                'iphone_assistant.verification.verify_screen',
                return_value=SimpleNamespace(status='found', message='matched')) as verify:
            backend.return_value.ready.return_value = True
            backend.return_value.screenshot.side_effect = lambda p: p.write_bytes(b'png')
            result = cli.run_turn(args)
            self.assertEqual(result.status, 'verified_match')
            backend.return_value.open_settings.assert_called_once()
            record.assert_called_once()
            verify.assert_called_once()

    def test_auto_ambiguity_and_out_of_scope_never_execute(self):
        args = SimpleNamespace(auto=True, listen=False, ai=True, execute=True, verify=True)
        for intent in [SimpleNamespace(decision='clarify', message='Nói lại?'),
                       SimpleNamespace(decision='action', command=Command('open_app', {'app_name': 'Mail'}))]:
            with patch('builtins.input', side_effect=AssertionError), patch(
                    'iphone_assistant.intent.understand_intent', return_value=intent), patch(
                    'iphone_assistant.wda.WDABackend') as backend:
                result = cli.run_turn(args, 'mở cái đất')
                self.assertIn(result.status, {'needs_clarification', 'target_not_found'})
                backend.assert_not_called()

    def test_auto_spoken_stop_does_not_call_ai(self):
        args = SimpleNamespace(auto=True, listen=False, ai=True, execute=True, verify=True)
        with patch('iphone_assistant.intent.understand_intent') as understand:
            self.assertEqual(cli.run_turn(args, 'dừng').status, 'canceled')
            understand.assert_not_called()

    def test_auto_session_has_no_turn_prompt_and_is_bounded(self):
        with patch('sys.argv', ['direct_cli', '--auto', '--max-turns', '2']), patch(
                'builtins.input', side_effect=AssertionError), patch.object(cli, 'run_logged_turn',
                return_value=ActionResult('verified_match', '')) as run:
            cli.main()
            self.assertEqual(run.call_count, 2)
            args = run.call_args.args[0]
            self.assertTrue(args.listen and args.execute and args.ai and args.verify)


if __name__ == '__main__':
    unittest.main()
