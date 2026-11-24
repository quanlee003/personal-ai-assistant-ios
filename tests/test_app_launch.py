import hashlib
import contextlib
import io
from threading import Event
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from iphone_assistant.app_launch import launch_app, resolve_app
from iphone_assistant.commands import Command
from iphone_assistant import direct_cli

APP = {'name': 'Zalo', 'bundle_id': 'com.test.zalo', 'type': 'User'}


class AppLaunchTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.catalog = Mock()
        self.catalog.refresh.return_value = {'status': 'scanned', 'device_key': hashlib.sha256(b'phone').hexdigest()[:24], 'apps': [APP]}
        self.backend = Mock()
        self.backend.tunnel = {'udid': 'phone'}
        self.backend.ready.return_value = True
        self.backend.active_bundle.return_value = APP['bundle_id']

    def run_app(self, **kwargs):
        return launch_app('Zalo', catalog=self.catalog, backend_factory=lambda: self.backend, **kwargs)

    def test_exact_name_not_guess_or_hidden_service(self):
        self.assertEqual(resolve_app('zalo', [APP]), APP)
        self.assertEqual(resolve_app('Zal', [APP]).status, 'target_not_found')
        self.assertEqual(resolve_app('Zalo', [APP, {**APP, 'bundle_id': 'other'}]).status, 'needs_clarification')
        self.assertEqual(resolve_app('Zalo', [{**APP, 'type': 'System'}]).status, 'target_not_found')
        clock = {'name': 'Clock', 'bundle_id': 'com.apple.mobiletimer', 'type': 'System'}
        self.assertEqual(resolve_app('đồng hồ', [clock]), clock)

    def test_foreground_verifies_success_without_vision(self):
        result = self.run_app()
        self.assertEqual(result.status, 'verified_match')
        self.assertEqual(result.target_bundle_id, result.observed_bundle_id)
        self.assertEqual(result.verification_method, 'foreground_bundle')
        self.backend.open_app.assert_called_once_with(APP['bundle_id'])
        self.catalog.refresh.assert_called_once_with(None, force=True)

    def test_wrong_device_and_preview_never_launch(self):
        self.backend.tunnel = {'udid': 'other'}
        self.assertEqual(self.run_app().error_code, 'device_mismatch')
        self.assertEqual(self.run_app(dry_run=True).status, 'dry_run')
        self.backend.open_app.assert_not_called()

    def test_timeout_is_not_replayed(self):
        self.backend.open_app.side_effect = TimeoutError
        self.assertEqual(self.run_app().status, 'verification_uncertain')
        self.backend.open_app.assert_called_once()
        self.backend.active_bundle.assert_not_called()

    def test_wrong_foreground_never_reports_success(self):
        self.backend.active_bundle.return_value = 'other'
        with patch('iphone_assistant.app_launch.time.sleep'):
            self.assertEqual(self.run_app().error_code, 'foreground_unconfirmed')
        self.backend.open_app.assert_called_once()

    def test_stop_after_launch_remains_uncertain(self):
        stop = Event()
        self.backend.open_app.side_effect = lambda _: stop.set()
        self.assertEqual(self.run_app(stop_event=stop).status, 'verification_uncertain')
        self.backend.active_bundle.assert_not_called()

    def test_real_turn_routes_ai_name_to_local_resolution(self):
        args = SimpleNamespace(auto=True, listen=False, ai=True, execute=True, verify=True)
        with patch('iphone_assistant.intent.understand_intent', return_value=SimpleNamespace(
                decision='action', command=Command('open_app', {'app_name': 'Zalo'}))), patch(
                'iphone_assistant.app_launch.launch_app', return_value='result') as launch:
            self.assertEqual(direct_cli.run_turn(args, 'mở Zalo'), 'result')
            self.assertEqual(launch.call_args.args, ('Zalo',))
