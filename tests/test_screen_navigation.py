import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace
from threading import Event
from iphone_assistant.screen_navigation import navigate_tab, navigate_back, xpath_literal, CLOCK
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

    def test_generic_tab_in_other_app(self):
        self.backend.active_bundle.return_value = 'example.app'
        result = navigate_tab('Stopwatch', backend_factory=lambda: self.backend)
        self.assertEqual(result.status, 'verified_match')
        self.assertEqual(result.target_bundle_id, 'example.app')
        self.assertEqual(self.clicked, 1)

    def test_arbitrary_button_is_not_a_tab(self):
        self.backend.session_request.side_effect = lambda *a: {'value': xml().replace('XCUIElementTypeTabBar', 'XCUIElementTypeOther')}
        self.assertEqual(self.run_tab().status, 'target_not_found')
        self.assertEqual(self.clicked, 0)

    def test_unselected_after_click_is_uncertain_without_replay(self):
        original = self.request
        self.backend.session_request.side_effect = lambda m, p, v=None: {'value': xml()} if p == '/source' else original(m, p, v)
        with patch('iphone_assistant.screen_navigation.time.sleep'):
            self.assertEqual(self.run_tab().status, 'verification_uncertain')
        self.assertEqual(self.clicked, 1)

    def test_changed_tree_before_click_is_rejected(self):
        original = self.request
        reads = []
        def request(m, p, v=None):
            if p == '/source':
                reads.append(1)
                return {'value': xml('0' if len(reads) == 1 else '1')}
            return original(m, p, v)
        self.backend.session_request.side_effect = request
        self.assertEqual(self.run_tab().status, 'target_not_found')
        self.assertEqual(self.clicked, 0)

    def test_xpath_escapes_both_quote_types(self):
        self.assertEqual(xpath_literal('a"b\'c'), 'concat("a",\'"\',"b\'c")')

    def test_generic_parser_preserves_name(self):
        self.assertEqual(parse_direct_command('switch to tab Search').arguments, {'target': 'Search'})
        self.assertEqual(parse_direct_command('go back').action, 'go_back')


class BackNavigationTests(unittest.TestCase):
    def setUp(self):
        self.backend = Mock()
        self.backend.request.return_value = {'value': False}
        self.backend.active_bundle.return_value = 'example.app'
        self.clicks = 0
        self.label = 'Back'
        self.name = ''
        self.container = 'XCUIElementTypeNavigationBar'
        self.change_title = True
        self.backend.session_request.side_effect = self.request

    def request(self, method, path, payload=None):
        if path == '/source':
            title = 'Parent' if self.clicks and self.change_title else 'Detail'
            return {'value': f'<root><{self.container} name="{title}" visible="true"><XCUIElementTypeButton name="{self.name}" label="{self.label}" visible="true" enabled="true"/></{self.container}></root>'}
        if path == '/elements':
            return {'value': [{'ELEMENT': 'back'}]}
        if '/attribute/' in path:
            return {'value': self.label if path.endswith('/label') else True}
        if path.endswith('/click'):
            self.clicks += 1
            return {'value': None}
        raise AssertionError(path)

    def run_back(self):
        with patch('iphone_assistant.screen_navigation.time.sleep'):
            return navigate_back(backend_factory=lambda: self.backend)

    def test_back_verifies_title_change(self):
        result = self.run_back()
        self.assertEqual(result.status, 'verified_match')
        self.assertEqual(result.verification_method, 'navigation_title_changed')
        self.assertEqual(self.clicks, 1)

    def test_native_back_identifier_with_parent_page_label(self):
        self.name = 'BackButton'
        self.label = 'Settings'
        self.assertEqual(self.run_back().status, 'verified_match')
        self.assertEqual(self.clicks, 1)

    def test_does_not_guess_unlabelled_back_or_close(self):
        for label in ('', 'Close', 'Delete', 'Settings'):
            self.label = label
            self.assertEqual(self.run_back().status, 'target_not_found')
        self.assertEqual(self.clicks, 0)

    def test_back_outside_navigation_bar_is_rejected(self):
        self.container = 'XCUIElementTypeOther'
        self.assertEqual(self.run_back().status, 'target_not_found')
        self.assertEqual(self.clicks, 0)

    def test_same_title_after_click_is_uncertain(self):
        self.change_title = False
        self.assertEqual(self.run_back().status, 'verification_uncertain')
        self.assertEqual(self.clicks, 1)

    def test_back_intent_has_no_extra_arguments(self):
        from iphone_assistant.intent import ModelIntent, validate_intent, IntentError
        item = ModelIntent(decision='action', action='go_back', direction='none', value='', message='')
        self.assertEqual(validate_intent(item).command.arguments, {})
        with self.assertRaises(IntentError):
            validate_intent(item.model_copy(update={'value': 'anything'}))
