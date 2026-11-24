import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import Mock, patch

from iphone_assistant.control import RunCanceled
from iphone_assistant.screen_reader import parse_screen, read_screen, describe_report
from iphone_assistant.wda import WDABackend

XML = '''<root><XCUIElementTypeApplication name="Clock" visible="true">
<XCUIElementTypeNavigationBar name="Timers" visible="true"/>
<XCUIElementTypeButton label="Start" visible="true" enabled="true"/>
<XCUIElementTypeButton label="Hidden" visible="false" enabled="true"/>
<XCUIElementTypeTextField label="Label" value="private value" visible="true" enabled="true"/>
<XCUIElementTypeStaticText label="Current timer" visible="true"/>
</XCUIElementTypeApplication></root>'''


class ScreenReaderTests(unittest.TestCase):
    def test_observation_session_has_no_launch_target(self):
        backend = WDABackend.__new__(WDABackend)
        backend.request = Mock(return_value={'sessionId': 'observe'})
        backend.observe_current_app()
        backend.request.assert_called_once_with('POST', '/session', {
            'capabilities': {'alwaysMatch': {'shouldTerminateApp': False}}})
        self.assertEqual(backend.session_id, 'observe')

    def test_cancel_during_ai_does_not_save_completed_report(self):
        stop = Event()
        def cancel(*args, **kwargs):
            stop.set()
            raise RuntimeError('interrupted')
        with patch('iphone_assistant.vision.observe_screen', side_effect=cancel):
            with self.assertRaises(RunCanceled):
                self.read(use_ai=True, stop_event=stop)
        self.assertFalse(list(self.folder.rglob('report.json')))

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.backend = Mock()
        self.backend.request.side_effect = self.request

    def request(self, method, path, *args):
        self.assertEqual(method, 'GET')
        return {'value': {'/wda/locked': False, '/wda/activeAppInfo': {'bundleId': 'clock'}, '/source': XML}[path]}

    def read(self, **kw):
        return read_screen(backend_factory=lambda: self.backend, folder=self.folder, **kw)

    def test_visible_controls_and_no_input_values(self):
        data = parse_screen(XML)
        self.assertEqual(data['page'], 'Timers')
        self.assertEqual(len(data['controls']), 2)
        self.assertNotIn('private value', json.dumps(data))
        self.assertNotIn('Hidden', json.dumps(data))

    def test_local_read_only_no_cloud_or_screenshot(self):
        with patch('iphone_assistant.vision.observe_screen') as ai:
            data = self.read()
        self.assertEqual(data['status'], 'read')
        self.assertTrue(Path(data['record']).exists())
        self.assertIn('Start', describe_report(data))
        self.backend.screenshot.assert_not_called()
        self.backend.open_app.assert_not_called()
        ai.assert_not_called()

    def test_locked_phone_does_not_read_content(self):
        self.backend.request.return_value = {'value': True}
        self.backend.request.side_effect = None
        self.assertEqual(self.read()['status'], 'unavailable')
        self.backend.request.assert_called_once_with('GET', '/wda/locked')

    def test_changed_screen_does_not_return_mixed_snapshot(self):
        self.backend.request.side_effect = [
            {'value': False}, {'value': {'bundleId': 'clock'}}, {'value': XML},
            {'value': XML.replace('Start', 'Stop')}, {'value': {'bundleId': 'clock'}}]
        self.assertEqual(self.read()['status'], 'changed')
        self.assertFalse(list(self.folder.iterdir()))

    def test_cancel_prevents_requests(self):
        stop = Event(); stop.set()
        with self.assertRaises(RunCanceled):
            self.read(stop_event=stop)
        self.backend.request.assert_not_called()

    def test_secure_field_blocks_ai(self):
        secure = XML.replace('XCUIElementTypeTextField', 'XCUIElementTypeSecureTextField')
        self.backend.request.side_effect = lambda method, path: {'value': secure} if path == '/source' else self.request(method, path)
        with patch('iphone_assistant.vision.observe_screen') as ai:
            report = self.read(use_ai=True)
        self.assertFalse(report['cloud_sent'])
        self.backend.screenshot.assert_not_called()
        ai.assert_not_called()

    def test_ai_failure_retains_local_report(self):
        with patch('iphone_assistant.vision.observe_screen', side_effect=RuntimeError):
            report = self.read(use_ai=True)
        self.assertEqual(report['status'], 'read')
        self.assertIsNone(report['ai_summary'])
        self.assertIn('RuntimeError', report['ai_message'])
        self.backend.screenshot.assert_called_once()
