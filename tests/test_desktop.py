import contextlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from queue import Queue
import tkinter as tk

from iphone_assistant.desktop_controller import DesktopController, Readiness, check_readiness
from iphone_assistant.direct import ActionResult, execute
from iphone_assistant.commands import Command
from iphone_assistant.direct_cli import run_turn
from iphone_assistant.desktop import DesktopApp

READY = Readiness(True, True, True, 'phone', 'mic', 'config')


class DesktopTests(unittest.TestCase):
    def finish(self, controller):
        controller._worker.join(2)
        self.assertFalse(controller.busy)
        events = []
        while not controller.events.empty():
            events.append(controller.events.get_nowait())
        return events

    def test_readiness_does_not_record_or_call_cloud(self):
        with patch('sounddevice.query_devices', return_value={'name': 'mic', 'default_samplerate': 48000}), patch(
                'sounddevice.check_input_settings'), patch('sounddevice.RawInputStream') as stream, patch(
                'iphone_assistant.desktop_controller.WDABackend') as backend, patch.dict(
                'os.environ', {'DEEPGRAM_API_KEY': 'test', 'AI_GATEWAY_API_KEY': 'test'}):
            backend.return_value.ready.return_value = True
            self.assertTrue(check_readiness().ready)
            stream.assert_not_called()

    def test_missing_prerequisite_prevents_runner(self):
        runner = Mock()
        controller = DesktopController(preflight=lambda _: Readiness(False, True, True, '', '', ''), runner=runner)
        controller.start()
        self.assertIn(('finished', 'not_ready'), self.finish(controller))
        runner.assert_not_called()

    def test_single_worker_and_stop_waits_for_inflight_request(self):
        entered, release = Event(), Event()
        def runner(*args, **kwargs):
            entered.set()
            release.wait(2)
            return ActionResult('verified_match', '')
        controller = DesktopController(preflight=lambda _: READY, runner=Mock(side_effect=runner))
        controller.start(5)
        self.assertTrue(entered.wait(1))
        try:
            self.assertFalse(controller.start())
            self.assertFalse(controller.refresh())
            controller.stop()
            self.assertTrue(controller.busy)
        finally:
            release.set()
        self.assertIn(('finished', 'canceled'), self.finish(controller))
        self.assertEqual(controller._runner.call_count, 1)

    def test_uncertainty_or_persistence_failure_halts_session(self):
        for outcome in [ActionResult('verification_uncertain', '', True), SystemExit(1)]:
            runner = Mock(side_effect=outcome if isinstance(outcome, BaseException) else None,
                          return_value=outcome)
            controller = DesktopController(preflight=lambda _: READY, runner=runner)
            controller.start(5)
            events = self.finish(controller)
            self.assertEqual(runner.call_count, 1)
            self.assertIn(('finished', 'error' if isinstance(outcome, BaseException) else 'halted'), events)

    def test_stop_after_capture_does_not_submit_audio(self):
        stop = Event()
        def capture(**kwargs):
            stop.set()
            return b'audio'
        args = SimpleNamespace(auto=True, listen=True, ai=True, execute=True, verify=True,
                               voice_threshold=500, silence_seconds=1.2)
        with patch('iphone_assistant.endpoint.record_until_silence', side_effect=capture), patch(
                'iphone_assistant.speech.transcribe_vietnamese') as transcribe:
            self.assertEqual(run_turn(args, stop_event=stop).status, 'canceled')
            transcribe.assert_not_called()

    def test_stop_after_intent_prevents_device_work(self):
        stop = Event()
        def intent(*args, **kwargs):
            stop.set()
            return SimpleNamespace(decision='action', command=Command('open_app', {'app_name': 'Settings'}))
        args = SimpleNamespace(auto=True, listen=False, ai=True, execute=True, verify=True)
        with patch('iphone_assistant.intent.understand_intent', side_effect=intent), patch(
                'iphone_assistant.wda.WDABackend') as backend, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_turn(args, 'open settings', stop_event=stop).status, 'canceled')
            backend.assert_not_called()

    def test_stop_after_launch_marks_uncertain_and_never_clicks(self):
        stop = Event()
        backend = Mock()
        backend.ready.return_value = True
        backend.screenshot.side_effect = lambda p: p.write_bytes(b'png')
        backend.open_settings.side_effect = stop.set
        with TemporaryDirectory() as folder:
            result = execute(Command('select_target', {'target': 'settings.battery'}), backend,
                             Path(folder), confirmed=True, dry_run=False, stop_event=stop)
        self.assertEqual(result.status, 'verification_uncertain')
        self.assertTrue(result.action_acknowledged)
        self.assertEqual(result.steps_attempted, 1)
        backend.click_battery.assert_not_called()


class DesktopWidgetTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.controller = Mock()
        self.controller.events = Queue()
        self.controller.busy = False
        self.app = DesktopApp(self.root, self.controller)

    def tearDown(self):
        for pending in self.root.tk.call('after', 'info'):
            self.root.after_cancel(pending)
        self.root.destroy()

    def test_controls_follow_readiness_and_stop_not_late_progress(self):
        self.assertIn('disabled', self.app.start_button.state())
        self.app._event('readiness', READY)
        self.app._event('finished', 'checked')
        self.assertNotIn('disabled', self.app.start_button.state())
        self.app.start_button.invoke()
        self.controller.start.assert_called_once_with(1)
        self.assertIn('disabled', self.app.start_button.state())
        self.app.stop_button.invoke()
        self.controller.stop.assert_called_once()
        stopped_text = self.app.phase.cget('text')
        self.app._event('executing', 'late progress')
        self.assertEqual(self.app.phase.cget('text'), stopped_text)
        self.assertIn('disabled', self.app.start_button.state())
        self.app._event('finished', 'canceled')
        self.assertNotIn('disabled', self.app.start_button.state())

    def test_new_turn_cannot_show_previous_transcript_or_record(self):
        self.app._event('transcript', 'old request')
        self.app._event('record', 'old/result.json')
        self.app._event('turn', (2, 2))
        self.app._event('result', ActionResult('error', 'no speech'))
        self.assertNotIn('old request', self.app.result_text.get('1.0', 'end'))
        self.assertIsNone(self.app.last_record)
        self.assertIn('disabled', self.app.record_button.state())

    def test_screen_read_is_explicit_local_default_and_clears_old_result(self):
        self.controller.read_screen.assert_not_called()
        self.app._event('readiness', READY)
        self.app._event('finished', 'checked')
        self.app._event('record', 'old/result.json')
        self.app.read_button.invoke()
        self.controller.read_screen.assert_called_once_with(use_ai=False)
        self.assertIn('disabled', self.app.start_button.state())
        self.assertIsNone(self.app.last_record)
        self.app._event('screen_report', {'status': 'unavailable', 'message': 'Phone locked'})
        self.assertIn('Phone locked', self.app.result_text.get('1.0', 'end'))
        self.app._event('finished', 'screen_read')
        self.assertNotIn('disabled', self.app.read_button.state())


if __name__ == '__main__':
    unittest.main()
