import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from threading import Event
from iphone_assistant.screen_navigation import navigate_tab, CLOCK
from iphone_assistant.direct import parse_direct_command


def xml(value='0', count=1):
    return '<root><XCUIElementTypeTabBar>' + count * (
        f'<XCUIElementTypeButton label="Stopwatch" visible="true" enabled="true" value="{value}"/>') + '</XCUIElementTypeTabBar></root>'


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.backend = Mock()
        self.backend.request.return_value = {'value': False}
        self.backend.active_bundle.return_value = CLOCK
        self.clicked = 0
        self.backend.session_request.side_effect = self.request

    def request(self, method, path, payload=None):
        if path == '/source':
            return {'value': xml(str(int(self.clicked > 0)))}
        if path == '/elements':
            return {'value': [{'ELEMENT': 'tab'}]}
        if '/attribute/' in path:
            return {'value': 'Stopwatch' if path.endswith('/label') else True}
        if path.endswith('/click'):
            self.clicked += 1
            return {'value': None}
        raise AssertionError(path)

    def run_tab(self, **kw):
        return navigate_tab('stopwatch', backend_factory=lambda: self.backend, **kw)

    def test_verified_single_click(self):
        result = self.run_tab()
        self.assertEqual(result.status, 'verified_match')
        self.assertEqual(self.clicked, 1)
        self.assertEqual(result.steps_acknowledged, 1)

    def test_wrong_app_never_clicks(self):
        self.backend.active_bundle.return_value = 'another.app'
        self.assertEqual(self.run_tab().status, 'target_not_found')
        self.backend.session_request.assert_not_called()

    def test_duplicate_tabs_never_click(self):
        self.backend.session_request.side_effect = lambda *a: {'value': xml(count=2)}
        self.assertEqual(self.run_tab().status, 'target_not_found')
        self.assertEqual(self.clicked, 0)

    def test_already_selected_is_noop(self):
        self.backend.session_request.side_effect = lambda *a: {'value': xml('1')}
        result = self.run_tab()
        self.assertEqual(result.status, 'verified_match')
        self.assertFalse(result.action_attempted)

    def test_click_timeout_is_not_replayed(self):
        original = self.request
        def request(method, path, payload=None):
            if path.endswith('/click'):
                self.clicked += 1
                raise TimeoutError()
            return original(method, path, payload)
        self.backend.session_request.side_effect = request
        result = self.run_tab()
        self.assertEqual(result.status, 'verification_uncertain')
        self.assertTrue(result.action_attempted)
        self.assertFalse(result.action_acknowledged)
        self.assertEqual(self.clicked, 1)

    def test_foreground_change_before_click(self):
        self.backend.active_bundle.side_effect = [CLOCK, CLOCK, 'another.app']
        self.assertEqual(self.run_tab().status, 'target_not_found')
        self.assertEqual(self.clicked, 0)

    def test_cancel_and_preview_do_not_connect(self):
        stop = Event(); stop.set()
        self.assertEqual(self.run_tab(stop_event=stop).status, 'canceled')
        self.assertEqual(self.run_tab(dry_run=True).status, 'dry_run')
        self.backend.request.assert_not_called()

    def test_parse_english_tab(self):
        command = parse_direct_command('switch to Stopwatch')
        self.assertEqual(command.action, 'select_tab')
        self.assertEqual(command.arguments, {'target': 'stopwatch'})

    def test_voice_intent_routes_to_navigation_without_confirmation(self):
        from iphone_assistant.direct_cli import run_turn
        from iphone_assistant.intent import IntentResult, ModelIntent, validate_intent
        intent = validate_intent(ModelIntent(decision='action', action='select_tab',
                                            direction='none', value='stopwatch', message=''))
        with patch('iphone_assistant.intent.understand_intent', return_value=intent), \
                patch('iphone_assistant.screen_navigation.navigate_tab') as navigate, \
                patch('builtins.input', side_effect=AssertionError('unexpected confirmation')):
            args = SimpleNamespace(auto=True, listen=False, ai=True, execute=True)
            self.assertIs(run_turn(args, 'switch to Stopwatch'), navigate.return_value)
        navigate.assert_called_once_with('stopwatch', stop_event=None, on_event=None, dry_run=False)
