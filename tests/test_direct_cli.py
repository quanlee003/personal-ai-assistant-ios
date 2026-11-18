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


if __name__ == '__main__':
    unittest.main()
