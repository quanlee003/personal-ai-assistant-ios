import json
from pathlib import Path
from tempfile import TemporaryDirectory
import tkinter as tk
from unittest import TestCase
from unittest.mock import Mock
from queue import Queue

from iphone_assistant.onboarding import SetupPreferences, setup_step
from iphone_assistant.desktop_controller import Readiness
from iphone_assistant.desktop import DesktopApp


def ready(phone=True, mic=True, services=True):
    return Readiness(phone, mic, services, '', '', '')

CATALOG = {'status': 'scanned', 'device_key': 'test-device'}


class SetupTests(TestCase):
    def test_required_steps_before_optional(self):
        self.assertEqual(setup_step(None, None, set()), 'checking')
        self.assertEqual(setup_step(ready(), {'status': 'disconnected'}, set()), 'connection')
        self.assertEqual(setup_step(ready(False), CATALOG, set()), 'phone')
        self.assertEqual(setup_step(ready(mic=False), CATALOG, set()), 'microphone')
        self.assertEqual(setup_step(ready(services=False), CATALOG, set()), 'services')
        self.assertEqual(setup_step(ready(), CATALOG, set()), 'personalization')

    def test_skip_is_per_device_and_not_usage_consent(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'setup.json'
            prefs = SetupPreferences(path)
            prefs.finish('test-device')
            data = json.loads(path.read_text())
            self.assertEqual(set(data), {'screen_time_prompt_dismissed'})
            prefs = SetupPreferences(path)
            self.assertEqual(setup_step(ready(), CATALOG, prefs.dismissed), 'ready')
            self.assertEqual(setup_step(ready(), {'status': 'scanned', 'device_key': 'other'}, prefs.dismissed), 'personalization')
            path.write_text('[]')
            self.assertEqual(SetupPreferences(path).dismissed, set())


class SetupWindowTests(TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.controller = Mock(busy=False, events=Queue())
        self.app = DesktopApp(self.root, self.controller, SetupPreferences(Path(self.temp.name) / 'prefs.json'))
        self.app.readiness = ready()
        self.app.catalog_data = CATALOG
        self.app._controls(False)
        self.root.update_idletasks()

    def test_optional_step_does_not_open_phone_automatically(self):
        self.assertEqual(self.app.current_setup_step, 'personalization')
        self.assertEqual(self.app.main_body.winfo_manager(), '')
        self.controller.open_phone_setup.assert_not_called()
        self.app.setup_action.invoke()
        self.controller.open_phone_setup.assert_called_once()
        self.assertNotIn('test-device', self.app.preferences.dismissed)

    def test_skip_opens_simple_home_and_personalization_can_return(self):
        self.app.setup_later.invoke()
        self.assertEqual(self.app.current_setup_step, 'ready')
        self.assertEqual(self.app.setup_frame.winfo_manager(), '')
        self.assertEqual(self.app.main_body.winfo_manager(), 'pack')
        self.assertEqual(self.app.tools_window.state(), 'withdrawn')
        self.assertEqual(self.app.stop_button.winfo_manager(), '')
        self.app.show_personalization()
        self.assertEqual(self.app.current_setup_step, 'personalization')

    def test_missing_required_connection_cannot_be_skipped(self):
        self.app.readiness = ready(False)
        self.app._controls(False)
        self.assertEqual(self.app.current_setup_step, 'phone')
        self.assertEqual(self.app.setup_later.winfo_manager(), '')
        self.app.finish_setup()
        self.assertEqual(self.app.preferences.dismissed, set())

    def test_setup_result_does_not_claim_report_access(self):
        self.app._event('setup_result', 'Opened page')
        self.app._event('finished', 'setup')
        self.assertEqual(self.app.setup_feedback.cget('text'), 'Opened page')
        self.assertEqual(self.app.setup_continue.winfo_manager(), 'pack')
        self.assertEqual(self.app.preferences.dismissed, set())
