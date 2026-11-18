import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
import unittest
from unittest.mock import Mock, patch

from iphone_assistant.control import RunCanceled
from iphone_assistant.device_catalog import DeviceCatalog
from iphone_assistant.phone_setup import open_screen_time
from iphone_assistant.desktop_controller import DesktopController, Readiness


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def test_first_connection_scan_reconnect_and_force(self):
        reader = Mock(side_effect=[
            {'status': 'connected', 'device_key': 'a'},
            {'status': 'scanned', 'device_key': 'a', 'apps': []},
            {'status': 'connected', 'device_key': 'a'},
            {'status': 'disconnected'},
            {'status': 'connected', 'device_key': 'a'},
            {'status': 'scanned', 'device_key': 'a', 'apps': []},
            {'status': 'connected', 'device_key': 'a'},
            {'status': 'scanned', 'device_key': 'a', 'apps': []},
        ])
        catalog = DeviceCatalog(reader, self.folder)
        catalog.refresh()
        catalog.refresh()
        self.assertEqual(reader.call_count, 3)
        self.assertEqual(catalog.refresh()['status'], 'disconnected')
        self.assertIsNone(catalog.current)
        catalog.refresh()
        catalog.refresh(force=True)
        self.assertEqual(reader.call_count, 8)
        self.assertEqual(json.loads((self.folder / 'a.json').read_text())['screen_time'], 'unknown')

    def test_switch_during_scan_does_not_save_wrong_device(self):
        reader = Mock(side_effect=[{'status': 'connected', 'device_key': 'a'},
                                   {'status': 'scanned', 'device_key': 'b', 'apps': []}])
        self.assertEqual(DeviceCatalog(reader, self.folder).refresh()['status'], 'device_error')
        self.assertFalse(list(self.folder.iterdir()))

    def test_cancel_does_not_replace_profile(self):
        stop = Event()
        def reader(full, event):
            if full:
                stop.set()
            return {'status': 'scanned' if full else 'connected', 'device_key': 'a', 'apps': []}
        with self.assertRaises(RunCanceled):
            DeviceCatalog(reader, self.folder).refresh(stop)
        self.assertFalse(list(self.folder.iterdir()))

    def test_optional_setup_checks_identity_and_never_enables(self):
        backend = Mock()
        backend.tunnel = {'udid': 'device'}
        backend.settings_foreground.return_value = True
        backend.session_request.return_value = {'value': '<root><XCUIElementTypeNavigationBar name="Screen Time" visible="true" /></root>'}
        key = hashlib.sha256(b'device').hexdigest()[:24]
        result = open_screen_time(backend_factory=lambda: backend, device_key=key)
        self.assertIn('Thời gian sử dụng', result)
        self.assertEqual(backend.session_request.call_count, 1)
        backend.reset_mock()
        with self.assertRaises(RuntimeError):
            open_screen_time(backend_factory=lambda: backend, device_key='other')
        backend.open_settings.assert_not_called()

    def test_failed_scan_does_not_reuse_old_device(self):
        catalog = DeviceCatalog(Mock(return_value={'status': 'multiple_devices'}), self.folder)
        catalog.current = {'device_key': 'old', 'apps': []}
        self.assertEqual(catalog.refresh()['status'], 'multiple_devices')
        self.assertIsNone(catalog.current)

    def test_storage_failure_does_not_claim_saved_or_keep_old_data(self):
        reader = Mock(side_effect=[{'status': 'connected', 'device_key': 'a'},
                                   {'status': 'scanned', 'device_key': 'a', 'apps': []}])
        catalog = DeviceCatalog(reader, self.folder)
        with patch('iphone_assistant.device_catalog.os.replace', side_effect=OSError):
            self.assertEqual(catalog.refresh()['status'], 'storage_error')
        self.assertIsNone(catalog.current)

    def test_app_refresh_scans_without_voice_or_wda_requirement(self):
        catalog = Mock()
        catalog.refresh.return_value = {'status': 'scanned', 'device_key': 'a', 'apps': []}
        runner = Mock()
        controller = DesktopController(preflight=lambda _: Readiness(False, False, False, '', '', ''),
                                       runner=runner, catalog=catalog)
        controller.refresh()
        controller._worker.join(2)
        self.assertFalse(controller.busy)
        catalog.refresh.assert_called_once()
        runner.assert_not_called()
        events = []
        while not controller.events.empty():
            events.append(controller.events.get_nowait()[0])
        self.assertIn('catalog', events)

    def test_navigation_clicks_only_observed_screen_time_and_verifies(self):
        backend = Mock()
        backend.tunnel = {'udid': 'device'}
        backend.settings_foreground.return_value = True
        root = '<root><XCUIElementTypeWindow height="900"/><XCUIElementTypeNavigationBar name="Settings"/><XCUIElementTypeButton name="com.apple.settings.screenTime" visible="true" y="300" height="50"/></root>'
        target = '<root><XCUIElementTypeNavigationBar name="Screen Time"/></root>'
        backend.session_request.side_effect = [
            {'value': root}, {'value': root}, {'value': [{'ELEMENT': 'target'}]},
            {'value': None}, {'value': target},
        ]
        with patch('iphone_assistant.phone_setup.time.sleep'):
            open_screen_time(backend_factory=lambda: backend,
                             device_key=hashlib.sha256(b'device').hexdigest()[:24])
        clicks = [c for c in backend.session_request.call_args_list if c.args[1].endswith('/click')]
        self.assertEqual(len(clicks), 1)
        self.assertEqual(clicks[0].args[1], '/element/target/click')
